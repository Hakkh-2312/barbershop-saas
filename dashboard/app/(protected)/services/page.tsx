"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiGet, apiPost, apiPatch, apiDelete, ApiError } from "@/lib/api";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import type { Service } from "@/lib/types";

export default function ServicesPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [durationMinutes, setDurationMinutes] = useState("");
  const [price, setPrice] = useState("");

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editDuration, setEditDuration] = useState("");
  const [editPrice, setEditPrice] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setServices(await apiGet<Service[]>("/api/services"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load services");
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
    try {
      await apiPost("/api/services", {
        name,
        duration_minutes: Number(durationMinutes),
        price: Number(price),
      });
      setName("");
      setDurationMinutes("");
      setPrice("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create service");
    }
  }

  function startEdit(s: Service) {
    setEditingId(s.id);
    setEditName(s.name);
    setEditDuration(String(s.duration_minutes));
    setEditPrice(String(s.price));
  }

  async function handleSaveEdit(id: number) {
    setError(null);
    try {
      await apiPatch(`/api/services/${id}`, {
        name: editName,
        duration_minutes: Number(editDuration),
        price: Number(editPrice),
      });
      setEditingId(null);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update service");
    }
  }

  async function handleDelete(id: number) {
    setError(null);
    try {
      await apiDelete(`/api/services/${id}`);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete service");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Services" description="What customers can book, with duration and price." />

      <Card>
        <h2 className="mb-4 text-sm font-semibold text-slate-900">Add a service</h2>
        <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-3">
          <label className="flex flex-1 min-w-[10rem] flex-col gap-1 text-sm">
            Name
            <Input required value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Duration (min)
            <Input
              required
              type="number"
              min={1}
              className="w-28"
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Price (₪)
            <Input
              required
              type="number"
              min={1}
              className="w-24"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
            />
          </label>
          <Button type="submit">Add</Button>
        </form>
      </Card>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Card className="p-0">
        {loading ? (
          <p className="p-5 text-sm text-slate-500">Loading...</p>
        ) : services.length === 0 ? (
          <p className="p-5 text-sm text-slate-500">No services yet.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {services.map((s) => (
              <li key={s.id} className="flex flex-wrap items-center gap-4 p-4">
                {editingId === s.id ? (
                  <>
                    <Input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="min-w-[10rem] flex-1"
                    />
                    <Input
                      type="number"
                      min={1}
                      value={editDuration}
                      onChange={(e) => setEditDuration(e.target.value)}
                      className="w-24"
                    />
                    <Input
                      type="number"
                      min={1}
                      value={editPrice}
                      onChange={(e) => setEditPrice(e.target.value)}
                      className="w-24"
                    />
                    <div className="flex gap-2">
                      <Button variant="secondary" onClick={() => handleSaveEdit(s.id)}>
                        Save
                      </Button>
                      <Button variant="ghost" onClick={() => setEditingId(null)}>
                        Cancel
                      </Button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-900">{s.name}</p>
                      <p className="truncate text-sm text-slate-500">
                        {s.duration_minutes} min · {s.price} ₪
                      </p>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <Button variant="secondary" onClick={() => startEdit(s)}>
                        Edit
                      </Button>
                      <Button variant="danger" onClick={() => handleDelete(s.id)}>
                        Delete
                      </Button>
                    </div>
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
