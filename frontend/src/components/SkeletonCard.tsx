export function SkeletonRow() {
  return (
    <div className="bg-white border border-slate-200 rounded-xl px-4 py-3 animate-pulse flex items-center gap-4">
      <div className="h-4 bg-slate-200 rounded w-24 shrink-0" />
      <div className="flex-1 flex items-center gap-3">
        <div className="h-5 bg-slate-200 rounded w-8" />
        <div className="h-4 bg-slate-200 rounded w-28" />
        <div className="h-3 bg-slate-200 rounded w-6" />
        <div className="h-5 bg-slate-200 rounded w-8" />
        <div className="h-4 bg-slate-200 rounded w-28" />
      </div>
      <div className="h-4 bg-slate-200 rounded w-20 shrink-0" />
    </div>
  );
}
