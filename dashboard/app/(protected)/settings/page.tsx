"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiGet, apiPatch, ApiError } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import type { Tenant } from "@/lib/types";

export default function SettingsPage() {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [countryCode, setCountryCode] = useState("");
  const [whatsappNumberId, setWhatsappNumberId] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const tenant = await apiGet<Tenant>("/api/tenants/me");
      setName(tenant.name);
      setPhone(tenant.phone ?? "");
      setAddress(tenant.address ?? "");
      setCountryCode(tenant.country_code ?? "");
      setWhatsappNumberId(tenant.whatsapp_phone_number_id ?? "");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load shop settings");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaved(false);
    setSaving(true);
    try {
      await apiPatch<Tenant>("/api/tenants/me", {
        name,
        phone: phone || null,
        address: address || null,
        country_code: countryCode || null,
        whatsapp_phone_number_id: whatsappNumberId || null,
      });
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save shop settings");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={t("settings.title")} description={t("settings.description")} />

      <Card className="max-w-md">
        {loading ? (
          <p className="text-sm text-slate-500">{t("common.loading")}</p>
        ) : (
          <form onSubmit={handleSave} className="flex flex-col gap-4">
            <label className="flex flex-col gap-1 text-sm">
              {t("settings.shopName")}
              <Input required value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              {t("settings.phone")}
              <Input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+972501234567"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              {t("settings.address")}
              <Input
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="123 Main St, City"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              {t("settings.countryCode")}
              <Input
                value={countryCode}
                onChange={(e) => setCountryCode(e.target.value)}
                placeholder="972"
              />
              <span className="text-xs text-slate-500">{t("settings.countryCodeHelp")}</span>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              {t("settings.whatsappNumberId")}
              <Input
                value={whatsappNumberId}
                onChange={(e) => setWhatsappNumberId(e.target.value)}
                placeholder="123456123456789"
              />
              <span className="text-xs text-slate-500">{t("settings.whatsappNumberIdHelp")}</span>
            </label>

            {error && <p className="text-sm text-red-600">{error}</p>}
            {saved && !error && <p className="text-sm text-emerald-600">{t("settings.saved")}</p>}

            <Button type="submit" disabled={saving} className="self-start">
              {saving ? t("common.saving") : t("common.save")}
            </Button>
          </form>
        )}
      </Card>
    </div>
  );
}
