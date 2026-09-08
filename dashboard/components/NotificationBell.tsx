"use client";

import { useEffect, useRef, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import { dateLocale, useLanguage } from "@/lib/i18n";
import { formatDateLong, formatRelativeTime, formatTime } from "@/lib/format";
import { BellIcon } from "@/components/icons";
import type { Notification } from "@/lib/types";

// Types the dashboard knows how to fully re-translate from their stored
// customer/service/time fields - anything else (or an older notification
// created before those fields existed) falls back to the stored English
// title/message instead.
const LOCALIZABLE_TYPES = new Set(["new_booking", "cancellation", "reschedule"]);

export function NotificationBell() {
  const { t, lang } = useLanguage();

  function localize(n: Notification): { title: string; message: string } {
    if (!n.customer_name || !n.appointment_time || !LOCALIZABLE_TYPES.has(n.type)) {
      return { title: n.title, message: n.message };
    }
    return {
      title: t(`notifications.type.${n.type}.title`),
      message: t(`notifications.type.${n.type}.message`, {
        customer: n.customer_name,
        service: n.service_name ?? t("notifications.defaultService"),
        date: formatDateLong(n.appointment_time, dateLocale(lang)),
        time: formatTime(n.appointment_time),
      }),
    };
  }
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  async function loadUnreadCount() {
    try {
      const { count } = await apiGet<{ count: number }>("/api/notifications/unread-count");
      setUnreadCount(count);
    } catch {
      // A failed notification check shouldn't disrupt the rest of the dashboard.
    }
  }

  async function loadNotifications() {
    try {
      setNotifications(await apiGet<Notification[]>("/api/notifications"));
    } catch {
      // Same as above - fail quietly.
    }
  }

  useEffect(() => {
    loadUnreadCount();
    const interval = setInterval(loadUnreadCount, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (open) loadNotifications();
  }, [open]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  async function handleMarkRead(id: number) {
    try {
      await apiPost(`/api/notifications/${id}/read`);
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // ignore
    }
  }

  async function handleMarkAllRead() {
    try {
      await apiPost("/api/notifications/read-all");
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // ignore
    }
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label={t("notifications.title")}
        className="relative flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
      >
        <BellIcon className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -end-0.5 -top-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-medium text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="animate-dropdown-in absolute end-0 z-10 mt-2 w-80 rounded-xl border border-slate-200 bg-white shadow-lg">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <p className="text-sm font-semibold text-slate-900">{t("notifications.title")}</p>
            {notifications.some((n) => !n.is_read) && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
              >
                {t("notifications.markAllRead")}
              </button>
            )}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="p-4 text-sm text-slate-500">{t("notifications.empty")}</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {notifications.map((n) => {
                  const { title, message } = localize(n);
                  return (
                  <li
                    key={n.id}
                    onClick={() => !n.is_read && handleMarkRead(n.id)}
                    className={`cursor-pointer p-4 text-sm hover:bg-slate-50 ${
                      n.is_read ? "" : "bg-indigo-50/40"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-medium text-slate-900">{title}</p>
                      {!n.is_read && (
                        <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-indigo-600" />
                      )}
                    </div>
                    <p className="mt-0.5 text-slate-600">{message}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {formatRelativeTime(n.created_at)}
                    </p>
                  </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
