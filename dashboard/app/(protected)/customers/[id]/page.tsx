"use client";

import { use, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { apiGet, apiPatch, ApiError } from "@/lib/api";
import { dateLocale, useLanguage } from "@/lib/i18n";
import { formatDateLong } from "@/lib/format";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { Skeleton } from "@/components/Skeleton";
import type { CustomerProfile } from "@/lib/types";

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
    </Card>
  );
}

export default function CustomerProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { t, lang } = useLanguage();

  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [notes, setNotes] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);
  const [notesSaved, setNotesSaved] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const data = await apiGet<CustomerProfile>(`/api/customers/${id}`);
      setProfile(data);
      setNotes(data.notes ?? "");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setNotFound(true);
      } else {
        setError(err instanceof ApiError ? err.message : "Failed to load customer");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function handleSaveNotes(e: FormEvent) {
    e.preventDefault();
    setSavingNotes(true);
    setNotesSaved(false);
    setError(null);
    try {
      const updated = await apiPatch<CustomerProfile>(`/api/customers/${id}`, {
        notes: notes || null,
      });
      setProfile((prev) => (prev ? { ...prev, notes: updated.notes } : prev));
      setNotesSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save notes");
    } finally {
      setSavingNotes(false);
    }
  }

  if (notFound) {
    return (
      <div className="flex flex-col gap-6">
        <Link href="/customers" className="text-sm text-indigo-600 hover:text-indigo-700">
          {t("customers.backToCustomers")}
        </Link>
        <Card>
          <p className="text-sm text-slate-500">{t("customers.notFound")}</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Link href="/customers" className="text-sm text-indigo-600 hover:text-indigo-700">
        {t("customers.backToCustomers")}
      </Link>

      <PageHeader
        title={loading ? "" : (profile?.name ?? "")}
        description={loading ? "" : `${profile?.phone ?? ""}${profile?.email ? ` · ${profile.email}` : ""}`}
      />

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <Skeleton className="h-3 w-20" />
              <Skeleton className="mt-2 h-7 w-14" />
            </Card>
          ))}
        </div>
      ) : (
        profile && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile label={t("customers.totalAppointments")} value={String(profile.total_appointments)} />
            <StatTile label={t("customers.totalSpent")} value={`₪${profile.total_spent}`} />
            <StatTile
              label={t("customers.lastVisit")}
              value={
                profile.last_visit
                  ? formatDateLong(profile.last_visit.slice(0, 10), dateLocale(lang))
                  : t("customers.noVisitsYet")
              }
            />
            <StatTile
              label={t("customers.favoriteService")}
              value={profile.favorite_service ?? t("customers.noneYetShort")}
            />
          </div>
        )
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Card className="max-w-lg">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">{t("customers.notes")}</h2>
        {loading ? (
          <Skeleton className="h-24 w-full rounded-lg" />
        ) : (
          <form onSubmit={handleSaveNotes} className="flex flex-col gap-3">
            <textarea
              value={notes}
              onChange={(e) => {
                setNotes(e.target.value);
                setNotesSaved(false);
              }}
              placeholder={t("customers.notesPlaceholder")}
              rows={4}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 transition-shadow duration-150 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/25"
            />
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={savingNotes} className="self-start">
                {savingNotes ? t("common.saving") : t("common.save")}
              </Button>
              {notesSaved && <span className="text-sm text-emerald-600">{t("settings.saved")}</span>}
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}
