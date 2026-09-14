import { useEffect, useRef, useState } from 'react';
import type { Probabilities } from '../types';

interface Props {
  probs: Probabilities;
  team1Name: string;
  team2Name: string;
  size?: 'sm' | 'md';
}

export function ProbabilityBar({ probs, team1Name, team2Name, size = 'md' }: Props) {
  const [mounted, setMounted] = useState(false);
  const [tooltip, setTooltip] = useState<{ label: string; pct: string; x: number } | null>(null);
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 40);
    return () => clearTimeout(t);
  }, []);

  const t1 = Math.round(probs.team1Win * 100);
  const dr = Math.round(probs.draw * 100);
  const t2 = 100 - t1 - dr;

  const segments = [
    { label: team1Name, pct: t1, bg: 'bg-blue-600', color: 'text-blue-700' },
    { label: 'Draw', pct: dr, bg: 'bg-slate-400', color: 'text-slate-500' },
    { label: team2Name, pct: t2, bg: 'bg-red-500', color: 'text-red-600' },
  ];

  const h = size === 'sm' ? 'h-2' : 'h-3';

  return (
    <div className="w-full">
      <div
        ref={barRef}
        className={`relative ${h} rounded-full overflow-hidden flex bg-slate-200`}
        onMouseLeave={() => setTooltip(null)}
      >
        {segments.map((seg, i) => (
          <div
            key={i}
            className={`${seg.bg} transition-all duration-700 ease-out cursor-default`}
            style={{ width: mounted ? `${seg.pct}%` : '0%' }}
            onMouseEnter={(e) => {
              const rect = barRef.current!.getBoundingClientRect();
              setTooltip({ label: seg.label, pct: `${seg.pct}%`, x: e.clientX - rect.left });
            }}
          />
        ))}
        {tooltip && (
          <div
            className="absolute -top-8 bg-slate-800 text-white text-xs px-2 py-1 rounded pointer-events-none whitespace-nowrap z-10 transform -translate-x-1/2"
            style={{ left: tooltip.x }}
          >
            {tooltip.label}: {tooltip.pct}
          </div>
        )}
      </div>
      {size === 'md' && (
        <div className="flex justify-between mt-1.5 text-xs font-semibold">
          <span className="text-blue-700">{t1}%</span>
          <span className="text-slate-400">{dr}%</span>
          <span className="text-red-600">{t2}%</span>
        </div>
      )}
    </div>
  );
}
