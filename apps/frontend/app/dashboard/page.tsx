'use client';

import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, Users, AlertCircle, PieChart } from 'lucide-react';
import { getUserRole, type UserRole } from '@/lib/auth/token';
import { useI18n } from '@/components/i18n-provider';
import { browserApiFetchAuth } from '@/lib/api/browser';
import { formatUserFacingApiError } from '@/lib/api/format-api-error';
import { notifyError } from '@/lib/notify';
import { formatDateTimeVietnam, formatDateVietnam } from '@/lib/datetime';
import { formatCompactVnd } from '@/lib/money';
import { RECHARTS_GRID_STROKE, RECHARTS_LEGEND_WRAPPER_STYLE, RECHARTS_TICK_MD } from '@/lib/chart-theme';

type PortfolioKPI = {
  total_exposure: number;
  avg_pd: number;
  expected_loss: number;
  npl_ratio: number;
  var_99: number;
};

type PortfolioTrend = { points: Array<{ timestamp: string; value: number }> };
type RiskDistribution = { chart_data: Array<{ bucket: string; count?: number }> };
type AlertItem = { alert_id: number; alert_type: string; severity: string; message: string; created_at: string; customer_name?: string | null };

const KPICard = ({ title, value, icon: Icon }: { title: string; value: string; icon: any }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium">{title}</CardTitle>
      <Icon className="h-4 w-4 text-accent" />
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold">{value}</div>
    </CardContent>
  </Card>
);

function roleLabel(role: UserRole | null, t: (key: string) => string) {
  switch (role) {
    case 'admin':
      return t('role.admin');
    case 'manager':
      return t('role.manager');
    case 'analyst':
      return t('role.analyst');
    case 'viewer':
      return t('role.viewer');
    default:
      return '—';
  }
}

