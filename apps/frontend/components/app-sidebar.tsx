'use client';

import * as React from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarRail,
  useSidebar,
} from '@/components/ui/sidebar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { clearAccessToken } from '@/lib/auth/token';
import { ThemeToggle } from '@/components/theme-toggle';
import { getUserRole, type UserRole } from '@/lib/auth/token';
import { LanguageToggle } from '@/components/language-toggle';
import { useI18n } from '@/components/i18n-provider';

import {
  LayoutDashboard,
  Users,
  TrendingUp,
  PieChart,
  Zap,
  AlertCircle,
  Settings,
  LogOut,
  ChevronDown,
  BarChart3,
  ScrollText,
  ClipboardList,
} from 'lucide-react';

const navigationItems = [
  {
    titleKey: 'sidebar.dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    titleKey: 'sidebar.customers',
    href: '/dashboard/customers',
    icon: Users,
  },
  {
    titleKey: 'sidebar.approved_loan_workbench',
    href: '/dashboard/loans/approved-workbench',
    icon: ClipboardList,
  },
  {
    titleKey: 'sidebar.risk',
    icon: TrendingUp,
    items: [
      {
        titleKey: 'sidebar.risk.score',
        href: '/dashboard/risk/score',
      },
      {
        titleKey: 'sidebar.risk.analyze',
        href: '/dashboard/risk/analyze',
      },
      {
        titleKey: 'sidebar.risk.batch',
        href: '/dashboard/risk/batch',
      },
      {
        titleKey: 'sidebar.risk.simulation',
        href: '/dashboard/risk/simulation',
      },
    ],
  },
  {
    titleKey: 'sidebar.portfolio',
    icon: PieChart,
    items: [
      {
        titleKey: 'sidebar.portfolio.overview',
        href: '/dashboard/portfolio/overview',
      },
      {
        titleKey: 'sidebar.portfolio.risk_distribution',
        href: '/dashboard/portfolio/risk-distribution',
      },
    ],
  },
  {
    titleKey: 'sidebar.ai_chat',
    href: '/dashboard/ai-chat',
    icon: Zap,
  },
  {
    titleKey: 'sidebar.powerbi',
    href: '/dashboard/powerbi/config',
    icon: BarChart3,
  },
  {
    titleKey: 'sidebar.alerts',
    href: '/dashboard/alerts',
    icon: AlertCircle,
  },
];

/** Analyst sidebar: customers, AI Chat, Power BI only. */
const ANALYST_NAV_TITLE_KEYS = new Set([
  'sidebar.customers',
  'sidebar.approved_loan_workbench',
  'sidebar.ai_chat',
  'sidebar.powerbi',
]);

const adminItems = [
  {
    titleKey: 'sidebar.admin.users',
    href: '/dashboard/admin/users',
    icon: Users,
  },
  {
    titleKey: 'sidebar.admin.registrations',
    href: '/dashboard/admin/registrations',
    icon: AlertCircle,
  },
  {
    titleKey: 'sidebar.admin.audit_logs',
    href: '/dashboard/admin/audit-logs',
    icon: ScrollText,
  },
];

