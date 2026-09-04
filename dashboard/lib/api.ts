import type { Token } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

interface ValidationDetail {
  msg: string;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.status === 204) {
    return undefined as T;
  }

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const detail = data?.detail;
    let message = `Request failed (${res.status})`;
    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = (detail as ValidationDetail[]).map((d) => d.msg).join("; ");
    }
    throw new ApiError(res.status, message);
  }

  return data as T;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { headers: { ...authHeaders() } });
  return handleResponse<T>(res);
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(res);
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  return handleResponse<T>(res);
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  return handleResponse<T>(res);
}

export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  return handleResponse<void>(res);
}

export async function login(email: string, password: string): Promise<Token> {
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    body: new URLSearchParams({ username: email, password }),
  });
  return handleResponse<Token>(res);
}

export async function signup(
  tenantName: string,
  email: string,
  password: string
): Promise<Token> {
  return apiPost<Token>("/api/auth/signup", {
    tenant_name: tenantName,
    email,
    password,
  });
}
