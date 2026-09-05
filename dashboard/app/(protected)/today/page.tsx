"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import { formatDateLong, formatTime, todayIso } from "@/lib/format";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { StatusBadge } from "@/components/StatusBadge";
import { BlockIcon } from "@/components/icons";
import type { Appointment, TimeBlock } from "@/lib/types";

type ScheduleItem =
  | { kind: "appointment"; start_time: string; data: Appointment }
  | { kind: "block"; start_time: string; data: TimeBlock };

export default function TodayPage() {
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

  const activeAppointments = items.filter(
    (i) => i.kind === "appointment" && i.data.status === "booked"
  ) as { kind: "appointment"; start_time: string; data: Appointment }[];
  const nextUp = activeAppointments[0];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Today"
        description={formatDateLong(today)}
        action={
          <Link href="/time-off">
            <Button variant="secondary">
              <BlockIcon className="h-4 w-4" />
              Block off time
            </Button>
          </Link>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <p className="text-sm text-slate-500">Appointments today</p>
          <p className="mt-1 text-3xl font-semibold text-slate-900">{activeAppointments.length}</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">Next up</p>
          <p className="mt-1 text-3xl font-semibold text-slate-900">
            {nextUp ? formatTime(nextUp.start_time) : "—"}
          </p>
          {nextUp && <p className="text-sm text-slate-500">{nextUp.data.customer_name}</p>}
        </Card>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Card className="p-0">
        {loading ? (
          <p className="p-5 text-sm text-slate-500">Loading...</p>
        ) : items.length === 0 ? (
          <p className="p-5 text-sm text-slate-500">Nothing scheduled today.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {items.map((item) => (
              <li key={`${item.kind}-${item.data.id}`} className="flex items-center gap-4 p-4">
                <div className="w-14 shrink-0 text-sm font-medium text-slate-500">
                  {formatTime(item.start_time)}
                </div>

                {item.kind === "block" ? (
                  <div className="flex flex-1 items-center gap-2 text-sm text-slate-400">
                    <BlockIcon className="h-4 w-4 shrink-0" />
                    <span>Blocked{item.data.reason ? ` — ${item.data.reason}` : ""}</span>
                    <span>
                      ({formatTime(item.data.start_time)}–{formatTime(item.data.end_time)})
                    </span>
                  </div>
                ) : (
                  <>
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
                              className="rounded-lg border border-slate-300 px-2 py-1 text-xs"
                            />
                            <Button variant="secondary" onClick={() => handleReschedule(item.data.id)}>
                              Save
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
                            Reschedule
                          </Button>
                        )}
                        <Button variant="danger" onClick={() => handleCancel(item.data.id)}>
                          Cancel
                        </Button>
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
