'use client';

import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Search, MoreHorizontal, Loader2, RefreshCw, AlertCircle, Download, Trash2 } from 'lucide-react';
import { browserApiFetchAuth } from '@/lib/api/browser';
import { ApiError } from '@/lib/api/shared';
import { useI18n } from '@/components/i18n-provider';
import { ListPagination } from '@/components/list-pagination';
import { downloadCsvFile } from '@/lib/export/csv';

type Locale = 'vi' | 'en';

const PIN_COPY: Record<
  Locale,
  {
    section_title: string;
    section_hint: string;
    pin_status: string;
    pin_set: string;
    pin_not_set: string;
    new_pin: string;
    confirm_pin: string;
    save_pin: string;
    pin_invalid: string;
    pin_mismatch: string;
    pin_saved: string;
    delete_user: string;
    delete_confirm: string;
  }
> = {
  vi: {
    section_title: 'Mã PIN tài khoản',
    section_hint:
      'Đặt hoặc thay mã PIN 6 chữ số để người dùng dùng cho quên mật khẩu và thao tác nhạy cảm. Không hiển thị lại PIN sau khi lưu.',
    pin_status: 'Trạng thái PIN',
    pin_set: 'Đã đặt PIN',
    pin_not_set: 'Chưa đặt PIN',
    new_pin: 'Mã PIN mới (6 số)',
    confirm_pin: 'Xác nhận PIN',
    save_pin: 'Lưu mã PIN',
    pin_invalid: 'PIN phải gồm đúng 6 chữ số.',
    pin_mismatch: 'Hai lần nhập PIN không khớp.',
    pin_saved: 'Đã cập nhật mã PIN.',
    delete_user: 'Xóa người dùng',
    delete_confirm: 'Xóa vĩnh viễn người dùng này? Hành động không thể hoàn tác.',
  },
  en: {
    section_title: 'Account PIN',
    section_hint:
      'Set or replace the 6-digit PIN for forgot-password and sensitive actions. The PIN is never shown after saving.',
    pin_status: 'PIN status',
    pin_set: 'PIN is set',
    pin_not_set: 'PIN not set',
    new_pin: 'New PIN (6 digits)',
    confirm_pin: 'Confirm PIN',
    save_pin: 'Save PIN',
    pin_invalid: 'PIN must be exactly 6 digits.',
    pin_mismatch: 'PIN entries do not match.',
    pin_saved: 'PIN updated.',
    delete_user: 'Delete user',
    delete_confirm: 'Permanently delete this user? This cannot be undone.',
  },
};

type AdminUserRow = {
  id: string;
  name: string;
  email: string;
  role: string;
  isActive: boolean;
  hasPin: boolean;
  raw: Record<string, unknown>;
};

function normalizeUser(item: unknown): AdminUserRow | null {
  if (!item || typeof item !== 'object') return null;
  const rec = item as Record<string, unknown>;
  const id = String(rec.user_id ?? rec.userId ?? rec.id ?? '').trim();
  if (!id) return null;
  const name = String(rec.name ?? rec.full_name ?? rec.fullName ?? rec.username ?? id).trim();
  const email = String(rec.email ?? '').trim() || '—';
  const role = String(rec.role ?? rec.user_role ?? rec.userRole ?? '').trim().toLowerCase() || 'viewer';
  const isActiveRaw = rec.is_active ?? rec.isActive ?? rec.active ?? rec.status;
  const activeStatuses = new Set(['approved', 'verified', 'active', 'true']);
  const isActive =
    typeof isActiveRaw === 'boolean'
      ? isActiveRaw
      : activeStatuses.has(String(isActiveRaw ?? '').toLowerCase());
  const hasPin = Boolean(rec.has_pin ?? rec.hasPin);
  return { id, name, email, role, isActive, hasPin, raw: rec };
}

function formatApiError(err: unknown): string {
  if (err instanceof ApiError) {
    return `${err.message} — ${err.url}${err.bodyText ? `\n${err.bodyText}` : ''}`;
  }
  return err instanceof Error ? err.message : String(err);
}

function getRoleBadgeClass(role: string) {
  const normalized = String(role || '').toLowerCase();
  if (normalized === 'admin') return 'border-violet-300 bg-violet-50 text-violet-700';
  if (normalized === 'manager') return 'border-sky-300 bg-sky-50 text-sky-700';
  if (normalized === 'analyst') return 'border-indigo-300 bg-indigo-50 text-indigo-700';
  if (normalized === 'viewer') return 'border-slate-300 bg-slate-50 text-slate-700';
  return 'border-slate-300 bg-slate-50 text-slate-700';
}

function getStatusBadgeClass(isActive: boolean) {
  return isActive
    ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
    : 'border-amber-300 bg-amber-50 text-amber-700';
}

