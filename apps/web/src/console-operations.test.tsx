import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Budget, RevisionHistory, ArchiveWork } from './ConsoleOperations';
import { SafeMarkdown } from './SafeMarkdown';
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
describe('versioned operations', () => {
    it('saves exact versioned budget and rejects invalid thresholds locally', async () => { const fetcher = vi.fn(async (_p: string, o?: RequestInit) => ({
        ok: true, json: async () => o?.method === 'PATCH' ? {
            revision: 2
        } : {
            policy: {
                revision: 1, monthly_token_threshold: 100, monthly_cost_threshold: null
            }, alerts: []
        }
    })); vi.stubGlobal('fetch', fetcher); render(<Budget workspaceId="w"/>); await waitFor(() => expect((screen.getByLabelText('Ngưỡng token tháng') as HTMLInputElement).value).toBe('100')); fireEvent.change(screen.getByLabelText('Ngưỡng token tháng'), {
        target: {
            value: '-1'
        }
    }); fireEvent.click(screen.getByText('Lưu ngưỡng')); await screen.findByText('Ngưỡng phải lớn hơn 0; token phải là số nguyên. Để trống để tắt cảnh báo.'); expect(fetcher.mock.calls.some(([, o]) => o?.method === 'PATCH')).toBe(false); fireEvent.change(screen.getByLabelText('Ngưỡng token tháng'), {
        target: {
            value: '200'
        }
    }); fireEvent.click(screen.getByText('Lưu ngưỡng')); await screen.findByText('Đã lưu ngưỡng cảnh báo.'); expect(fetcher.mock.calls.some(([, o]) => o?.method === 'PATCH' && JSON.parse(String(o.body)).monthly_token_threshold === 200 && JSON.parse(String(o.body)).revision === 1)).toBe(true); });
    it('displays budget conflict without success', async () => { vi.stubGlobal('fetch', vi.fn(async (_p: string, o?: RequestInit) => ({
        ok: o?.method !== 'PATCH', json: async () => o?.method === 'PATCH' ? {
            detail: 'budget stale'
        } : {
            policy: {
                revision: 1
            }, alerts: []
        }
    }))); render(<Budget workspaceId="w"/>); await waitFor(() => expect((screen.getByText('Lưu ngưỡng') as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(screen.getByText('Lưu ngưỡng')); await screen.findByText('Error: budget stale'); expect(screen.queryByText('Đã lưu ngưỡng cảnh báo.')).toBeNull(); });
    it('previews history and sends reviewed rollback revision, handles conflict', async () => { let denied = false; const restored = vi.fn(), fetcher = vi.fn(async (_p: string, o?: RequestInit) => ({
        ok: !(denied && o?.method === 'POST'), json: async () => o?.method === 'POST' ? (denied ? {
            detail: 'stale history'
        } : {
            revision: 3
        }) : [{
                revision: 1, content: 'first'
            }]
    })); vi.stubGlobal('fetch', fetcher); render(<RevisionHistory workspaceId="w" agentId="a" kind="soul" currentRevision={2} currentContent="current" onRestored={restored}/>); await screen.findByText('revision 1'); fireEvent.click(screen.getByText('revision 1')); await screen.findByText('first'); fireEvent.click(screen.getByText('Khôi phục nội dung revision 1 thành revision mới')); await waitFor(() => expect(restored).toHaveBeenCalledOnce()); expect(fetcher.mock.calls.some(([p, o]) => p.includes('workspace_id=w') && o?.method === 'POST' && JSON.parse(String(o.body)).target_revision === 1 && JSON.parse(String(o.body)).revision === 2)).toBe(true); denied = true; fireEvent.click(screen.getByText('revision 1')); fireEvent.click(screen.getByText('Khôi phục nội dung revision 1 thành revision mới')); await screen.findByText('Error: stale history'); expect(restored).toHaveBeenCalledOnce(); });
    it('archives through versioned scoped API, preserves item on failure', async () => { let deny = false; const changed = vi.fn().mockResolvedValue(undefined), fetcher = vi.fn(async () => ({
        ok: !deny, json: async () => deny ? {
            detail: 'archive conflict'
        } : {
            archived: true
        }
    })); vi.stubGlobal('fetch', fetcher); render(<ArchiveWork workspaceId="w" item={{
        id: 'i', archive_revision: 3
    }} onChanged={changed}/>); fireEvent.click(screen.getByText('Lưu trữ công việc')); await waitFor(() => expect(changed).toHaveBeenCalledOnce()); expect(fetcher.mock.calls[0]).toEqual(['/api/console/work-items/i/archive?workspace_id=w', expect.objectContaining({
            method: 'POST', body: JSON.stringify({
                archived: true, revision: 3
            })
        })]); deny = true; fireEvent.click(screen.getByText('Lưu trữ công việc')); await screen.findByText('Error: archive conflict'); expect(changed).toHaveBeenCalledOnce(); });
});
describe('untrusted report rendering', () => { it('renders markdown table safely without executing HTML or unsafe links', () => { const { container } = render(<SafeMarkdown content={'# Report\n**Verified** [source](https://example.com)\n<script>alert(1)</script>\n[bad](javascript:alert(1))\n| Metric | Value |\n| --- | --- |\n| Rows | 3 |'}/>); expect(screen.getByText('Report').tagName).toBe('H3'); expect(container.querySelectorAll('table tbody tr')).toHaveLength(1); expect(container.querySelectorAll('script')).toHaveLength(0); expect(container.querySelectorAll('a')).toHaveLength(1); expect(screen.getByRole('link').getAttribute('rel')).toContain('noopener'); expect(container.textContent).toContain('<script>alert(1)</script>'); }); });
it('previews actual current config and refreshes history when revision advances', async () => {
    const fetcher = vi.fn(async () => ({
        ok: true, json: async () => [{
                revision: 1, config: {
                    role: 'before'
                }
            }]
    }));
    vi.stubGlobal('fetch', fetcher);
    const restored = vi.fn();
    const view = render(<RevisionHistory workspaceId="w" agentId="a" kind="config" currentRevision={4} currentContent={{
        role: 'current'
    }} onRestored={restored}/>);
    fireEvent.click(await screen.findByText('revision 1'));
    expect(screen.getByText(/"current"/)).toBeTruthy();
    expect(screen.getByText(/"before"/)).toBeTruthy();
    view.rerender(<RevisionHistory workspaceId="w" agentId="a" kind="config" currentRevision={5} currentContent={{
        role: 'new'
    }} onRestored={restored}/>);
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
    expect(screen.queryByText('Khôi phục nội dung revision 1 thành revision mới')).toBeNull();
});
it('downloads a bounded redacted log payload through the actual export contract', async () => {
    const data = {
        items: [{
                message: 'token=[REDACTED]'
            }], limit: 200
    };
    const fetcher = vi.fn(async (_path: string) => ({
        ok: true, json: async () => data
    }));
    vi.stubGlobal('fetch', fetcher);
    const { Blob: NodeBlob } = await import('node:buffer');
    vi.stubGlobal('Blob', NodeBlob);
    let downloaded: InstanceType<typeof NodeBlob> | undefined;
    const create = vi.fn((blob: Blob | MediaSource) => { downloaded = blob as unknown as InstanceType<typeof NodeBlob>; return 'blob:local-export'; });
    vi.stubGlobal('URL', class extends URL {
        static createObjectURL = create;
        static revokeObjectURL = vi.fn();
    });
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => { });
    const { LogExport } = await import('./ConsoleOperations');
    render(<LogExport workspaceId="w" kind="system"/>);
    fireEvent.click(screen.getByText('↓ Xuất JSON đã redaction'));
    await waitFor(() => expect(click).toHaveBeenCalledOnce());
    expect(fetcher.mock.calls[0][0]).toBe('/api/console/logs/export?workspace_id=w&kind=system&limit=200');
    expect(JSON.parse(await downloaded!.text())).toEqual(data);
    expect(downloaded!.type).toBe('application/json');
    vi.restoreAllMocks();
});
