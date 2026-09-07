"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiGet } from "./api";
import { useAuth } from "./auth";
import type { Tenant } from "./types";

interface TenantContextValue {
  tenant: Tenant | null;
  refreshTenant: () => void;
}

const TenantContext = createContext<TenantContextValue | undefined>(undefined);

/** Fetches the current shop's tenant record once per session and shares
 * it everywhere it's needed (sidebar shop name, WhatsApp country code on
 * Today/Appointments, ...) instead of every page re-fetching the same
 * mostly-static row - each `/api/tenants/me` call is a real, measurable
 * round trip, and several pages were making it redundantly on every
 * navigation alongside the layout's own fetch. */
export function TenantProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const [tenant, setTenant] = useState<Tenant | null>(null);

  function refreshTenant() {
    if (!token) {
      setTenant(null);
      return;
    }
    apiGet<Tenant>("/api/tenants/me")
      .then(setTenant)
      .catch(() => setTenant(null));
  }

  useEffect(() => {
    refreshTenant();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <TenantContext.Provider value={{ tenant, refreshTenant }}>{children}</TenantContext.Provider>
  );
}

export function useTenant(): TenantContextValue {
  const ctx = useContext(TenantContext);
  if (!ctx) {
    throw new Error("useTenant must be used within a TenantProvider");
  }
  return ctx;
}
