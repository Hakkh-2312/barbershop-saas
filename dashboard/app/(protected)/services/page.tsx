"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiGet, apiPost, apiPatch, apiDelete, ApiError } from "@/lib/api";
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
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Services</h1>

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
          type="number"
          min={1}
          placeholder="Duration (minutes)"
          value={durationMinutes}
          onChange={(e) => setDurationMinutes(e.target.value)}
          className="rounded border px-2 py-1 text-sm"
        />
        <input
          required
          type="number"
          min={1}
          placeholder="Price"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
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
                <th className="pr-4">Duration (min)</th>
                <th className="pr-4">Price</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {services.map((s) => (
                <tr key={s.id} className="border-b">
                  {editingId === s.id ? (
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
                          type="number"
                          min={1}
                          value={editDuration}
                          onChange={(e) => setEditDuration(e.target.value)}
                          className="w-20 rounded border px-1"
                        />
                      </td>
                      <td className="pr-4">
                        <input
                          type="number"
                          min={1}
                          value={editPrice}
                          onChange={(e) => setEditPrice(e.target.value)}
                          className="w-20 rounded border px-1"
                        />
                      </td>
                      <td className="flex gap-2 py-2">
                        <button
                          onClick={() => handleSaveEdit(s.id)}
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
                      <td className="py-2 pr-4">{s.name}</td>
                      <td className="pr-4">{s.duration_minutes}</td>
                      <td className="pr-4">{s.price}</td>
                      <td className="flex gap-2 py-2">
                        <button onClick={() => startEdit(s)} className="text-blue-600 underline">
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(s.id)}
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