export default function DashboardPage() {
  const role = getUserRole();
  const { locale, t } = useI18n();
  const [kpi, setKpi] = useState<PortfolioKPI | null>(null);
  const [trendData, setTrendData] = useState<Array<{ month: string; value: number; score: number }>>([]);
  const [recentAlerts, setRecentAlerts] = useState<AlertItem[]>([]);
  const [openAlertsCount, setOpenAlertsCount] = useState(0);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState(0);
  const [pendingCustomerApplicationsCount, setPendingCustomerApplicationsCount] = useState(0);
  const [activeUsersCount, setActiveUsersCount] = useState(0);
  const [customerCount, setCustomerCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [kpiData, trend, dist, alerts] = await Promise.all([
          browserApiFetchAuth<PortfolioKPI>('/portfolio/kpi', { method: 'GET' }),
          browserApiFetchAuth<PortfolioTrend>('/portfolio/trend?metric=total_exposure&interval=month', { method: 'GET' }),
          browserApiFetchAuth<RiskDistribution>('/portfolio/risk-distribution', { method: 'GET' }),
          browserApiFetchAuth<AlertItem[]>('/alerts?status=open', { method: 'GET' }),
        ]);
        if (cancelled) return;

        setKpi(kpiData);
        const distCountMap = Object.fromEntries((dist.chart_data || []).map((x) => [x.bucket, Number(x.count || 0)]));
        const total = Math.max(1, Number(distCountMap.low || 0) + Number(distCountMap.medium || 0) + Number(distCountMap.high || 0));
        const avgScore = ((Number(distCountMap.low || 0) * 85) + (Number(distCountMap.medium || 0) * 65) + (Number(distCountMap.high || 0) * 35)) / total;
        setTrendData((trend.points || []).map((item) => ({
          month: formatDateVietnam(item.timestamp, locale, { month: 'short' }),
          value: Number(item.value || 0),
          score: Number(avgScore.toFixed(1)),
        })));
        setRecentAlerts((alerts || []).slice(0, 4));
        setOpenAlertsCount((alerts || []).length);

        if (role === 'admin') {
          const [pending, activeUsers] = await Promise.all([
            browserApiFetchAuth<any[]>('/auth/register/list?status_filter=pending', { method: 'GET' }),
            browserApiFetchAuth<any[]>('/admin/users?status_filter=active', { method: 'GET' }),
          ]);
          if (!cancelled) {
            setPendingApprovalsCount((pending || []).length);
            setActiveUsersCount((activeUsers || []).length);
          }
        } else if (role === 'manager') {
          const pendingCustomers = await browserApiFetchAuth<{ total: number }>(
            '/customers?page=1&application_status=pending',
            { method: 'GET' },
          );
          if (!cancelled) setPendingCustomerApplicationsCount(Number(pendingCustomers?.total || 0));
        }

        const customers = await browserApiFetchAuth<{ total: number }>('/customers?page=1', { method: 'GET' });
        if (!cancelled) setCustomerCount(Number(customers?.total || 0));
      } catch (err) {
        if (!cancelled) notifyError(formatUserFacingApiError(err));
      }
    };
    void load();
    return () => { cancelled = true; };
  }, [locale, role]);

  const cards = useMemo(() => {
    const portfolioScore = Math.round((1 - Number(kpi?.avg_pd || 0)) * 100);
    const health = (Number(kpi?.npl_ratio || 0) < 0.1)
      ? (locale === 'vi' ? 'Tốt' : 'Good')
      : (Number(kpi?.npl_ratio || 0) < 0.2 ? (locale === 'vi' ? 'Theo dõi' : 'Watch') : (locale === 'vi' ? 'Rủi ro' : 'Risk'));
    return [
      { title: locale === 'vi' ? 'Điểm danh mục' : 'Portfolio score', value: String(portfolioScore), icon: TrendingUp },
      { title: locale === 'vi' ? 'Khách hàng' : 'Customers', value: String(customerCount), icon: Users },
      { title: locale === 'vi' ? 'Cảnh báo mở' : 'Open alerts', value: String(openAlertsCount), icon: AlertCircle },
      {
        title:
          role === 'admin'
            ? (locale === 'vi' ? 'Chờ phê duyệt' : 'Pending approvals')
            : role === 'manager'
              ? (locale === 'vi' ? 'Hồ sơ chưa phê duyệt của khách hàng' : 'Customer applications pending approval')
              : (locale === 'vi' ? 'Sức khỏe hệ thống' : 'System health'),
        value:
          role === 'admin'
            ? String(pendingApprovalsCount)
            : role === 'manager'
              ? String(pendingCustomerApplicationsCount)
              : health,
        icon: PieChart,
      },
      ...(role === 'admin' ? [{ title: locale === 'vi' ? 'Người dùng hoạt động' : 'Active users', value: String(activeUsersCount), icon: Users }] : []),
    ];
  }, [kpi?.avg_pd, kpi?.npl_ratio, locale, customerCount, openAlertsCount, pendingApprovalsCount, pendingCustomerApplicationsCount, activeUsersCount, role]);

  return (
    <div className="flex flex-col gap-8 p-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">{t('dashboard.title')}</h1>
        <p className="text-muted-foreground mt-2">{t('dashboard.welcome')} - {roleLabel(role, t)}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.slice(0, 4).map((metric, idx) => <KPICard key={idx} title={metric.title} value={metric.value} icon={metric.icon} />)}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>{locale === 'vi' ? 'Xu hướng danh mục' : 'Portfolio trend'}</CardTitle>
            <CardDescription>{locale === 'vi' ? 'Giá trị danh mục theo thời gian và điểm trung bình' : 'Portfolio value over time and average score'}</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trendData} margin={{ top: 12, right: 28, left: 20, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={RECHARTS_GRID_STROKE} />
                <XAxis dataKey="month" tick={RECHARTS_TICK_MD} />
                <YAxis yAxisId="left" tickFormatter={(v) => formatCompactVnd(Number(v), locale === 'vi' ? 'vi' : 'en')} width={72} tickMargin={8} tick={RECHARTS_TICK_MD} />
                <YAxis yAxisId="right" orientation="right" width={44} tickMargin={8} tick={RECHARTS_TICK_MD} />
                <Tooltip formatter={(value: number, name: string) => name === 'value' ? [formatCompactVnd(Number(value), locale === 'vi' ? 'vi' : 'en'), locale === 'vi' ? 'Giá trị danh mục' : 'Portfolio value'] : [value, locale === 'vi' ? 'Điểm trung bình' : 'Average score']} />
                <Legend wrapperStyle={RECHARTS_LEGEND_WRAPPER_STYLE} />
                <Line yAxisId="left" type="monotone" dataKey="value" stroke="#0ea5a6" strokeWidth={2} name={locale === 'vi' ? 'Giá trị danh mục' : 'Portfolio value'} />
                <Line yAxisId="right" type="monotone" dataKey="score" stroke="#6366f1" strokeWidth={2} name={locale === 'vi' ? 'Điểm rủi ro TB' : 'Avg risk score'} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{locale === 'vi' ? 'Cảnh báo gần đây' : 'Recent Alerts'}</CardTitle>
            <CardDescription>{locale === 'vi' ? '4 cảnh báo mở mới nhất trong hệ thống' : 'Latest 4 open alerts'}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {recentAlerts.length === 0 ? (
              <p className="text-sm text-muted-foreground">{locale === 'vi' ? 'Hiện chưa có cảnh báo mở.' : 'No open alerts yet.'}</p>
            ) : recentAlerts.map((item) => (
              <div key={item.alert_id} className="flex items-center justify-between pb-3 border-b last:border-0 last:pb-0">
                <div>
                  <p className="font-medium text-foreground">{item.customer_name || `${locale === 'vi' ? 'Khách hàng' : 'Customer'} #${item.alert_id}`}</p>
                  <p className="text-sm text-muted-foreground">{item.message}</p>
                </div>
                <p className="text-xs text-muted-foreground">{formatDateTimeVietnam(item.created_at, locale)}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
