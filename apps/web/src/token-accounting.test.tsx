import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { TokenAccounting, accountingLabel } from './TokenAccounting';
afterEach(cleanup);
describe('runtime token provenance', () => {
    it('labels estimates without presenting provider or billing certainty', () => {
        render(<TokenAccounting value={{
            token_accounting: 'estimated', accounting_counts: {
                estimated: 1, provider: 0, unknown: 0
            }, tokens_by_accounting: {
                estimated: 40, provider: 0, unknown: 0
            }
        }}/>);
        expect(screen.getByText('Ước tính token runtime')).toBeTruthy();
        expect(screen.getByText(/1 lượt \/ 40 token/)).toBeTruthy();
        expect(screen.queryByText('Token do provider báo cáo')).toBeNull();
        expect(screen.getByText(/Token không phải hóa đơn/)).toBeTruthy();
    });
    it('shows mixed counts with separately attributed tokens, and unknown fallback', () => {
        render(<TokenAccounting value={{
            token_accounting: 'mixed', accounting_counts: {
                estimated: 2, provider: 1, unknown: 1
            }, tokens_by_accounting: {
                estimated: 80, provider: 30, unknown: 10
            }
        }}/>);
        expect(screen.getByText('Token từ nhiều nguồn đếm')).toBeTruthy();
        expect(screen.getByText(/Ước tính token runtime: 2 lượt \/ 80 token/)).toBeTruthy();
        expect(screen.getByText(/Token do provider báo cáo: 1 lượt \/ 30 token/)).toBeTruthy();
        expect(screen.getByText(/Nguồn đếm token chưa xác định: 1 lượt \/ 10 token/)).toBeTruthy();
        expect(accountingLabel(undefined)).toBe('Nguồn đếm token chưa xác định');
    });
});
