"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPut, ApiError } from "@/lib/api";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import type { WorkingHours } from "@/lib/types";

// Backend convention: Sunday = 0, Monday = 1, ..., Saturday = 6.
const DAY_NAMES = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
];

interface DayRow {
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_closed: boolean;
  saved: boolean;
}

const DEFAULT_ROW = (day: number): DayRow => ({
  day_of_week: day,
  start_time: "09:00",
  end_time: "18:00",
  is_closed: false,
  saved: false,
});

export default function WorkingHoursPage() {
  const [rows, setRows] = useState<DayRow[]>(
    Array.from({ length: 7 }, (_, day) => DEFAULT_ROW(day))
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingDay, setSavingDay] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const existing = await apiGet<WorkingHours[]>("/api/working-hours");
      setRows(
        Array.from({ length: 7 }, (_, day) => {
          const found = existing.find((w) => w.day_of_week === day);
          return found
            ? {
                day_of_week: day,
                start_time: found.start_time.slice(0, 5),
                end_time: found.end_time.slice(0, 5),
                is_closed: found.is_closed,
                saved: true,
              }
            : DEFAULT_ROW(day);
        })
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load working hours");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function updateRow(day: number, patch: Partial<DayRow>) {
    setRows((prev) => prev.map((r) => (r.day_of_week === day ? { ...r, ...patch } : r)));
  }

  async function handleSave(day: number) {
    const row = rows.find((r) => r.day_of_week === day);
    if (!row) return;

    setSavingDay(day);
    setError(null);
    try {
      await apiPut(`/api/working-hours/${day}`, {
        start_time: `${row.start_time}:00`,
        end_time: `${row.end_time}:00`,
        is_closed: row.is_closed,
      });
      updateRow(day, { saved: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save working hours");
    } finally {
      setSavingDay(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Working Hours" description="When your shop is open for bookings." />

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Card className="p-0">
        {loading ? (
          <p className="p-5 text-sm text-slate-500">Loading...</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {rows.map((row) => (
              <li key={row.day_of_week} className="flex flex-wrap items-center gap-4 p-4">
                <div className="w-28 shrink-0 text-sm font-medium text-slate-900">
                  {DAY_NAMES[row.day_of_week]}
                  {!row.saved && <span className="ml-1.5 text-xs text-slate-400">(not set)</span>}
                </div>
                <input
                  type="time"
                  value={row.start_time}
                  disabled={row.is_closed}
                  onChange={(e) => updateRow(row.day_of_week, { start_time: e.target.value })}
                  className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 disabled:opacity-40"
                />
                <span className="text-sm text-slate-400">to</span>
                <input
                  type="time"
                  value={row.end_time}
                  disabled={row.is_closed}
                  onChange={(e) => updateRow(row.day_of_week, { end_time: e.target.value })}
                  className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 disabled:opacity-40"
                />
                <label className="flex items-center gap-1.5 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={row.is_closed}
                    onChange={(e) => updateRow(row.day_of_week, { is_closed: e.target.checked })}
                  />
                  Closed
                </label>
                <Button
                  variant="secondary"
                  className="ml-auto"
                  onClick={() => handleSave(row.day_of_week)}
                  disabled={savingDay === row.day_of_week}
                >
                  {savingDay === row.day_of_week ? "Saving..." : "Save"}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
