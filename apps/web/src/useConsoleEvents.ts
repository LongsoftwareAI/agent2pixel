import {useEffect, useState} from 'react';
import type {RuntimeEvent} from './types';
import {useStore} from './store';

type Connection = 'connecting' | 'live' | 'disconnected';

/** Durable lifecycle events, not model token streaming. Polling preferences do not stop this subscription. */
export function useConsoleEvents(workspaceId: string) {
  const [revision, setRevision] = useState(0);
  const [connection, setConnection] = useState<Connection>('connecting');
  useEffect(() => {
    if (!workspaceId || typeof WebSocket === 'undefined') return;
    let disposed = false;
    let cursor = 0;
    let socket: WebSocket | undefined;
    let retry: ReturnType<typeof setTimeout> | undefined;
    const connect = () => {
      if (disposed) return;
      setConnection('connecting');
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
      socket = new WebSocket(`${protocol}//${location.host}/ws/workspaces/${encodeURIComponent(workspaceId)}/events?after=${cursor}`);
      socket.onopen = () => {
        if (!disposed) {
          setConnection('live');
          // Reconcile an authoritative snapshot after every reconnect, even without new events.
          setRevision(value => value + 1);
        }
      };
      socket.onmessage = event => {
        if (disposed) return;
        let value: RuntimeEvent;
        try { value = JSON.parse(String(event.data)) as RuntimeEvent; } catch { return; }
        if (value.workspace_id !== workspaceId || !Number.isInteger(value.seq) || value.seq <= cursor) return;
        cursor = value.seq;
        useStore.getState().receive(value);
        setRevision(previous => previous + 1);
      };
      socket.onerror = () => {
        if (!disposed) setConnection('disconnected');
        socket?.close();
      };
      socket.onclose = () => {
        if (disposed) return;
        setConnection('disconnected');
        retry = setTimeout(connect, 1000);
      };
    };
    connect();
    return () => {
      disposed = true;
      if (retry !== undefined) clearTimeout(retry);
      socket?.close();
    };
  }, [workspaceId]);
  return {revision, connection};
}
