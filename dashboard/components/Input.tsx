import type { InputHTMLAttributes } from "react";

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 transition-shadow duration-150 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/25 ${className}`}
      {...props}
    />
  );
}
