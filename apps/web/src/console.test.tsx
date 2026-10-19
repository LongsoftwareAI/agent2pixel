import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import Console from './Console';
import { VoiceDraft, type SpeechAdapter } from './VoiceDraft';
import { useStore } from './store';
import { newAgent } from './AgentForm';
const prefs = {
    theme: 'dark', accent: 'blue', sidebar: 'full', font: 'medium', density: 'comfortable', office_enabled: true, start_page: 'overview', refresh: 'off', revision: 1
};
const agent = {
    ...newAgent('w'), id: 'a', name: 'Researcher', role: 'Research', status: 'idle'
};
const overview = {
    agents: {
        total: 1, busy: 0
    }, work: {
        total: 1, pending_review: 0, completed: 0
    }, runs: {
        total: 0, active: 0
    }, usage: {
        input_tokens: null, output_tokens: null, total_tokens: null, actual_cost: null, estimated_cost: null
    }, activity: [], services: [], observed_at: '2026-10-18T10:00:00Z'
};
function setup(overrides?: (path: string, method: string, body: Record<string, unknown>) => unknown) {
    const fetcher = vi.fn(async (path: string, options?: RequestInit) => {
        const method = options?.method ?? 'GET';
        const body = options?.body ? JSON.parse(String(options.body)) : {};
        const custom = overrides?.(path, method, body);
        if (custom instanceof Error)
            return {
                ok: false, json: async () => ({
                    detail: custom.message
                })
            };
        if (custom !== undefined)
            return {
                ok: true, json: async () => custom
            };
        let result: unknown = {};
        if (path === '/api/workspaces')
            result = [{
                    id: 'w', name: 'Studio', root_path: '/local', created_at: ''
                }];
        else if (path.startsWith('/api/bootstrap'))
            result = {
                workspaces: [], agents: [agent], workflows: [{
                        id: 'flow', name: 'Review', version: 1
                    }], room: null, assets: [], runs: []
            };
        else if (path.includes('/overview'))
            result = overview;
        else if (path.includes('/preferences'))
            result = prefs;
        else if (path.includes('/usage'))
            result = {
                daily: []
            };
        else if (path.includes('/conversations/c1'))
            result = {
                id: 'c1', agent_id: 'a', title: 'Test', messages: []
            };
        else if (path.includes('/conversations'))
            result = [];
        return {
            ok: true, json: async () => result
        };
    });
    vi.stubGlobal('fetch', fetcher);
    return fetcher;
}
beforeEach(() => { history.replaceState(null, '', '/#overview'); useStore.setState({
    workspaceId: 'w', events: [], connected: false
}); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); history.replaceState(null, '', '/'); delete document.documentElement.dataset.consoleTheme; });
describe('operations console', () => {
    it('renders real counts, unknown tokens and command palette navigation', async () => { setup(); render(<Console />); await screen.findByText('Researcher'); const token = screen.getByText('Token đã ghi nhận').closest('button'); expect(token?.textContent).toContain('—'); expect(screen.getByText('Localhost · đã đồng bộ')).toBeTruthy(); fireEvent.keyDown(window, {
        key: 'k', ctrlKey: true
    }); const dialog = screen.getByRole('dialog', {
        name: 'Điều hướng nhanh'
    }); expect(dialog).toBeTruthy(); fireEvent.change(screen.getByLabelText('Tìm màn hình'), {
        target: {
            value: 'Chi phí'
        }
    }); fireEvent.click(screen.getByRole('button', {
        name: /▥ Chi phí/
    })); await screen.findByText('Mức sử dụng runtime'); expect(location.hash).toBe('#usage'); });
    it('shows connection failure honestly and retries', async () => { let fail = true; setup(path => path.includes('/overview') && fail ? Error('backend unavailable') : undefined); render(<Console />); await screen.findByRole('alert'); expect(screen.getByText('Kết nối lỗi · dữ liệu có thể cũ')).toBeTruthy(); expect(screen.queryByText('Localhost · đã đồng bộ')).toBeNull(); fail = false; fireEvent.click(screen.getByText('Thử lại')); await screen.findByText('Localhost · đã đồng bộ'); });
    it('persists preferences including revision and reports rejection', async () => {
        history.replaceState(null, '', '/#preferences');
        let reject = false;
        const fetcher = setup((path, method, body) => {
            if (path.includes('/preferences') && method === 'PATCH')
                return reject ? Error('revision conflict') : {
                    ...prefs, ...body, revision: 2
                };
        });
        render(<Console />);
        await screen.findByText('revision 1');
        fireEvent.change(screen.getByLabelText('Giao diện'), {
            target: {
                value: 'light'
            }
        });
        fireEvent.click(screen.getByText('Lưu cài đặt'));
        await screen.findByText('Đã lưu cài đặt');
        expect(document.documentElement.dataset.consoleTheme).toBe('light');
        expect(fetcher.mock.calls.some(([, o]) => o?.method === 'PATCH' && JSON.parse(String(o.body)).revision === 1)).toBe(true);
        reject = true;
        fireEvent.click(screen.getByText('Lưu cài đặt'));
        await screen.findByText('revision conflict');
    });
    it('creates a real direct conversation and sends a scoped idempotent request; failure keeps draft', async () => {
        history.replaceState(null, '', '/#chat');
        let reject = false;
        const fetcher = setup((path, method, body) => {
            if (path.endsWith('/conversations') && method === 'POST')
                return {
                    id: 'c1', agent_id: 'a', title: body.title
                };
            if (path.includes('/messages') && method === 'POST')
                return reject ? Error('runtime unavailable') : {
                    message: {
                        id: 'm1'
                    }, run_id: 'r1', work_item_id: 'i1'
                };
        });
        render(<Console />);
        await screen.findByRole('option', {
            name: 'Researcher · mock'
        });
        fireEvent.change(screen.getByLabelText('Bot thực thi'), {
            target: {
                value: 'a'
            }
        });
        fireEvent.change(screen.getByLabelText('Tin nhắn'), {
            target: {
                value: 'Analyze a brief'
            }
        });
        fireEvent.click(screen.getByText('Gửi ↑'));
        await waitFor(() => expect((screen.getByLabelText('Tin nhắn') as HTMLTextAreaElement).value).toBe(''));
        const call = fetcher.mock.calls.find(([p, o]) => p.includes('/messages') && o?.method === 'POST');
        expect(call?.[0]).toContain('workspace_id=w');
        expect(JSON.parse(String(call?.[1]?.body))).toEqual(expect.objectContaining({
            content: 'Analyze a brief', client_request_id: expect.any(String)
        }));
        reject = true;
        fireEvent.change(screen.getByLabelText('Tin nhắn'), {
            target: {
                value: 'Keep this draft'
            }
        });
        fireEvent.click(screen.getByText('Gửi ↑'));
        await screen.findByText('Error: runtime unavailable');
        expect((screen.getByLabelText('Tin nhắn') as HTMLTextAreaElement).value).toBe('Keep this draft');
    });
    it('uses actual run state for cancellation and never guesses an active run', async () => {
        history.replaceState(null, '', '/#chat');
        let state = 'completed';
        setup((path, method) => {
            if (path.includes('/sessions'))
                return [{
                        id: 'r', run_id: 'r', state
                    }];
            if (path.includes('/runs/r/cancel') && method === 'POST') {
                state = 'cancelled';
                return {
                    id: 'r', state
                };
            }
            if (path.includes('/conversations/c1'))
                return {
                    id: 'c1', agent_id: 'a', title: 'History task', messages: [{
                            id: 'u', role: 'user', content: 'Work input', created_at: '', run_id: 'r'
                        }]
                };
            if (path.includes('/conversations'))
                return [{
                        id: 'c1', agent_id: 'a', title: 'History task'
                    }];
        });
        render(<Console />);
        await screen.findByText('History task');
        fireEvent.click(screen.getByText('History task'));
        await screen.findByText('Work input');
        await screen.findByText('completed');
        expect(screen.queryByText('Hủy lượt chạy')).toBeNull();
        state = 'running';
        fireEvent.click(screen.getByText('＋ Cuộc trò chuyện mới'));
        fireEvent.click(screen.getByText('History task'));
        await screen.findByText('Hủy lượt chạy');
        fireEvent.click(screen.getByText('Hủy lượt chạy'));
        await screen.findByText('cancelled');
        expect(screen.queryByText('Hủy lượt chạy')).toBeNull();
    });
    it('blocks a common room message without configured workflow', async () => { history.replaceState(null, '', '/#room'); const fetcher = setup(); render(<Console />); await screen.findByRole('option', {
        name: 'Researcher · mock'
    }); fireEvent.change(screen.getByLabelText('Tin nhắn'), {
        target: {
            value: 'Task'
        }
    }); fireEvent.click(screen.getByText('Gửi ↑')); await screen.findByText('Chọn bot hoặc workflow; phòng chung không tự cấp quyền.'); expect(fetcher.mock.calls.some(([, o]) => o?.method === 'POST')).toBe(false); });
    it('shows SOUL save conflicts instead of success', async () => { history.replaceState(null, '', '/#bots'); setup((path, method) => path.includes('/soul/history') ? [] : path.includes('/soul') ? method === 'PATCH' ? Error('SOUL revision conflict') : {
        content: 'Be helpful', revision: 2
    } : undefined); render(<Console />); await screen.findByText('Hồ sơ thực thi'); fireEvent.click(screen.getByText('SOUL')); await screen.findByText('Be helpful'); fireEvent.click(screen.getByText('Sửa SOUL')); fireEvent.change(screen.getByLabelText('Nội dung SOUL'), {
        target: {
            value: 'Review carefully'
        }
    }); fireEvent.click(screen.getByText('Lưu revision mới')); await screen.findByText('Error: SOUL revision conflict'); expect(screen.queryByText('Đã lưu. Chỉ các lượt chạy mới dùng revision này.')).toBeNull(); });
});
describe('voice draft adapter', () => {
    function adapter(): SpeechAdapter { return {
        lang: '', continuous: false, interimResults: false, onresult: null, onerror: null, onend: null, start: vi.fn(), stop: vi.fn(), abort: vi.fn()
    }; }
    it('requires consent, previews transcript and never automatically sends', () => { const speech = adapter(), received = vi.fn(); render(<VoiceDraft createAdapter={() => speech} onTranscript={received}/>); fireEvent.click(screen.getByText('♩ Giọng nói')); expect(speech.start).not.toHaveBeenCalled(); fireEvent.click(screen.getByText('Đồng ý & bắt đầu')); expect(speech.start).toHaveBeenCalledOnce(); speech.onresult?.({
        results: [[{
                    transcript: 'Tạo kế hoạch'
                }]]
    }); expect(received).not.toHaveBeenCalled(); return waitFor(() => { fireEvent.click(screen.getByText('Dùng làm bản nháp')); expect(received).toHaveBeenCalledWith('Tạo kế hoạch'); }); });
    it('cancels recording, ignores late result and surfaces permission failure', async () => { const speech = adapter(), received = vi.fn(); render(<VoiceDraft createAdapter={() => speech} onTranscript={received}/>); fireEvent.click(screen.getByText('♩ Giọng nói')); fireEvent.click(screen.getByText('Đồng ý & bắt đầu')); fireEvent.click(screen.getByText('Hủy ghi âm')); speech.onresult?.({
        results: [[{
                    transcript: 'late'
                }]]
    }); expect(screen.queryByText('late')).toBeNull(); expect(speech.abort).toHaveBeenCalledOnce(); fireEvent.click(screen.getByText('♩ Giọng nói')); fireEvent.click(screen.getByText('Đồng ý & bắt đầu')); speech.onerror?.({
        error: 'not-allowed'
    }); await screen.findByText('Nhận dạng giọng nói: not-allowed'); expect(received).not.toHaveBeenCalled(); });
});
it('switches direct bot A to B without sending the previous conversation to A', async () => {
    history.replaceState(null, '', '/#chat');
    const second = {
        ...agent, id: 'b', name: 'Analyst'
    };
    const fetcher = setup((path, method, body) => {
        if (path.startsWith('/api/bootstrap'))
            return {
                workspaces: [], agents: [agent, second], workflows: [], room: null, assets: [], runs: []
            };
        if (path.includes('/conversations/c1'))
            return {
                id: 'c1', agent_id: 'a', title: 'History A', messages: [{
                        id: 'old', role: 'assistant', content: 'Previous A output', created_at: ''
                    }]
            };
        if (path.includes('/conversations/c2'))
            return {
                id: 'c2', agent_id: 'b', title: 'New B', messages: []
            };
        if (path.endsWith('/conversations') && method === 'POST')
            return {
                id: 'c2', agent_id: body.agent_id, title: body.title
            };
        if (path.endsWith('/conversations?workspace_id=w'))
            return [{
                    id: 'c1', agent_id: 'a', title: 'History A'
                }];
    });
    render(<Console />);
    fireEvent.click(await screen.findByText('History A'));
    await screen.findByText('Previous A output');
    fireEvent.change(screen.getByLabelText('Bot thực thi'), {
        target: {
            value: 'b'
        }
    });
    expect(screen.queryByText('Previous A output')).toBeNull();
    fireEvent.change(screen.getByLabelText('Tin nhắn'), {
        target: {
            value: 'New analysis for B'
        }
    });
    fireEvent.click(screen.getByText('Gửi ↑'));
    await waitFor(() => expect(fetcher.mock.calls.some(([path, options]) => path.includes('/conversations/c2/messages') && options?.method === 'POST')).toBe(true));
    const created = fetcher.mock.calls.find(([path, options]) => path.endsWith('/conversations') && options?.method === 'POST');
    expect(JSON.parse(String(created?.[1]?.body)).agent_id).toBe('b');
    expect(fetcher.mock.calls.some(([path, options]) => path.includes('/conversations/c1/messages') && options?.method === 'POST')).toBe(false);
});
it('uploads a PNG, previews the server image and declares missing vision capability', async () => {
    history.replaceState(null, '', '/#chat');
    const fetcher = setup((path, method) => {
        if (path.includes('/attachments/image') && method === 'POST')
            return {
                id: 'img1', name: 'sample.png', pixel_interpretation: 'unsupported', preview_url: '/api/console/attachments/img1/image?workspace_id=w'
            };
    });
    render(<Console />);
    await screen.findByRole('option', {
        name: 'Researcher · mock'
    });
    const encoded = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGOQ8DsOAAGvAS6L4kr/AAAAAElFTkSuQmCC';
    const file = new File([Uint8Array.from(atob(encoded), c => c.charCodeAt(0))], 'sample.png', {
        type: 'image/png'
    });
    fireEvent.change(screen.getByLabelText('Đính kèm tệp'), {
        target: {
            files: [file]
        }
    });
    await screen.findByAltText('Ảnh đính kèm sample.png');
    expect(screen.getByText(/Agent chỉ nhận metadata/)).toBeTruthy();
    const call = fetcher.mock.calls.find(([path, options]) => path.includes('/attachments/image') && options?.method === 'POST');
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({
        workspace_id: 'w', name: 'sample.png', media_type: 'image/png', content_base64: encoded
    });
    expect(fetcher.mock.calls.some(([path]) => path.includes('/messages'))).toBe(false);
});
it('rejects oversized image locally and reports backend PNG validation failure', async () => {
    history.replaceState(null, '', '/#chat');
    const fetcher = setup((path, method) => path.includes('/attachments/image') && method === 'POST' ? Error('PNG metadata unsupported') : undefined);
    render(<Console />);
    const input = await screen.findByLabelText('Đính kèm tệp');
    fireEvent.change(input, {
        target: {
            files: [new File([new Uint8Array(1048577)], 'huge.png', {
                    type: 'image/png'
                })]
        }
    });
    await screen.findByText('Tệp vượt giới hạn 1 MiB.');
    expect(fetcher.mock.calls.some(([path]) => path.includes('/attachments'))).toBe(false);
    fireEvent.change(input, {
        target: {
            files: [new File(['bad'], 'bad.png', {
                    type: 'image/png'
                })]
        }
    });
    await screen.findByText('Error: PNG metadata unsupported');
    expect(screen.queryByAltText('Ảnh đính kèm bad.png')).toBeNull();
});
it('initializes the first editable preferences revision atomically after delayed loading', async () => {
    history.replaceState(null, '', '/#preferences');
    let ready!: (value: typeof prefs) => void;
    const pending = new Promise<typeof prefs>(resolve => { ready = resolve; });
    const fetcher = setup((path, method, body) => path.includes('/preferences') ? method === 'GET' ? pending : {
        ...prefs, ...body, revision: 2
    } : undefined);
    render(<Console />);
    expect((screen.getByText('Lưu cài đặt') as HTMLButtonElement).disabled).toBe(true);
    await act(async () => { ready(prefs); await pending; });
    fireEvent.change(screen.getByLabelText('Giao diện'), {
        target: {
            value: 'light'
        }
    });
    fireEvent.click(screen.getByText('Lưu cài đặt'));
    await screen.findByText('Đã lưu cài đặt');
    const saved = fetcher.mock.calls.find(([, options]) => options?.method === 'PATCH');
    expect(JSON.parse(String(saved?.[1]?.body))).toEqual(expect.objectContaining({
        theme: 'light', revision: 1
    }));
});
