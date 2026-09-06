import type { ReactElement, SVGProps } from "react";

export function EmptyState({
  icon: Icon,
  title,
}: {
  icon: (props: SVGProps<SVGSVGElement>) => ReactElement;
  title: string;
}) {
  return (
    <div className="flex flex-col items-center gap-3 p-10 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-400">
        <Icon className="h-5 w-5" />
      </div>
      <p className="text-sm text-slate-500">{title}</p>
    </div>
  );
}
