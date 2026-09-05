"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiGet } from "@/lib/api";
import type { Tenant } from "@/lib/types";
import {
  HomeIcon,
  CalendarIcon,
  UsersIcon,
  TagIcon,
  ClockIcon,
  BlockIcon,
  GearIcon,
  LogoutIcon,
} from "@/components/icons";

const NAV_LINKS = [
  { href: "/today", label: "Today", icon: HomeIcon },
  { href: "/appointments", label: "Appointments", icon: CalendarIcon },
  { href: "/customers", label: "Customers", icon: UsersIcon },
  { href: "/services", label: "Services", icon: TagIcon },
  { href: "/working-hours", label: "Working Hours", icon: ClockIcon },
  { href: "/time-off", label: "Time Off", icon: BlockIcon },
  { href: "/settings", label: "Settings", icon: GearIcon },
];

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  const { token, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [shopName, setShopName] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && !token) {
      router.replace("/login");
    }
  }, [isLoading, token, router]);

  useEffect(() => {
    if (!token) return;
    apiGet<Tenant>("/api/tenants/me")
      .then((t) => setShopName(t.name))
      .catch(() => setShopName(null));
  }, [token]);

  if (isLoading || !token) {
    return null;
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-5 py-5">
          <p className="truncate text-sm font-semibold text-slate-900">
            {shopName ?? "Your Shop"}
          </p>
        </div>
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
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-200 px-3 py-4">
          <button
            onClick={() => {
              logout();
              router.push("/login");
            }}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          >
            <LogoutIcon className="h-[18px] w-[18px]" />
            Log out
          </button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 overflow-y-auto p-8">{children}</main>
    </div>
  );
}
