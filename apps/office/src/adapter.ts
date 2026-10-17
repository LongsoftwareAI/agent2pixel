import { OfficeStore } from '../../../vendor/habblaud/client/src/net/store';
import type { OfficeSnapshot } from '../../../vendor/habblaud/shared/types';

export type Projection = OfficeSnapshot & { seq?: number; source?: string };
/** Reject malformed network data instead of quietly populating a demonstration. */
export function validateProjection(value: unknown): Projection {
  const s = value as Projection;
  if (!s || !Number.isFinite(s.rev) || !Number.isFinite(s.serverTime) || !Array.isArray(s.rooms) || !Array.isArray(s.agents) || !Array.isArray(s.accounts) || !s.meta || s.meta.demo !== false) {
    throw new Error('Invalid live office projection');
  }
  const roomIds = new Set(s.rooms.map(r => r.id));
  if (s.agents.some(a => !a.id || !roomIds.has(a.roomId) || a.kind !== 'main' || a.provider !== 'agentverse' || !Array.isArray(a.recent) || !Array.isArray(a.tasks) || !a.stats)) {
    throw new Error('Invalid agent projection');
  }
  return s;
}

/** Original Habblaud store, with live AgentVerse transport only. Never enables DemoSimulator. */
export class AgentVerseStore extends OfficeStore {
  constructor() {
    super({ mock: false, eventSource: url => new EventSource(url) });
  }
  override applySnapshot(snapshot: OfficeSnapshot): void {
    super.applySnapshot(validateProjection(snapshot));
  }
  override async agentHistory(id: string) {
    return this.agent(id)?.recent ?? [];
  }
  async bootstrap(fetcher: typeof fetch = fetch): Promise<void> {
    try {
      const response = await fetcher('/api/office/snapshot', { cache: 'no-store' });
      if (!response.ok) throw new Error(`Office API returned ${response.status}`);
      this.applySnapshot(validateProjection(await response.json()));
    } finally {
      // SSE remains active when the first HTTP request fails; upstream exposes reconnection status.
      this.connect();
    }
  }
}
