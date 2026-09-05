"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiGet, apiPost, apiPatch, apiDelete, ApiError } from "@/lib/api";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import type { Customer } from "@/lib/types";

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [editEmail, setEditEmail] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setCustomers(await apiGet<Customer[]>("/api/customers"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load customers");
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
      await apiPost("/api/customers", { name, phone, email: email || null });
      setName("");
      setPhone("");
      setEmail("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create customer");
    }
  }

  function startEdit(c: Customer) {
    setEditingId(c.id);
    setEditName(c.name);
    setEditPhone(c.phone);
    setEditEmail(c.email ?? "");
  }

  async function handleSaveEdit(id: number) {
    setError(null);
    try {
      await apiPatch(`/api/customers/${id}`, {
        name: editName,
        phone: editPhone,
        email: editEmail || null,
      });
      setEditingId(null);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update customer");
    }
  }

  async function handleDelete(id: number) {
    setError(null);
    try {
      await apiDelete(`/api/customers/${id}`);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete customer");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Customers" description="Everyone who's booked with your shop." />

      <Card>
        <h2 className="mb-4 text-sm font-semibold text-slate-900">Add a customer</h2>
        <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            Name
            <Input required value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Phone
            <Input required value={phone} onChange={(e) => setPhone(e.target.value)} />
          </label>
          <label className="flex flex-1 min-w-[10rem] flex-col gap-1 text-sm">
            Email (optional)
            <Input value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <Button type="submit">Add</Button>
        </form>
      </Card>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Card className="p-0">
        {loading ? (
          <p className="p-5 text-sm text-slate-500">Loading...</p>
        ) : customers.length === 0 ? (
          <p className="p-5 text-sm text-slate-500">No customers yet.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {customers.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center gap-4 p-4">
                {editingId === c.id ? (
                  <>
                    <Input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="w-40"
                    />
                    <Input
                      value={editPhone}
                      onChange={(e) => setEditPhone(e.target.value)}
                      className="w-36"
                    />
                    <Input
                      value={editEmail}
                      onChange={(e) => setEditEmail(e.target.value)}
                      className="min-w-[10rem] flex-1"
                    />
                    <div className="flex gap-2">
                      <Button variant="secondary" onClick={() => handleSaveEdit(c.id)}>
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
                      <p className="truncate text-sm font-medium text-slate-900">{c.name}</p>
                      <p className="truncate text-sm text-slate-500">
                        {c.phone}
                        {c.email ? ` · ${c.email}` : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <Button variant="secondary" onClick={() => startEdit(c)}>
                        Edit
                      </Button>
                      <Button variant="danger" onClick={() => handleDelete(c.id)}>
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
