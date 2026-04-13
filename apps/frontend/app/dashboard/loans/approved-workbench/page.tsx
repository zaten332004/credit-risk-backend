'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { AlertCircle, Download, Loader2, RefreshCw } from 'lucide-react';
import { browserApiFetchAuth } from '@/lib/api/browser';
import { ApiError } from '@/lib/api/shared';
import { useI18n } from '@/components/i18n-provider';
import { getUserRole, type UserRole } from '@/lib/auth/token';
import { ListSearchInput } from '@/components/list-search-input';

type WorkbenchRow = {
  application_id: number;
  application_ref_no?: string | null;
  customer_id?: number | null;
  customer_name?: string | null;
  loan_status?: string | null;
  loan_type?: string | null;
  loan_purpose?: string | null;
  loan_amount?: number | null;
  loan_term?: number | null;
  interest_rate?: number | null;
  facility_id?: number | null;
  next_installment_no?: number | null;
  next_due_date?: string | null;
  installment_state?: string | null;
  installment_dpd?: number | null;
  next_total_due?: number | null;
  next_paid?: number | null;
  cumulative_paid?: number | null;
};

function formatMoney(n: number | null | undefined) {
  if (n == null || Number.isNaN(n)) return '—';
  return new Intl.NumberFormat('vi-VN').format(n);
}

function formatApiError(err: unknown): string {
  if (err instanceof ApiError) {
    return `${err.message} — ${err.url}${err.bodyText ? `\n${err.bodyText}` : ''}`;
  }
  return err instanceof Error ? err.message : String(err);
}

function normLoanStatus(s: string | null | undefined) {
  return String(s ?? '').trim().toLowerCase();
}

type LoanStatusScope = 'all' | 'approved' | 'disbursed';

