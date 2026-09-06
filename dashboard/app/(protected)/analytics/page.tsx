"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, ApiError } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Input } from "@/components/Input";
import { Button } from "@/components/Button";
import { Skeleton } from "@/components/Skeleton";
import type { AnalyticsOverview } from "@/lib/types";

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(amount);
}

type Range = "today" | "week" | "month" | "custom";

export default function AnalyticsPage() {
  const { t } = useLanguage();
  const [range, setRange] = useState<Range>("today");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (range === "custom" && (!customStart || !customEnd)) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ range });
      if (range === "custom") {
        params.set("start", customStart);
        params.set("end", customEnd);
      }
      setData(await apiGet<AnalyticsOverview>(`/api/analytics/overview?${params.toString()}`));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, [range, customStart, customEnd]);

  useEffect(() => {
    load();
  }, [load]);

  const rangeOptions: { value: Range; label: string }[] = [
    { value: "today", label: t("analytics.today") },
    { value: "week", label: t("analytics.thisWeek") },
    { value: "month", label: t("analytics.thisMonth") },
    { value: "custom", label: t("analytics.custom") },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={t("analytics.title")} description={t("analytics.description")} />

      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-wrap gap-2">
            {rangeOptions.map((opt) => (
              <Button
                key={opt.value}
                variant={range === opt.value ? "primary" : "secondary"}
                onClick={() => setRange(opt.value)}
              >
                {opt.label}
              </Button>
            ))}
          </div>

          {range === "custom" && (
            <>
              <label className="flex flex-col gap-1 text-sm">
                {t("analytics.from")}
                <Input
                  type="date"
                  value={customStart}
                  onChange={(e) => setCustomStart(e.target.value)}
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                {t("analytics.to")}
                <Input
                  type="date"
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                />
              </label>
            </>
          )}
        </div>
      </Card>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <Skeleton className="h-3.5 w-24" />
              <Skeleton className="mt-2 h-8 w-16" />
            </Card>
          ))}
        </div>
      ) : data ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <p className="text-sm text-slate-500">{t("analytics.revenue")}</p>
            <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-900">
              ₪{formatCurrency(data.revenue)}
            </p>
          </Card>
          <Card>
            <p className="text-sm text-slate-500">{t("analytics.newCustomers")}</p>
            <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-900">
              {data.new_customers}
            </p>
          </Card>
          <Card>
            <p className="text-sm text-slate-500">{t("analytics.returningCustomers")}</p>
            <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-900">
              {data.returning_customers}
            </p>
          </Card>
          <Card>
            <p className="text-sm text-slate-500">{t("analytics.totalCustomers")}</p>
            <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-900">
              {data.total_customers}
            </p>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
