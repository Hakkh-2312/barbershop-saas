"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPut, ApiError } from "@/lib/api";
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
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Working Hours</h1>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-max border-collapse text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="py-2 pr-4">Day</th>
                <th className="pr-4">Open</th>
                <th className="pr-4">Close</th>
                <th className="pr-4">Closed</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.day_of_week} className="border-b">
                  <td className="py-2 pr-4">
                    {DAY_NAMES[row.day_of_week]}
                    {!row.saved && (
                      <span className="ml-2 text-xs text-gray-400">(not set)</span>
                    )}
                  </td>
                  <td className="pr-4">
                    <input
                      type="time"
                      value={row.start_time}
                      disabled={row.is_closed}
                      onChange={(e) => updateRow(row.day_of_week, { start_time: e.target.value })}
                      className="rounded border px-1 disabled:opacity-40"
                    />
                  </td>
                  <td className="pr-4">
                    <input
                      type="time"
                      value={row.end_time}
                      disabled={row.is_closed}
                      onChange={(e) => updateRow(row.day_of_week, { end_time: e.target.value })}
                      className="rounded border px-1 disabled:opacity-40"
                    />
                  </td>
                  <td className="pr-4">
                    <input
                      type="checkbox"
                      checked={row.is_closed}
                      onChange={(e) =>
                        updateRow(row.day_of_week, { is_closed: e.target.checked })
                      }
                    />
                  </td>
                  <td className="py-2">
                    <button
                      onClick={() => handleSave(row.day_of_week)}
                      disabled={savingDay === row.day_of_week}
                      className="text-blue-600 underline disabled:opacity-50"
                    >
                      {savingDay === row.day_of_week ? "Saving..." : "Save"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
