"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { useLanguage } from "@/lib/i18n";
import { useTenant } from "@/lib/tenant";
import { NotificationBell } from "@/components/NotificationBell";
import {
  HomeIcon,
  CalendarIcon,
  UsersIcon,
  TagIcon,
  ClockIcon,
  BlockIcon,
  ChartIcon,
  CreditCardIcon,
  GearIcon,
  LogoutIcon,
  MenuIcon,
  CloseIcon,
} from "@/components/icons";

const NAV_LINKS = [
  { href: "/today", key: "nav.today", icon: HomeIcon },
  { href: "/appointments", key: "nav.appointments", icon: CalendarIcon },
  { href: "/customers", key: "nav.customers", icon: UsersIcon },
  { href: "/services", key: "nav.services", icon: TagIcon },
  { href: "/working-hours", key: "nav.workingHours", icon: ClockIcon },
  { href: "/time-off", key: "nav.timeOff", icon: BlockIcon },
  { href: "/analytics", key: "nav.analytics", icon: ChartIcon },
  { href: "/billing", key: "nav.billing", icon: CreditCardIcon },
  { href: "/settings", key: "nav.settings", icon: GearIcon },
];

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  const { token, isLoading, logout } = useAuth();
  const { t, lang, setLang } = useLanguage();
  const { tenant } = useTenant();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !token) {
      router.replace("/login");
    }
  }, [isLoading, token, router]);

  // Close the mobile drawer automatically whenever the route changes -
  // otherwise it stays open after tapping a nav link.
  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  if (isLoading || !token) {
    return null;
  }

  function handleLogout() {
    logout();
    router.push("/login");
  }

  const navList = (
    <nav className="flex-1 space-y-1 px-3 py-4">
      {NAV_LINKS.map((link) => {
        const isActive = pathname === link.href || pathname?.startsWith(`${link.href}/`);
        const Icon = link.icon;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              isActive
                ? "bg-indigo-50 text-indigo-700"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            }`}
          >
            <Icon className="h-[18px] w-[18px] shrink-0" />
            {t(link.key)}
          </Link>
        );
      })}
    </nav>
  );

  const footer = (
    <div className="border-t border-slate-200 px-3 py-4">
      <button
        onClick={() => setLang(lang === "ar" ? "en" : "ar")}
        className="flex w-full items-center justify-center rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
      >
        {t("lang.switchTo")}
      </button>
      <button
        onClick={handleLogout}
        className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
      >
        <LogoutIcon className="h-[18px] w-[18px]" />
        {t("nav.logout")}
      </button>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Desktop sidebar - persistent, hidden below md */}
      <aside className="hidden w-60 shrink-0 flex-col border-e border-slate-200 bg-white md:flex">
        <div className="border-b border-slate-200 px-5 py-5">
          <p className="truncate text-sm font-semibold text-slate-900">
            {tenant?.name ?? t("nav.shopFallback")}
          </p>
        </div>
        {navList}
        {footer}
      </aside>

      {/* Mobile drawer - overlay + sliding panel, only rendered interactive below md */}
      {mobileNavOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/50 md:hidden"
          onClick={() => setMobileNavOpen(false)}
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed inset-y-0 start-0 z-50 flex w-64 flex-col border-e border-slate-200 bg-white transition-transform duration-200 md:hidden ${
          mobileNavOpen ? "translate-x-0" : "-translate-x-full rtl:translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-5">
          <p className="truncate text-sm font-semibold text-slate-900">
            {tenant?.name ?? t("nav.shopFallback")}
          </p>
          <button
            onClick={() => setMobileNavOpen(false)}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100"
            aria-label={t("nav.closeMenu")}
          >
            <CloseIcon className="h-5 w-5" />
          </button>
        </div>
        {navList}
        {footer}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2.5 md:justify-end md:px-6">
          <button
            onClick={() => setMobileNavOpen(true)}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-900 md:hidden"
            aria-label={t("nav.openMenu")}
          >
            <MenuIcon className="h-5 w-5" />
          </button>
          <NotificationBell />
        </header>
        <main className="min-w-0 flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
