"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { Skeleton } from "@/components/Skeleton";
import type { Tenant } from "@/lib/types";

export default function BillingPage() {
  const { t } = useLanguage();
  const searchParams = useSearchParams();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [trialDaysLeft, setTrialDaysLeft] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [redirecting, setRedirecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const checkoutResult = searchParams.get("billing");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const myTenant = await apiGet<Tenant>("/api/tenants/me");
      setTenant(myTenant);
      setTrialDaysLeft(
        myTenant.trial_ends_at
          ? Math.max(
              0,
              Math.ceil((new Date(myTenant.trial_ends_at).getTime() - Date.now()) / 86400000)
            )
          : null
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load billing status");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSubscribe() {
    setError(null);
    setRedirecting(true);
    try {
      const { url } = await apiPost<{ url: string }>("/api/billing/checkout");
      window.location.href = url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start checkout");
      setRedirecting(false);
    }
  }

  async function handleManage() {
    setError(null);
    setRedirecting(true);
    try {
      const { url } = await apiPost<{ url: string }>("/api/billing/portal");
      window.location.href = url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to open billing portal");
      setRedirecting(false);
    }
  }

  function statusLine(): { text: string; tone: "neutral" | "good" | "warning" } {
    if (!tenant) return { text: "", tone: "neutral" };

    if (tenant.subscription_status === null) {
      return { text: t("billing.grandfathered"), tone: "good" };
    }
    if (tenant.subscription_status === "active" || tenant.subscription_status === "trialing") {
      if (tenant.subscription_status === "trialing" && trialDaysLeft !== null) {
        return trialDaysLeft > 0
          ? { text: t("billing.trialDaysLeft", { days: trialDaysLeft }), tone: "neutral" }
          : { text: t("billing.trialExpired"), tone: "warning" };
      }
      return { text: t("billing.active"), tone: "good" };
    }
    if (tenant.subscription_status === "past_due") {
      return { text: t("billing.pastDue"), tone: "warning" };
    }
    return { text: t("billing.canceled"), tone: "warning" };
  }

  const status = statusLine();
  const canManage = tenant?.subscription_status === "active" || tenant?.subscription_status === "past_due";
  const canSubscribe = tenant?.subscription_status !== null && !canManage;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={t("billing.title")} description={t("billing.description")} />

      {checkoutResult === "success" && (
        <p className="text-sm text-emerald-600">{t("billing.success")}</p>
      )}
      {checkoutResult === "cancelled" && (
        <p className="text-sm text-slate-500">{t("billing.cancelledCheckout")}</p>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}

      <Card className="max-w-md">
        {loading ? (
          <div className="flex flex-col gap-4">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-9 w-28 rounded-lg" />
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <p
              className={`text-sm font-medium ${
                status.tone === "good"
                  ? "text-emerald-700"
                  : status.tone === "warning"
                    ? "text-red-600"
                    : "text-slate-700"
              }`}
            >
              {status.text}
            </p>

            {canSubscribe && (
              <Button onClick={handleSubscribe} disabled={redirecting} className="self-start">
                {t("billing.subscribe")}
              </Button>
            )}
            {canManage && (
              <Button
                variant="secondary"
                onClick={handleManage}
                disabled={redirecting}
                className="self-start"
              >
                {t("billing.manage")}
              </Button>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