export function AppSidebar() {
  const { state: sidebarState } = useSidebar();
  const router = useRouter();
  const pathname = usePathname();
  const { t, locale } = useI18n();
  const navT = React.useCallback(
    (key: string) => {
      if (key === 'sidebar.approved_loan_workbench') {
        return locale === 'en' ? 'Approved loan applications' : 'Hồ sơ vay đã duyệt';
      }
      return t(key);
    },
    [t, locale],
  );
  const isSidebarCollapsed = sidebarState === 'collapsed';
  const [openItems, setOpenItems] = React.useState<string[]>([]);
  const [role, setRole] = React.useState<UserRole | null>(null);

  React.useEffect(() => {
    setRole(getUserRole());
  }, []);

  // Icon rail width is defined on SidebarProvider’s wrapper (`--sidebar-width-icon`), not on
  // `Sidebar` itself — setting it only on the fixed panel would desync the spacer gap.
  React.useLayoutEffect(() => {
    const wrapper = document.querySelector('[data-slot="sidebar-wrapper"]');
    if (!(wrapper instanceof HTMLElement)) return;
    const prev = wrapper.style.getPropertyValue('--sidebar-width-icon');
    wrapper.style.setProperty('--sidebar-width-icon', '3.75rem');
    return () => {
      if (prev) wrapper.style.setProperty('--sidebar-width-icon', prev);
      else wrapper.style.removeProperty('--sidebar-width-icon');
    };
  }, []);

  const handleLogout = () => {
    clearAccessToken();
    router.push('/auth?mode=login');
  };

  const toggleItem = (title: string) => {
    setOpenItems((prev) =>
      prev.includes(title) ? prev.filter((item) => item !== title) : [...prev, title]
    );
  };

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + '/');
  const isAdmin = role === 'admin';
  const isViewer = role === 'viewer';
  const isAnalyst = role === 'analyst';
  const homeHref = isAnalyst ? '/dashboard/customers' : '/dashboard';

  const visibleNavHrefs = React.useMemo(() => {
    const hrefs: string[] = [];
    const analyst = role === 'analyst';

    for (const item of navigationItems) {
      if (analyst && !ANALYST_NAV_TITLE_KEYS.has(item.titleKey)) {
        continue;
      }
      if (isViewer) {
        if (item.href === '/dashboard/upload') continue;
        if (item.items) {
          const filteredSubItems = item.items.filter((subItem) => !subItem.href.includes('/batch'));
          for (const subItem of filteredSubItems) hrefs.push(subItem.href);
          continue;
        }
      }
      if (item.items) {
        const filteredSubItems = isViewer
          ? item.items.filter((subItem) => !subItem.href.includes('/batch'))
          : item.items;
        for (const subItem of filteredSubItems) hrefs.push(subItem.href);
        continue;
      }
      if (item.href) hrefs.push(item.href);
    }

    if (isAdmin) {
      for (const item of adminItems) hrefs.push(item.href);
    }

    // Ensure deterministic indices and a fallback.
    if (!analyst && !hrefs.includes('/dashboard')) hrefs.unshift('/dashboard');
    if (analyst && !hrefs.includes('/dashboard/customers')) {
      hrefs.unshift('/dashboard/customers');
    }
    return hrefs;
  }, [isAdmin, isViewer, role]);

  const navIndexFor = React.useCallback(
    (path: string) => {
      let bestIdx = -1;
      let bestLen = -1;
      for (let i = 0; i < visibleNavHrefs.length; i++) {
        const href = visibleNavHrefs[i];
        const matches = path === href || path.startsWith(href + '/');
        if (!matches) continue;
        if (href.length > bestLen) {
          bestIdx = i;
          bestLen = href.length;
        }
      }
      return bestIdx;
    },
    [visibleNavHrefs],
  );

  const currentNavIndex = navIndexFor(pathname);

  const navDirForHref = React.useCallback(
    (href: string) => {
      const toIndex = navIndexFor(href);
      if (toIndex === -1 || currentNavIndex === -1) return 'forward' as const;
      if (toIndex === currentNavIndex) return 'forward' as const;
      return toIndex < currentNavIndex ? ('back' as const) : ('forward' as const);
    },
    [currentNavIndex, navIndexFor],
  );

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border p-4 group-data-[collapsible=icon]:flex group-data-[collapsible=icon]:flex-col group-data-[collapsible=icon]:items-center group-data-[collapsible=icon]:px-2 group-data-[collapsible=icon]:py-3">
        <Link
          href={homeHref}
          data-nav-dir={navDirForHref(homeHref)}
          className="flex w-full items-center gap-2 hover:opacity-80 transition-opacity group-data-[collapsible=icon]:w-auto group-data-[collapsible=icon]:justify-center"
        >
          <Image
            src="/logo.svg"
            alt="CRAI DB"
            width={32}
            height={32}
            className="shrink-0"
          />
          <span className="font-semibold text-sm text-sidebar-foreground group-data-[collapsible=icon]:hidden">
            CRAI DB
          </span>
        </Link>
      </SidebarHeader>

      <SidebarContent className="group-data-[collapsible=icon]:items-center">
        <SidebarMenu className="group-data-[collapsible=icon]:items-center">
          {navigationItems
            .filter((item) => {
              const isManager = role === 'manager';
              const analyst = role === 'analyst';

              if (analyst) {
                return ANALYST_NAV_TITLE_KEYS.has(item.titleKey);
              }
              if (isViewer) {
                if (item.href === '/dashboard/upload') return false;
                if (item.href === '/dashboard/customers') return true;
                if (item.titleKey === 'sidebar.risk') return true;
              }
              return true;
            })
            .map((item) => {
            if (item.items) {
              const filteredSubItems = isViewer
                ? item.items.filter((subItem) => !subItem.href.includes('/batch'))
                : item.items;
              if (isSidebarCollapsed) {
                return (
                  <SidebarMenuItem key={item.titleKey}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <SidebarMenuButton tooltip={navT(item.titleKey)}>
                          <item.icon className="h-4 w-4" />
                          <span>{navT(item.titleKey)}</span>
                        </SidebarMenuButton>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent className="w-56" side="right" align="start">
                        {filteredSubItems.map((subItem) => (
                          <DropdownMenuItem key={subItem.href} asChild>
                            <Link href={subItem.href} data-nav-dir={navDirForHref(subItem.href)}>
                              {navT(subItem.titleKey)}
                            </Link>
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </SidebarMenuItem>
                );
              }
              return (
                <Collapsible
                  key={item.titleKey}
                  open={openItems.includes(item.titleKey)}
                  onOpenChange={() => toggleItem(item.titleKey)}
                  className="group/collapsible group-data-[collapsible=icon]:flex group-data-[collapsible=icon]:w-full group-data-[collapsible=icon]:justify-center"
                >
                  <SidebarMenuItem>
                    <CollapsibleTrigger asChild>
                      <SidebarMenuButton
                        className="data-[state=open]:bg-sidebar-accent"
                        tooltip={navT(item.titleKey)}
                      >
                        <item.icon className="h-4 w-4" />
                        <span>{navT(item.titleKey)}</span>
                        <ChevronDown className="ml-auto h-4 w-4 transition-transform group-data-[state=open]/collapsible:rotate-180" />
                      </SidebarMenuButton>
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <SidebarMenuSub>
                        {filteredSubItems.map((subItem) => (
                          <SidebarMenuSubItem key={subItem.href}>
                            <SidebarMenuSubButton
                              asChild
                              isActive={isActive(subItem.href)}
                            >
                              <Link href={subItem.href} data-nav-dir={navDirForHref(subItem.href)}>
                                <span>{navT(subItem.titleKey)}</span>
                              </Link>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        ))}
                      </SidebarMenuSub>
                    </CollapsibleContent>
                  </SidebarMenuItem>
                </Collapsible>
              );
            }

            return (
              <SidebarMenuItem key={item.href}>
                <SidebarMenuButton
                  asChild
                  isActive={isActive(item.href)}
                  tooltip={navT(item.titleKey)}
                >
                  <Link href={item.href} data-nav-dir={navDirForHref(item.href)}>
                    <item.icon className="h-4 w-4" />
                    <span>{navT(item.titleKey)}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>

        {/* Admin Section */}
        {isAdmin && (
          <div className="mt-8 pt-6 border-t border-sidebar-border group-data-[collapsible=icon]:mt-4 group-data-[collapsible=icon]:flex group-data-[collapsible=icon]:flex-col group-data-[collapsible=icon]:items-center group-data-[collapsible=icon]:pt-4">
            <div className="px-3 py-2 group-data-[collapsible=icon]:hidden">
              <h3 className="text-xs font-semibold text-sidebar-foreground/70 uppercase tracking-wider">
                {t("sidebar.admin")}
              </h3>
            </div>
            <SidebarMenu className="group-data-[collapsible=icon]:items-center">
              {adminItems.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive(item.href)}
                    tooltip={navT(item.titleKey)}
                  >
                    <Link href={item.href} data-nav-dir={navDirForHref(item.href)}>
                      <item.icon className="h-4 w-4" />
                      <span>{navT(item.titleKey)}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </div>
        )}
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border p-4 group-data-[collapsible=icon]:flex group-data-[collapsible=icon]:flex-col group-data-[collapsible=icon]:items-center group-data-[collapsible=icon]:px-2 group-data-[collapsible=icon]:py-3">
        <SidebarMenu className="group-data-[collapsible=icon]:items-center">
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton tooltip={t("sidebar.settings")}>
                  <Settings className="h-4 w-4" />
                  <span>{t("sidebar.settings")}</span>
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="top" className="w-56">
                <DropdownMenuItem onSelect={(e) => e.preventDefault()} className="flex items-center justify-between">
                  <span>{t("nav.theme")}</span>
                  <ThemeToggle variant="outline" />
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={(e) => e.preventDefault()} className="flex items-center justify-between">
                  <span>{t("nav.language")}</span>
                  <LanguageToggle variant="outline" />
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/dashboard/profile">
                    <span>{t("sidebar.profile")}</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>{t("sidebar.logout")}</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  );
}
