const STATUS_CLASSES: Record<string, string> = {
  booked: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200",
  cancelled: "bg-slate-100 text-slate-500 ring-1 ring-inset ring-slate-200",
  completed: "bg-indigo-50 text-indigo-700 ring-1 ring-inset ring-indigo-200",
};

export function StatusBadge({ status }: { status: string }) {
  const classes = STATUS_CLASSES[status] ?? "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-200";
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${classes}`}>
      {status}
    </span>
  );
}
