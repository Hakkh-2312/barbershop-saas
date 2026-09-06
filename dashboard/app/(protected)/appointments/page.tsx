"use client";

import { useEffect, useState, useCallback } from "react";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import { formatTime } from "@/lib/format";
import { useLanguage } from "@/lib/i18n";
import { toWhatsAppLink } from "@/lib/whatsapp";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { StatusBadge } from "@/components/StatusBadge";
import { SkeletonList } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { WhatsAppIcon, CalendarIcon } from "@/components/icons";
import type { Appointment, Tenant } from "@/lib/types";

export default function AppointmentsPage() {
  const { t } = useLanguage();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateFilter, setDateFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [rescheduleId, setRescheduleId] = useState<number | null>(null);
  const [rescheduleValue, setRescheduleValue] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (dateFilter) params.set("date", dateFilter);
      if (statusFilter) params.set("status", statusFilter);
      const query = params.toString() ? `?${params.toString()}` : "";
      const [appts, myTenant] = await Promise.all([
        apiGet<Appointment[]>(`/api/appointments${query}`),
        apiGet<Tenant>("/api/tenants/me"),
      ]);
      setAppointments(appts);
      setTenant(myTenant);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load appointments");
    } finally {
      setLoading(false);
    }
  }, [dateFilter, statusFilter]);

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

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={t("appointments.title")} description={t("appointments.description")} />

      <Card>
        <div className="flex flex-wrap gap-3">
          <Input type="date" value={dateFilter} onChange={(e) => setDateFilter(e.target.value)} />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 transition-shadow duration-150 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/25"
          >
            <option value="">{t("appointments.allStatuses")}</option>
            <option value="booked">{t("status.booked")}</option>
            <option value="cancelled">{t("status.cancelled")}</option>
            <option value="completed">{t("status.completed")}</option>
            <option value="no_show">{t("status.no_show")}</option>
          </select>
        </div>
      </Card>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Card className="p-0">
        {loading ? (
          <SkeletonList rows={4} />
        ) : appointments.length === 0 ? (
          <EmptyState icon={CalendarIcon} title={t("appointments.noneFound")} />
        ) : (
          <ul className="divide-y divide-slate-100">
            {appointments.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center gap-4 p-4">
                <div className="w-32 shrink-0 text-sm font-medium text-slate-500">
                  {a.start_time.slice(0, 10)}
                  <div className="text-slate-900">{formatTime(a.start_time)}</div>
                </div>
                <a
                  href={toWhatsAppLink(a.customer_phone, tenant?.country_code)}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={t("common.whatsapp")}
                  className="shrink-0 text-emerald-600 hover:text-emerald-700"
                >
                  <WhatsAppIcon className="h-5 w-5" />
                </a>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-900">{a.customer_name}</p>
                  <p className="truncate text-sm text-slate-500">{a.service_name}</p>
                </div>
                <StatusBadge status={a.status} />
                {a.status === "booked" && (
                  <div className="flex shrink-0 items-center gap-2">
                    {rescheduleId === a.id ? (
                      <>
                        <input
                          type="datetime-local"
                          value={rescheduleValue}
                          onChange={(e) => setRescheduleValue(e.target.value)}
                          className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs text-slate-900 transition-shadow duration-150 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/25"
                        />
                        <Button variant="secondary" onClick={() => handleReschedule(a.id)}>
                          {t("common.save")}
                        </Button>
                      </>
                    ) : (
                      <Button
                        variant="secondary"
                        onClick={() => {
                          setRescheduleId(a.id);
                          setRescheduleValue(a.start_time.slice(0, 16));
                        }}
                      >
                        {t("appointments.reschedule")}
                      </Button>
                    )}
                    <Button variant="danger" onClick={() => handleCancel(a.id)}>
                      {t("common.cancel")}
                    </Button>
                    {new Date(a.start_time) < new Date() && (
                      <Button variant="ghost" onClick={() => handleNoShow(a.id)}>
                        {t("common.noShow")}
                      </Button>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
