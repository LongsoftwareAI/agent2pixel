type Accounting = {
    token_accounting?: unknown;
    accounting_counts?: unknown;
    tokens_by_accounting?: unknown;
};
const labels: Record<string, string> = {
    estimated: 'Ước tính token runtime',
    provider: 'Token do provider báo cáo',
    unknown: 'Nguồn đếm token chưa xác định',
    mixed: 'Token từ nhiều nguồn đếm',
};
export function accountingLabel(value: unknown) {
    return labels[String(value)] ?? labels.unknown;
}
export function TokenAccounting({ value }: {
    value?: Accounting | null;
}) {
    const counts = (value?.accounting_counts ?? {}) as Record<string, unknown>;
    const tokens = (value?.tokens_by_accounting ?? {}) as Record<string, unknown>;
    return <div className="c-muted c-token-accounting">
    <strong>
        {accountingLabel(value?.token_accounting)}
    </strong>
    {(['estimated', 'provider', 'unknown'] as const).map(kind => typeof counts[kind] === 'number' && Number(counts[kind]) > 0 &&
            <span key={kind}> · {accountingLabel(kind)}: {String(counts[kind])} lượt / {String(tokens[kind] ?? '—')} token</span>)}
    <span> · Token không phải hóa đơn chi phí.</span>
  </div>;
}