export default function ApprovedLoanWorkbenchPage() {
  const { locale } = useI18n();
  const [role, setRole] = useState<UserRole | null>(null);
  const [rows, setRows] = useState<WorkbenchRow[]>([]);
  const [statusScope, setStatusScope] = useState<LoanStatusScope>('all');
  const [searchText, setSearchText] = useState('');
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const copy = useMemo(() => {
    const vi = {
      title: 'Hồ sơ vay đã duyệt',
      subtitle: 'Danh sách khoản đã duyệt / giải ngân và trạng thái kỳ thanh toán tiếp theo.',
      refresh: 'Làm mới',
      export: 'Xuất file CSV',
      exportBusy: 'Đang xuất...',
      filterApproved: 'Đã duyệt',
      filterDisbursed: 'Giải ngân',
      statusSelectPh: 'Tất cả trạng thái',
      searchPh: 'Tìm theo tên khách hàng hoặc mã hồ sơ...',
      showingRecords: (shown: number, total: number) => `Hiển thị ${shown} / ${total} hồ sơ`,
      loading: 'Đang tải...',
      empty: 'Chưa có dữ liệu.',
      cols: {
        ref: 'Số HSTD',
        customer: 'Khách hàng',
        amount: 'Số tiền vay',
        term: 'Tháng',
        rate: 'Lãi %',
        status: 'Trạng thái',
        nextDue: 'Đến hạn kỳ tiếp',
        nextDueAmt: 'Phải trả kỳ',
        paidCum: 'Đã trả lũy kế',
        dpd: 'DPD',
      },
    };
    const en = {
      title: 'Approved loan applications',
      subtitle: 'Approved or disbursed facilities and the next installment snapshot.',
      refresh: 'Refresh',
      export: 'Export CSV',
      exportBusy: 'Exporting...',
      filterApproved: 'Approved',
      filterDisbursed: 'Disbursed',
      statusSelectPh: 'All statuses',
      searchPh: 'Search by customer name or application ref...',
      showingRecords: (shown: number, total: number) => `Showing ${shown} / ${total} records`,
      loading: 'Loading...',
      empty: 'No rows yet.',
      cols: {
        ref: 'App ref',
        customer: 'Customer',
        amount: 'Loan amount',
        term: 'Months',
        rate: 'Rate %',
        status: 'Status',
        nextDue: 'Next due',
        nextDueAmt: 'Next installment',
        paidCum: 'Cumulative paid',
        dpd: 'DPD',
      },
    };
    return locale === 'en' ? en : vi;
  }, [locale]);

  useEffect(() => {
    setRole(getUserRole());
  }, []);

  const canExport = role === 'admin' || role === 'manager';

  const statusFiltered = useMemo(() => {
    if (statusScope === 'all') return rows;
    return rows.filter((r) => {
      const st = normLoanStatus(r.loan_status);
      if (statusScope === 'approved') return st === 'approved';
      return st === 'disbursed';
    });
  }, [rows, statusScope]);

  const filteredRows = useMemo(() => {
    const q = searchText.trim().toLowerCase();
    if (!q) return statusFiltered;
    return statusFiltered.filter((r) => {
      const name = String(r.customer_name ?? '').toLowerCase();
      const ref = String(r.application_ref_no ?? r.application_id ?? '').toLowerCase();
      return name.includes(q) || ref.includes(q);
    });
  }, [statusFiltered, searchText]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await browserApiFetchAuth('/customers/approved-loan-workbench?limit=500', { method: 'GET' });
      const list = Array.isArray(data) ? data : [];
      setRows(list as WorkbenchRow[]);
    } catch (e) {
      setError(formatApiError(e));
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleExportCsv = async () => {
    const base = (process.env.NEXT_PUBLIC_API_BASE_URL ?? '').replace(/\/$/, '');
    if (!base) {
      setError('Missing NEXT_PUBLIC_API_BASE_URL');
      return;
    }
    setExporting(true);
    setError(null);
    try {
      const token =
        typeof window !== 'undefined' ? window.localStorage.getItem('accessToken') : null;
      const res = await fetch(`${base}/customers/approved-loan-workbench/export?limit=500`, {
        method: 'GET',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text}` : ''}`);
      }
      const blob = await res.blob();
      const cd = res.headers.get('Content-Disposition');
      let filename = 'approved-loan-workbench.csv';
      const m = cd?.match(/filename="([^"]+)"/i) ?? cd?.match(/filename=([^;\s]+)/i);
      if (m?.[1]) filename = m[1].trim();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.rel = 'noopener';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <Card>
        <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            <CardTitle>{copy.title}</CardTitle>
            <CardDescription>{copy.subtitle}</CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              <span className="ml-2">{copy.refresh}</span>
            </Button>
            {canExport ? (
              <Button
                type="button"
                variant="secondary"
                size="icon"
                className="h-9 w-9 shrink-0 rounded-md border border-border bg-muted/80 text-foreground hover:bg-muted"
                onClick={() => void handleExportCsv()}
                disabled={exporting}
                title={copy.export}
                aria-label={copy.export}
              >
                {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              </Button>
            ) : null}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {error ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="whitespace-pre-wrap">{error}</AlertDescription>
            </Alert>
          ) : null}
          <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-center">
            <ListSearchInput
              placeholder={copy.searchPh}
              value={searchText}
              onChange={setSearchText}
              disabled={loading}
              aria-label={copy.searchPh}
            />
            <Select value={statusScope} onValueChange={(v) => setStatusScope(v as LoanStatusScope)}>
              <SelectTrigger className="w-full sm:w-[220px] shrink-0" aria-label={copy.cols.status}>
                <SelectValue placeholder={copy.statusSelectPh} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{copy.statusSelectPh}</SelectItem>
                <SelectItem value="approved">{copy.filterApproved}</SelectItem>
                <SelectItem value="disbursed">{copy.filterDisbursed}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <p className="text-sm text-muted-foreground">
            {copy.showingRecords(filteredRows.length, statusFiltered.length)}
          </p>
          <div className="rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{copy.cols.ref}</TableHead>
                  <TableHead>{copy.cols.customer}</TableHead>
                  <TableHead className="text-right">{copy.cols.amount}</TableHead>
                  <TableHead className="text-right">{copy.cols.term}</TableHead>
                  <TableHead className="text-right">{copy.cols.rate}</TableHead>
                  <TableHead>{copy.cols.status}</TableHead>
                  <TableHead>{copy.cols.nextDue}</TableHead>
                  <TableHead className="text-right">{copy.cols.nextDueAmt}</TableHead>
                  <TableHead className="text-right">{copy.cols.paidCum}</TableHead>
                  <TableHead className="text-right">{copy.cols.dpd}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {!loading && filteredRows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center text-muted-foreground">
                      {copy.empty}
                    </TableCell>
                  </TableRow>
                ) : null}
                {filteredRows.map((r) => (
                  <TableRow key={r.application_id}>
                    <TableCell className="font-mono text-xs">
                      {r.application_ref_no ?? r.application_id}
                    </TableCell>
                    <TableCell>{r.customer_name ?? '—'}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatMoney(r.loan_amount ?? null)}</TableCell>
                    <TableCell className="text-right tabular-nums">{r.loan_term ?? '—'}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {r.interest_rate != null ? r.interest_rate : '—'}
                    </TableCell>
                    <TableCell>{r.loan_status ?? '—'}</TableCell>
                    <TableCell className="text-xs">{r.next_due_date ?? '—'}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatMoney(r.next_total_due ?? null)}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(r.cumulative_paid ?? null)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{r.installment_dpd ?? 0}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {copy.loading}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
