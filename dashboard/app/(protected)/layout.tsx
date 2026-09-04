"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

const NAV_LINKS = [
  { href: "/appointments", label: "Appointments" },
  { href: "/customers", label: "Customers" },
  { href: "/services", label: "Services" },
  { href: "/working-hours", label: "Working Hours" },
  { href: "/settings", label: "Settings" },
];

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  const { token, isLoading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !token) {
      router.replace("/login");
    }
  }, [isLoading, token, router]);

  if (isLoading || !token) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <nav className="flex gap-4 text-sm font-medium">
          {NAV_LINKS.map((link) => (
            <Link key={link.href} href={link.href} className="hover:underline">
              {link.label}
            </Link>
          ))}
        </nav>
        <button
          onClick={() => {
            logout();
            router.push("/login");
          }}
          className="text-sm text-gray-600 underline"
        >
          Log out
        </button>
      </header>
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