export default function AdminUsersPage() {
  const PAGE_SIZE = 15;
  const { t, locale } = useI18n();
  const pinT = PIN_COPY[locale === 'en' ? 'en' : 'vi'];

  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [query, setQuery] = useState('');
  const [scope, setScope] = useState('all');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [selectedUser, setSelectedUser] = useState<AdminUserRow | null>(null);
  const [selectedRole, setSelectedRole] = useState('');
  const [pinNew, setPinNew] = useState('');
  const [pinConfirm, setPinConfirm] = useState('');
  const [pinMessage, setPinMessage] = useState<string | null>(null);

  const loadUsers = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await browserApiFetchAuth('/admin/users', { method: 'GET' });
      const rawList = Array.isArray(data)
        ? data
        : Array.isArray((data as { items?: unknown }).items)
          ? (data as { items: unknown[] }).items
          : Array.isArray((data as { value?: unknown }).value)
            ? (data as { value: unknown[] }).value
            : [];
      const rows = rawList.map(normalizeUser).filter(Boolean) as AdminUserRow[];
      setUsers(rows);
    } catch (err) {
      setError(formatApiError(err));
      setUsers([]);
    } finally {
      setIsLoading(false);
    }
  };

  const searchUsers = async (rawQuery: string) => {
    const q = rawQuery.trim();
    if (!q) return loadUsers();
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set('name_contains', q);
      const data = await browserApiFetchAuth(`/admin/users/search?${params.toString()}`, { method: 'GET' });
      const rawList = Array.isArray(data)
        ? data
        : Array.isArray((data as { items?: unknown }).items)
          ? (data as { items: unknown[] }).items
          : Array.isArray((data as { value?: unknown }).value)
            ? (data as { value: unknown[] }).value
            : [];
      const rows = rawList.map(normalizeUser).filter(Boolean) as AdminUserRow[];
      setUsers(rows);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  const setUserActive = async (userId: string, isActive: boolean) => {
    setIsLoading(true);
    setError(null);
    try {
      await browserApiFetchAuth(`/admin/users/${encodeURIComponent(userId)}/status?is_active=${isActive ? 'true' : 'false'}`, {
        method: 'PATCH',
      });
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, isActive } : u)));
      setSelectedUser((prev) => (prev && prev.id === userId ? { ...prev, isActive } : prev));
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  const setUserRole = async (userId: string, role: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = (await browserApiFetchAuth(`/admin/users/${encodeURIComponent(userId)}/role`, {
        method: 'PATCH',
        body: { role },
      })) as { role?: string };
      const updatedRole = String(response?.role || role).toLowerCase();
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, role: updatedRole } : u)));
      setSelectedUser((prev) => (prev && prev.id === userId ? { ...prev, role: updatedRole } : prev));
      setSelectedRole(updatedRole);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  const deleteUser = async (userId: string) => {
    if (!window.confirm(pinT.delete_confirm)) return;
    setIsLoading(true);
    setError(null);
    try {
      await browserApiFetchAuth(`/admin/users/${encodeURIComponent(userId)}`, { method: 'DELETE' });
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      setSelectedUser(null);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  const saveUserPin = async () => {
    if (!selectedUser) return;
    const a = pinNew.replace(/\D/g, '');
    const b = pinConfirm.replace(/\D/g, '');
    setPinMessage(null);
    if (a.length !== 6) {
      setError(pinT.pin_invalid);
      return;
    }
    if (a !== b) {
      setError(pinT.pin_mismatch);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const updated = (await browserApiFetchAuth(`/admin/users/${encodeURIComponent(selectedUser.id)}/pin`, {
        method: 'POST',
        body: { pin: a },
      })) as { has_pin?: boolean };
      const hasPin = Boolean(updated?.has_pin ?? true);
      setUsers((prev) => prev.map((u) => (u.id === selectedUser.id ? { ...u, hasPin } : u)));
      setSelectedUser((prev) => (prev && prev.id === selectedUser.id ? { ...prev, hasPin } : prev));
      setPinNew('');
      setPinConfirm('');
      setPinMessage(pinT.pin_saved);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void searchUsers(query);
    }, 250);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  const filtered = useMemo(() => {
    if (scope === 'all') return users;
    if (scope === 'active') return users.filter((u) => u.isActive);
    return users.filter((u) => !u.isActive);
  }, [users, scope]);

  useEffect(() => {
    setPage(1);
  }, [query, scope, users.length]);

  useEffect(() => {
    setSelectedRole(selectedUser?.role ?? '');
    setPinNew('');
    setPinConfirm('');
    setPinMessage(null);
  }, [selectedUser]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const stats = useMemo(() => {
    const total = users.length;
    const active = users.filter((u) => u.isActive).length;
    const managers = filtered.filter((u) => u.role === 'manager').length;
    const analysts = filtered.filter((u) => u.role === 'analyst').length;
    return { total, active, managers, analysts };
  }, [users, filtered]);

  const roleLabel = (role: string) => {
    switch (role.toLowerCase()) {
      case 'manager':
        return t('role.manager');
      case 'analyst':
        return t('role.analyst');
      case 'admin':
        return t('role.admin');
      case 'viewer':
        return t('role.viewer');
      default:
        return role;
    }
  };

  const handleExportCsv = () => {
    downloadCsvFile(
      'admin-users',
      [t('common.name'), t('common.email'), t('common.role'), t('common.status'), 'ID', pinT.pin_status],
      filtered.map((user) => [
        user.name,
        user.email,
        roleLabel(user.role),
        t(user.isActive ? 'status.active' : 'status.inactive'),
        user.id,
        user.hasPin ? pinT.pin_set : pinT.pin_not_set,
      ]),
    );
  };

  const detailRows = useMemo(() => {
    if (!selectedUser) return [];
    const raw = selectedUser.raw ?? {};
    return [
      { label: 'ID', value: selectedUser.id },
      { label: t('common.name'), value: selectedUser.name },
      { label: t('common.email'), value: selectedUser.email },
      { label: t('common.role'), value: roleLabel(selectedUser.role) },
      { label: t('common.status'), value: t(selectedUser.isActive ? 'status.active' : 'status.inactive') },
      { label: pinT.pin_status, value: selectedUser.hasPin ? pinT.pin_set : pinT.pin_not_set },
      { label: 'Username', value: String(raw.username ?? raw.user_name ?? '—') },
      { label: 'Created at', value: String(raw.created_at ?? raw.createdAt ?? '—') },
    ];
  }, [selectedUser, t, pinT]);

  const pinReady = pinNew.replace(/\D/g, '').length === 6 && pinConfirm.replace(/\D/g, '').length === 6;

  return (
    <div className="flex flex-col gap-6 p-6 bg-[#f4f7fc]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">{t('admin.users.title')}</h1>
          <p className="text-muted-foreground mt-2">{t('admin.users.desc')}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="icon" onClick={handleExportCsv} aria-label="Export CSV">
            <Download className="h-4 w-4" />
          </Button>
          <Button variant="outline" onClick={() => void loadUsers()} disabled={isLoading}>
            {isLoading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            {t('common.refresh')}
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="whitespace-pre-wrap">{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {(
          [
            { titleKey: 'admin.users.total', count: stats.total },
            { titleKey: 'common.active', count: stats.active },
            { titleKey: 'admin.users.managers', count: stats.managers },
            { titleKey: 'admin.users.analysts', count: stats.analysts },
          ] as const
        ).map((stat, idx) => (
          <Card key={idx}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">{t(stat.titleKey)}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stat.count}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-border/80 bg-card shadow-sm">
        <CardHeader className="space-y-3 pb-3">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div>
              <CardTitle>{t('admin.users.list_title')}</CardTitle>
              <CardDescription>
                {t('common.showing')} {filtered.length} {t('admin.users.items')}
              </CardDescription>
            </div>
            <div className="w-full md:w-80">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder={t('admin.users.search_ph')}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <Tabs value={scope} onValueChange={setScope}>
              <TabsList>
                <TabsTrigger value="all">{t('common.all')}</TabsTrigger>
                <TabsTrigger value="active">{t('common.active')}</TabsTrigger>
                <TabsTrigger value="inactive">{t('common.inactive')}</TabsTrigger>
              </TabsList>
              <TabsContent value="all" />
              <TabsContent value="active" />
              <TabsContent value="inactive" />
            </Tabs>
            <div />
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="overflow-x-auto rounded-xl border border-black/70 bg-white">
            <Table className="min-w-[820px] w-full">
              <TableHeader>
                <TableRow className="bg-muted/35 hover:bg-muted/35">
                  <TableHead className="py-1.5">{t('common.name')}</TableHead>
                  <TableHead className="py-1.5">{t('common.email')}</TableHead>
                  <TableHead className="py-1.5">{t('common.role')}</TableHead>
                  <TableHead className="py-1.5">{t('common.status')}</TableHead>
                  <TableHead className="py-1.5 text-right">{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paged.map((user) => (
                  <TableRow
                    key={user.id}
                    className="cursor-pointer border-b border-black/15 hover:bg-muted/30"
                    onClick={() => setSelectedUser(user)}
                  >
                    <TableCell className="py-1.5 font-medium">
                      <div className="flex flex-col">
                        <span>{user.name}</span>
                        <span className="text-xs text-muted-foreground font-mono">{user.id}</span>
                      </div>
                    </TableCell>
                    <TableCell className="py-1.5">{user.email}</TableCell>
                    <TableCell className="py-1.5">
                      <Badge variant="outline" className={getRoleBadgeClass(user.role)}>
                        {roleLabel(user.role)}
                      </Badge>
                    </TableCell>
                    <TableCell className="py-1.5">
                      <Badge variant="outline" className={getStatusBadgeClass(user.isActive)}>
                        {t(user.isActive ? 'status.active' : 'status.inactive')}
                      </Badge>
                    </TableCell>
                    <TableCell className="py-1.5 text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 px-1.5"
                            disabled={isLoading}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              void setUserActive(user.id, !user.isActive);
                            }}
                            className={!user.isActive ? 'text-green-700' : 'text-red-600'}
                          >
                            {user.isActive ? t('admin.users.deactivate') : t('admin.users.activate')}
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
                {paged.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="py-10 text-center text-muted-foreground">
                      {isLoading ? t('common.loading') : t('common.no_results')}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
          <div className="mt-1">
            <ListPagination page={page} totalPages={totalPages} onPageChange={setPage} />
          </div>
        </CardContent>
      </Card>

      <Dialog
        open={Boolean(selectedUser)}
        onOpenChange={(open) => {
          if (!open) setSelectedUser(null);
        }}
      >
        <DialogContent className="!w-[94vw] !max-w-[1150px] max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>
              {t('admin.users.list_title')} - {selectedUser?.name}
            </DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 max-h-[68vh] overflow-y-auto pr-1">
            {detailRows.map((item) => (
              <div key={item.label} className="rounded-lg border bg-secondary/40 p-3">
                <p className="text-xs uppercase tracking-wider text-muted-foreground">{item.label}</p>
                <p className="mt-1 text-sm font-medium break-words">{String(item.value ?? '—')}</p>
              </div>
            ))}
          </div>

          {selectedUser ? (
            <div className="rounded-lg border border-dashed bg-muted/15 p-4 space-y-3 shrink-0">
              <div>
                <p className="text-sm font-semibold">{pinT.section_title}</p>
                <p className="text-xs text-muted-foreground mt-1">{pinT.section_hint}</p>
              </div>
              {pinMessage ? <p className="text-sm text-emerald-700">{pinMessage}</p> : null}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs uppercase tracking-wider text-muted-foreground">{pinT.new_pin}</label>
                  <Input
                    type="password"
                    inputMode="numeric"
                    autoComplete="new-password"
                    maxLength={6}
                    value={pinNew}
                    onChange={(e) => setPinNew(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="••••••"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs uppercase tracking-wider text-muted-foreground">{pinT.confirm_pin}</label>
                  <Input
                    type="password"
                    inputMode="numeric"
                    autoComplete="new-password"
                    maxLength={6}
                    value={pinConfirm}
                    onChange={(e) => setPinConfirm(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="••••••"
                  />
                </div>
              </div>
              <Button type="button" variant="secondary" disabled={isLoading || !pinReady} onClick={() => void saveUserPin()}>
                {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                {pinT.save_pin}
              </Button>
            </div>
          ) : null}

          <DialogFooter className="gap-2 sm:gap-0 flex-col sm:flex-row sm:justify-between sm:items-center">
            {selectedUser ? (
              <div className="mr-auto flex flex-wrap items-center gap-2">
                <Select value={selectedRole || selectedUser.role} onValueChange={setSelectedRole}>
                  <SelectTrigger className="w-[220px]">
                    <SelectValue placeholder={t('common.role')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">{t('role.admin')}</SelectItem>
                    <SelectItem value="manager">{t('role.manager')}</SelectItem>
                    <SelectItem value="analyst">{t('role.analyst')}</SelectItem>
                    <SelectItem value="viewer">{t('role.viewer')}</SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  variant="outline"
                  className="min-w-[140px]"
                  onClick={() => void setUserRole(selectedUser.id, selectedRole || selectedUser.role)}
                  disabled={
                    isLoading ||
                    !(selectedRole || selectedUser.role) ||
                    (selectedRole || selectedUser.role) === selectedUser.role
                  }
                >
                  {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  {t('common.save_changes')}
                </Button>
              </div>
            ) : null}
            <div className="flex flex-wrap items-center justify-end gap-2 w-full sm:w-auto">
              {selectedUser ? (
                <>
                  <Button
                    variant={selectedUser.isActive ? 'destructive' : 'default'}
                    onClick={() => void setUserActive(selectedUser.id, !selectedUser.isActive)}
                    disabled={isLoading}
                  >
                    {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    {selectedUser.isActive ? t('admin.users.deactivate') : t('admin.users.activate')}
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => void deleteUser(selectedUser.id)}
                    disabled={isLoading}
                    className="gap-1"
                  >
                    <Trash2 className="h-4 w-4" />
                    {pinT.delete_user}
                  </Button>
                </>
              ) : null}
              <Button variant="outline" onClick={() => setSelectedUser(null)}>
                {t('common.close')}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
