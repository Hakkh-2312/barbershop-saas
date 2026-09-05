"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiGet, apiPatch, ApiError } from "@/lib/api";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import type { Tenant } from "@/lib/types";

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const tenant = await apiGet<Tenant>("/api/tenants/me");
      setName(tenant.name);
      setPhone(tenant.phone ?? "");
      setAddress(tenant.address ?? "");
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
      <PageHeader
        title="Shop Settings"
        description="Shown to customers on WhatsApp when they ask to call you or for your address."
      />

      <Card className="max-w-md">
        {loading ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : (
          <form onSubmit={handleSave} className="flex flex-col gap-4">
            <label className="flex flex-col gap-1 text-sm">
              Shop name
              <Input required value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Phone number
              <Input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+972501234567"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Address
              <Input
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="123 Main St, City"
              />
            </label>

            {error && <p className="text-sm text-red-600">{error}</p>}
            {saved && !error && <p className="text-sm text-emerald-600">Saved.</p>}

            <Button type="submit" disabled={saving} className="self-start">
              {saving ? "Saving..." : "Save"}
            </Button>
          </form>
        )}
      </Card>
    </div>
  );
}
