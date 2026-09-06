export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-slate-200 ${className}`} />;
}

/** Placeholder for the common "Card > ul > li" list pattern used across
 * the dashboard, shaped roughly like the real rows (a leading icon/dot,
 * two lines of text, a trailing control) so the loading state doesn't
 * visually jump when the real content replaces it. */
export function SkeletonList({ rows = 4 }: { rows?: number }) {
  return (
    <ul className="divide-y divide-slate-100">
      {Array.from({ length: rows }).map((_, i) => (
        <li key={i} className="flex items-center gap-4 p-4">
          <Skeleton className="h-9 w-9 shrink-0 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3.5 w-1/3" />
            <Skeleton className="h-3 w-1/4" />
          </div>
          <Skeleton className="h-8 w-20 shrink-0 rounded-lg" />
        </li>
      ))}
    </ul>
  );
}
