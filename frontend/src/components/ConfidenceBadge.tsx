import type { Confidence } from '../types';

const CONFIG: Record<Confidence, { label: string; cls: string }> = {
  low:      { label: "Anyone's game",  cls: 'bg-amber-100 text-amber-700 border-amber-200' },
  moderate: { label: 'Slight edge',    cls: 'bg-blue-100 text-blue-700 border-blue-200' },
  high:     { label: 'Clear favourite',cls: 'bg-green-100 text-green-700 border-green-200' },
};

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const { label, cls } = CONFIG[confidence];
  return (
    <span className={`text-xs px-2.5 py-0.5 rounded-full border font-medium ${cls}`}>
      {label}
    </span>
  );
}
