"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiGet, apiPost, apiDelete, ApiError } from "@/lib/api";
import { formatTime } from "@/lib/format";
import { useLanguage } from "@/lib/i18n";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { SkeletonList } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { BlockIcon } from "@/components/icons";
import type { TimeBlock } from "@/lib/types";

export default function TimeOffPage() {
  const { t } = useLanguage();
  const [blocks, setBlocks] = useState<TimeBlock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [date, setDate] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setBlocks(await apiGet<TimeBlock[]>("/api/time-blocks"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load time blocks");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await apiPost("/api/time-blocks", {
        start_time: `${date}T${startTime}:00`,
        end_time: `${date}T${endTime}:00`,
        reason: reason || null,
      });
      setDate("");
      setStartTime("");
      setEndTime("");
      setReason("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create time block");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number) {
    setError(null);
    try {
      await apiDelete(`/api/time-blocks/${id}`);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete time block");
    }
  }

  const upcoming = [...blocks].sort((a, b) => a.start_time.localeCompare(b.start_time));

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={t("timeOff.title")} description={t("timeOff.description")} />

      <Card>
        <h2 className="mb-4 text-sm font-semibold text-slate-900">{t("timeOff.addHeading")}</h2>
        <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            {t("timeOff.date")}
            <Input required type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            {t("timeOff.from")}
            <Input
              required
              type="time"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            {t("timeOff.to")}
            <Input required type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
          </label>
          <label className="flex flex-1 min-w-[10rem] flex-col gap-1 text-sm">
            {t("timeOff.reasonOptional")}
            <Input
              placeholder={t("timeOff.reasonPlaceholder")}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          <Button type="submit" disabled={submitting}>
            {submitting ? t("common.adding") : t("timeOff.addBlock")}
          </Button>
        </form>
      </Card>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Card className="p-0">
        {loading ? (
          <SkeletonList rows={2} />
        ) : upcoming.length === 0 ? (
          <EmptyState icon={BlockIcon} title={t("timeOff.noneBlocked")} />
        ) : (
          <ul className="divide-y divide-slate-100">
            {upcoming.map((b) => (
              <li key={b.id} className="flex items-center gap-4 p-4">
                <BlockIcon className="h-4 w-4 shrink-0 text-slate-400" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-900">
                    {b.start_time.slice(0, 10)} · {formatTime(b.start_time)}–{formatTime(b.end_time)}
                  </p>
                  {b.reason && <p className="truncate text-sm text-slate-500">{b.reason}</p>}
                </div>
                <Button variant="danger" onClick={() => handleDelete(b.id)}>
                  {t("timeOff.remove")}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
