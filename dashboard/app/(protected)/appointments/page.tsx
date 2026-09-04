"use client";

import { useEffect, useState, useCallback } from "react";
import { apiGet, apiPost, ApiError } from "@/lib/api";
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
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Appointments</h1>

      <div className="flex flex-wrap gap-3">
        <input
          type="date"
          value={dateFilter}
          onChange={(e) => setDateFilter(e.target.value)}
          className="rounded border px-2 py-1 text-sm"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded border px-2 py-1 text-sm"
        >
          <option value="">All statuses</option>
          <option value="booked">Booked</option>
          <option value="cancelled">Cancelled</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : appointments.length === 0 ? (
        <p className="text-sm text-gray-500">No appointments found.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-max border-collapse text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="py-2 pr-4">Start</th>
                <th className="pr-4">End</th>
                <th className="pr-4">Customer ID</th>
                <th className="pr-4">Service ID</th>
                <th className="pr-4">Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {appointments.map((a) => (
                <tr key={a.id} className="border-b">
                  <td className="py-2 pr-4">{a.start_time.replace("T", " ")}</td>
                  <td className="pr-4">{a.end_time.replace("T", " ")}</td>
                  <td className="pr-4">{a.customer_id}</td>
                  <td className="pr-4">{a.service_id}</td>
                  <td className="pr-4">{a.status}</td>
                  <td className="py-2">
                    {a.status === "booked" && (
                      <div className="flex flex-col gap-1 sm:flex-row sm:items-center">
                        <button
                          onClick={() => handleCancel(a.id)}
                          className="text-left text-red-600 underline"
                        >
                          Cancel
                        </button>
                        {rescheduleId === a.id ? (
                          <span className="flex gap-1">
                            <input
                              type="datetime-local"
                              value={rescheduleValue}
                              onChange={(e) => setRescheduleValue(e.target.value)}
                              className="rounded border px-1 text-xs"
                            />
                            <button
                              onClick={() => handleReschedule(a.id)}
                              className="text-blue-600 underline"
                            >
                              Save
                            </button>
                          </span>
                        ) : (
                          <button
                            onClick={() => {
                              setRescheduleId(a.id);
                              setRescheduleValue(a.start_time.slice(0, 16));
                            }}
                            className="text-left text-blue-600 underline"
                          >
                            Reschedule
                          </button>
                        )}
                      </div>
                    )}
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
