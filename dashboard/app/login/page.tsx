"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login as loginRequest, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useLanguage } from "@/lib/i18n";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";

export default function LoginPage() {
  const { t, lang, setLang } = useLanguage();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { access_token } = await loginRequest(email, password);
      login(access_token);
      router.push("/today");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen w-full items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">{t("login.title")}</h1>
            <p className="mt-1 text-sm text-slate-500">{t("login.subtitle")}</p>
          </div>
          <button
            type="button"
            onClick={() => setLang(lang === "ar" ? "en" : "ar")}
            className="shrink-0 text-sm font-medium text-indigo-600 hover:text-indigo-700"
          >
            {t("lang.switchTo")}
          </button>
        </div>
        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-3">
          <Input
            type="email"
            required
            placeholder={t("login.email")}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Input
            type="password"
            required
            placeholder={t("login.password")}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" disabled={submitting} className="mt-1 justify-center">
            {submitting ? t("login.submitting") : t("login.submit")}
          </Button>
        </form>
        <p className="mt-6 text-sm text-slate-500">
          {t("login.noShop")}{" "}
          <Link href="/signup" className="font-medium text-indigo-600 hover:text-indigo-700">
            {t("login.signUp")}
          </Link>
        </p>
      </div>
    </main>
  );
}
