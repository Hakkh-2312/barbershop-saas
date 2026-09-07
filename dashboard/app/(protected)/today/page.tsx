"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import { formatDateLong, formatTime, todayIso } from "@/lib/format";
import { dateLocale, useLanguage } from "@/lib/i18n";
import { useTenant } from "@/lib/tenant";
import { toWhatsAppLink } from "@/lib/whatsapp";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { StatusBadge } from "@/components/StatusBadge";
import { Skeleton, SkeletonList } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { BlockIcon, WhatsAppIcon, HomeIcon } from "@/components/icons";
import type { Appointment, TimeBlock } from "@/lib/types";

type ScheduleItem =
  | { kind: "appointment"; start_time: string; data: Appointment }
  | { kind: "block"; start_time: string; data: TimeBlock };

export default function TodayPage() {
  const { t, lang } = useLanguage();
  const { tenant } = useTenant();
  const [items, setItems] = useState<ScheduleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rescheduleId, setRescheduleId] = useState<number | null>(null);
  const [rescheduleValue, setRescheduleValue] = useState("");

  const today = todayIso();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [appointments, blocks] = await Promise.all([
        apiGet<Appointment[]>(`/api/appointments?date=${today}`),
        apiGet<TimeBlock[]>(`/api/time-blocks?date=${today}`),
      ]);

      const merged: ScheduleItem[] = [
        ...appointments.map((a): ScheduleItem => ({ kind: "appointment", start_time: a.start_time, data: a })),
        ...blocks.map((b): ScheduleItem => ({ kind: "block", start_time: b.start_time, data: b })),
      ].sort((a, b) => a.start_time.localeCompare(b.start_time));

      setItems(merged);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load today's schedule");
    } finally {
      setLoading(false);
    }
  }, [today]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCancel(id: number) {
    setError(null);
    try {
      await apiPost(`/api/appointments/${id}/cancel`);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to cancel appointment");
    }
  }

  async function handleReschedule(id: number) {
    setError(null);
    try {
      await apiPost(`/api/appointments/${id}/reschedule`, { start_time: rescheduleValue });
      setRescheduleId(null);
      setRescheduleValue("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reschedule appointment");
    }
  }

  async function handleNoShow(id: number) {
    setError(null);
    try {
      await apiPost(`/api/appointments/${id}/no-show`);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to mark as no-show");
    }
  }

  const activeAppointments = items.filter(
    (i) => i.kind === "appointment" && i.data.status === "booked"
  ) as { kind: "appointment"; start_time: string; data: Appointment }[];
  const nextUp = activeAppointments[0];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={t("nav.today")}
        description={formatDateLong(today, dateLocale(lang))}
        action={
          <Link href="/time-off">
            <Button variant="secondary">
              <BlockIcon className="h-4 w-4" />
              {t("today.blockOffTime")}
            </Button>
          </Link>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <p className="text-sm text-slate-500">{t("today.appointmentsToday")}</p>
          {loading ? (
            <Skeleton className="mt-2 h-8 w-10" />
          ) : (
            <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-900">
              {activeAppointments.length}
            </p>
          )}
        </Card>
        <Card>
          <p className="text-sm text-slate-500">{t("today.nextUp")}</p>
          {loading ? (
            <Skeleton className="mt-2 h-8 w-16" />
          ) : (
            <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-900">
              {nextUp ? formatTime(nextUp.start_time) : "—"}
            </p>
          )}
          {!loading && nextUp && <p className="text-sm text-slate-500">{nextUp.data.customer_name}</p>}
        </Card>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Card className="p-0">
        {loading ? (
          <SkeletonList rows={4} />
        ) : items.length === 0 ? (
          <EmptyState icon={HomeIcon} title={t("today.nothingScheduled")} />
        ) : (
          <ul className="divide-y divide-slate-100">
            {items.map((item) => (
              <li
                key={`${item.kind}-${item.data.id}`}
                className="flex flex-wrap items-center gap-3 p-4"
              >
                <div className="w-14 shrink-0 text-sm font-medium text-slate-500">
                  {formatTime(item.start_time)}
                </div>

                {item.kind === "block" ? (
                  <div className="flex flex-1 items-center gap-2 text-sm text-slate-400">
                    <BlockIcon className="h-4 w-4 shrink-0" />
                    <span>
                      {t("today.blocked")}
                      {item.data.reason ? ` — ${item.data.reason}` : ""}
                    </span>
                    <span>
                      ({formatTime(item.data.start_time)}–{formatTime(item.data.end_time)})
                    </span>
                  </div>
                ) : (
                  <>
                    <a
                      href={toWhatsAppLink(item.data.customer_phone, tenant?.country_code)}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={t("common.whatsapp")}
                      className="shrink-0 text-emerald-600 hover:text-emerald-700"
                    >
                      <WhatsAppIcon className="h-5 w-5" />
                    </a>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-900">
                        {item.data.customer_name}
                      </p>
                      <p className="truncate text-sm text-slate-500">{item.data.service_name}</p>
                    </div>
                    <StatusBadge status={item.data.status} />
                    {item.data.status === "booked" && (
                      <div className="flex shrink-0 items-center gap-2">
                        {rescheduleId === item.data.id ? (
                          <>
                            <input
                              type="datetime-local"
                              value={rescheduleValue}
                              onChange={(e) => setRescheduleValue(e.target.value)}
                              className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs text-slate-900 transition-shadow duration-150 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/25"
                            />
                            <Button variant="secondary" onClick={() => handleReschedule(item.data.id)}>
                              {t("common.save")}
                            </Button>
                          </>
                        ) : (
                          <Button
                            variant="secondary"
                            onClick={() => {
                              setRescheduleId(item.data.id);
                              setRescheduleValue(item.data.start_time.slice(0, 16));
                            }}
                          >
                            {t("appointments.reschedule")}
                          </Button>
                        )}
                        <Button variant="danger" onClick={() => handleCancel(item.data.id)}>
                          {t("common.cancel")}
                        </Button>
                        {new Date(item.data.start_time) < new Date() && (
                          <Button variant="ghost" onClick={() => handleNoShow(item.data.id)}>
                            {t("common.noShow")}
                          </Button>
                        )}
                      </div>
                    )}
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
