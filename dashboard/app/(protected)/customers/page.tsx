"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiGet, apiPost, apiPatch, apiDelete, ApiError } from "@/lib/api";
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
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Customers</h1>

      <form onSubmit={handleCreate} className="flex flex-wrap gap-2">
        <input
          required
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="rounded border px-2 py-1 text-sm"
        />
        <input
          required
          placeholder="Phone"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          className="rounded border px-2 py-1 text-sm"
        />
        <input
          placeholder="Email (optional)"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded border px-2 py-1 text-sm"
        />
        <button type="submit" className="rounded bg-black px-3 py-1 text-sm text-white">
          Add
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-max border-collapse text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="py-2 pr-4">Name</th>
                <th className="pr-4">Phone</th>
                <th className="pr-4">Email</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => (
                <tr key={c.id} className="border-b">
                  {editingId === c.id ? (
                    <>
                      <td className="py-2 pr-4">
                        <input
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          className="rounded border px-1"
                        />
                      </td>
                      <td className="pr-4">
                        <input
                          value={editPhone}
                          onChange={(e) => setEditPhone(e.target.value)}
                          className="rounded border px-1"
                        />
                      </td>
                      <td className="pr-4">
                        <input
                          value={editEmail}
                          onChange={(e) => setEditEmail(e.target.value)}
                          className="rounded border px-1"
                        />
                      </td>
                      <td className="flex gap-2 py-2">
                        <button
                          onClick={() => handleSaveEdit(c.id)}
                          className="text-blue-600 underline"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="text-gray-500 underline"
                        >
                          Cancel
                        </button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="py-2 pr-4">{c.name}</td>
                      <td className="pr-4">{c.phone}</td>
                      <td className="pr-4">{c.email ?? "-"}</td>
                      <td className="flex gap-2 py-2">
                        <button onClick={() => startEdit(c)} className="text-blue-600 underline">
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(c.id)}
                          className="text-red-600 underline"
                        >
                          Delete
                        </button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
