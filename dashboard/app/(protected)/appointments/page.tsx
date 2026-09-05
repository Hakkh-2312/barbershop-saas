"use client";

import { useEffect, useState, useCallback } from "react";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import { formatTime } from "@/lib/format";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { StatusBadge } from "@/components/StatusBadge";
import type { Appointment } from "@/lib/types";

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
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
      setAppointments(await apiGet<Appointment[]>(`/api/appointments${query}`));
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

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Appointments" description="Every booking for your shop, past and upcoming." />

      <Card>
        <div className="flex flex-wrap gap-3">
          <Input type="date" value={dateFilter} onChange={(e) => setDateFilter(e.target.value)} />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All statuses</option>
            <option value="booked">Booked</option>
            <option value="cancelled">Cancelled</option>
            <option value="completed">Completed</option>
          </select>
        </div>
      </Card>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Card className="p-0">
        {loading ? (
          <p className="p-5 text-sm text-slate-500">Loading...</p>
        ) : appointments.length === 0 ? (
          <p className="p-5 text-sm text-slate-500">No appointments found.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {appointments.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center gap-4 p-4">
                <div className="w-32 shrink-0 text-sm font-medium text-slate-500">
                  {a.start_time.slice(0, 10)}
                  <div className="text-slate-900">{formatTime(a.start_time)}</div>
                </div>
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
                          className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs text-slate-900"
                        />
                        <Button variant="secondary" onClick={() => handleReschedule(a.id)}>
                          Save
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
                        Reschedule
                      </Button>
                    )}
                    <Button variant="danger" onClick={() => handleCancel(a.id)}>
                      Cancel
                    </Button>
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
