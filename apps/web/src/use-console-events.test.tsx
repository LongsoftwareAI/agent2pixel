import {afterEach, describe, expect, it, vi} from 'vitest';
import {act, cleanup, render, screen} from '@testing-library/react';
import {useConsoleEvents} from './useConsoleEvents';
import {useStore} from './store';

class Socket {
  static instances: Socket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: {data: string}) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(public url: string) { Socket.instances.push(this); }
  close = vi.fn(() => this.onclose?.());
  emit(seq: number, workspace_id = 'w') {
    this.onmessage?.({data: JSON.stringify({id: String(seq), seq, workspace_id, event_type: 'workflow.completed'})});
  }
}
function Probe({workspace = 'w'}: {workspace?: string}) {
  const events = useConsoleEvents(workspace);
  return <output>{events.connection}:{events.revision}</output>;
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.useRealTimers(); Socket.instances = []; });
describe('console durable lifecycle subscription', () => {
  it('deduplicates, rejects foreign events, resumes from cursor and reconciles after reconnect', () => {
    vi.useFakeTimers(); vi.stubGlobal('WebSocket', Socket);
    useStore.setState({workspaceId: 'w', events: []});
    render(<Probe/>);
    const first = Socket.instances[0];
    expect(first.url).toContain('/ws/workspaces/w/events?after=0');
    act(() => { first.onopen?.(); first.emit(4); first.emit(4); first.emit(9, 'foreign'); });
    expect(screen.getByText('live:2')).toBeTruthy();
    expect(useStore.getState().events.map(event => event.seq)).toEqual([4]);
    act(() => first.onclose?.());
    expect(screen.getByText('disconnected:2')).toBeTruthy();
    act(() => vi.advanceTimersByTime(1000));
    const resumed = Socket.instances[1];
    expect(resumed.url).toContain('after=4');
    act(() => { resumed.onopen?.(); resumed.emit(4); resumed.emit(5); });
    expect(screen.getByText('live:4')).toBeTruthy();
    expect(useStore.getState().events.map(event => event.seq)).toEqual([4, 5]);
  });
  it('closes old workspace sockets, ignores late events and cancels reconnect on unmount', () => {
    vi.useFakeTimers(); vi.stubGlobal('WebSocket', Socket);
    useStore.setState({events: []});
    const view = render(<Probe/>);
    const first = Socket.instances[0];
    view.rerender(<Probe workspace="other"/>);
    expect(first.close).toHaveBeenCalledOnce();
    act(() => first.emit(20));
    expect(useStore.getState().events).toHaveLength(0);
    expect(Socket.instances[1].url).toContain('/other/events?after=0');
    act(() => Socket.instances[1].onerror?.());
    view.unmount();
    act(() => vi.advanceTimersByTime(3000));
    expect(Socket.instances).toHaveLength(2);
  });
});
