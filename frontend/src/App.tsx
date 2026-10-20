import { useEffect, useRef, useState } from 'react';
import type { Cache2026, Cache2022, FixtureData, Match2026, Match2022 } from './types';
import { api } from './api';
import { Tab2026 } from './components/Tab2026';
import { Tab2022 } from './components/Tab2022';
import { FifaRankingsTab } from './components/FifaRankingsTab';
import { MatchDetailPage } from './pages/MatchDetailPage';
import { BracketPage } from './pages/BracketPage';
import { AboutPage } from './pages/AboutPage';
import { About2022Page } from './pages/About2022Page';
import { AnimatedThemeToggler } from './components/ui/animated-theme-toggler';

type TabId = '2026' | '2022';
type Route =
  | { view: 'home'; tab: TabId }
  | { view: 'match'; matchId: string; year: '2026' | '2022' }
  | { view: 'bracket' }
  | { view: 'about' }
  | { view: 'about2022' };

function useData() {
  const [data2026, setData2026] = useState<Cache2026 | null>(null);
  const [data2022, setData2022] = useState<Cache2022 | null>(null);
  const [fixtures, setFixtures] = useState<FixtureData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const e = (err: unknown) => setError(String((err as Error)?.message ?? err));
    Promise.all([api.get2026(), api.get2022(), api.getFixtures()])
      .then(([d26, d22, fix]) => { setData2026(d26); setData2022(d22); setFixtures(fix); })
      .catch(e)
      .finally(() => setLoading(false));
  }, []);

  return { data2026, data2022, fixtures, loading, error };
}

function resolveMatch(
  matchId: string,
  year: '2026' | '2022',
  data2026: Cache2026 | null,
  data2022: Cache2022 | null,
): Match2026 | Match2022 | null {
  if (year === '2026')
    return data2026?.matches.find(m => m.matchId === matchId)
        ?? data2026?.bracketMatches?.find(m => m.matchId === matchId)
        ?? null;
  return data2022?.matches.find(m => m.matchId === matchId) ?? null;
}

type SubTab2026 = 'matches' | 'bracket' | 'rankings';

export default function App() {
  const [route, setRoute] = useState<Route>({ view: 'home', tab: '2026' });
  const [subTab2026, setSubTab2026] = useState<SubTab2026>('matches');
  const { data2026, data2022, fixtures, loading, error } = useData();
  const topRef = useRef<HTMLDivElement>(null);

  const navigate = (r: Route) => {
    setRoute(r);
    topRef.current?.scrollIntoView({ behavior: 'instant' });
  };

  // Wire up the "Learn more" links in sub-pages
  useEffect(() => {
    (window as any).__navigateAbout = () => navigate({ view: 'about' });
    return () => { delete (window as any).__navigateAbout; };
  }, []);

  // Update page title based on route
  useEffect(() => {
    const base = '2026 FIFA World Cup Predictions';
    const titles: Record<string, string> = {
      bracket: `Predicted Bracket · ${base}`,
      about: `About the Model · ${base}`,
      about2022: `2022 Retrospective · ${base}`,
    };
    if (route.view === 'match') {
      document.title = `Match Details · ${base}`;
    } else if (route.view === 'home' && route.tab === '2022') {
      document.title = `2022 Retrospective · ${base}`;
    } else if (route.view === 'home' && subTab2026 === 'bracket') {
      document.title = `Predicted Bracket · ${base}`;
    } else {
      document.title = titles[route.view] ?? base;
    }
  }, [route, subTab2026]);

  const tab = (route.view === 'home' ? route.tab : '2026') as TabId;

  // ── Sub-pages ─────────────────────────────────────────────────────────────
  if (route.view === 'match') {
    const match = resolveMatch(route.matchId, route.year, data2026, data2022);
    if (!match) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <p className="text-slate-500">Match not found.</p>
            <button onClick={() => navigate({ view: 'home', tab })} className="mt-3 text-blue-600 text-sm hover:underline">
              ← Go back
            </button>
          </div>
        </div>
      );
    }
    return (
      <div ref={topRef}>
        <MatchDetailPage
          match={match}
          onBack={() => {
            if (route.view === 'match' && route.matchId.startsWith('bracket_')) {
              navigate({ view: 'bracket' });
            } else {
              navigate({ view: 'home', tab: route.year as TabId });
            }
          }}
        />
      </div>
    );
  }

  if (route.view === 'bracket') {
    if (!data2026) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <p className="text-slate-500">Loading bracket…</p>
        </div>
      );
    }
    return (
      <div ref={topRef}>
        <BracketPage
          data2026={data2026}
          onBack={() => navigate({ view: 'home', tab: '2026' })}
          onMatchClick={(id, year) => navigate({ view: 'match', matchId: id, year })}
        />
      </div>
    );
  }

  if (route.view === 'about') {
    return (
      <div ref={topRef}>
        <AboutPage onBack={() => navigate({ view: 'home', tab })} />
      </div>
    );
  }

  if (route.view === 'about2022') {
    if (!data2022) return null;
    return (
      <div ref={topRef}>
        <About2022Page data={data2022} onBack={() => navigate({ view: 'home', tab: '2022' })} />
      </div>
    );
  }

  // ── Home (tabs) ───────────────────────────────────────────────────────────
  return (
    <div ref={topRef} className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-5xl mx-auto px-4">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center gap-4">
              <div>
                <h1 className="text-xl font-black text-slate-900 leading-none">2026 FIFA World Cup</h1>
                <p className="text-sm text-slate-400 leading-none mt-1">June 11 – July 19 · USA / Canada / Mexico</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <AnimatedThemeToggler />
              <button
                onClick={() => navigate({ view: 'about' })}
                className="text-sm text-slate-500 hover:text-slate-800 hover:bg-slate-100 px-4 py-2 rounded-lg transition-colors"
              >
                About the predictions
              </button>
            </div>
          </div>

          {/* Tab bar */}
          <div className="flex -mb-px">
            {([['2026', '2026 Predictions'], ['2022', '2022 Retrospective']] as [TabId, string][]).map(([id, label]) => (
              <button
                key={id}
                onClick={() => navigate({ view: 'home', tab: id as TabId })}
                className={`px-6 py-3 text-sm font-semibold border-b-2 transition-all ${
                  route.view === 'home' && tab === id
                    ? 'border-green-600 text-green-700'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* 2026 sub-tabs */}
          {route.view === 'home' && tab === '2026' && (
            <div className="flex mt-px">
              {([['matches', 'Group Stage Matches'], ['bracket', 'Predicted Bracket'], ['rankings', 'FIFA Rankings']] as [SubTab2026, string][]).map(([id, label]) => (
                <button
                  key={id}
                  onClick={() => setSubTab2026(id)}
                  className={`px-4 py-2 text-xs font-medium transition-all border-l border-r border-t-0 border-b-0 ${
                    subTab2026 === id
                      ? 'bg-green-50 text-green-700 border-green-200'
                      : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50 border-transparent'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="max-w-5xl mx-auto px-4 mt-4">
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
            <strong>Could not load predictions.</strong> Make sure the backend is running on localhost:5050.
            <br /><span className="text-red-500 text-xs">{error}</span>
          </div>
        </div>
      )}

      {/* Main content */}
      <main className="max-w-5xl mx-auto px-4 py-8">
        {tab === '2026' && subTab2026 === 'matches' && (
          <Tab2026
            data={data2026}
            fixtures={fixtures}
            loading={loading}
            onMatchClick={(id, year) => navigate({ view: 'match', matchId: id, year })}
          />
        )}
        {tab === '2026' && subTab2026 === 'bracket' && (
          data2026
            ? <BracketPage
                data2026={data2026}
                inline
                onBack={() => setSubTab2026('matches')}
                onMatchClick={(id, year) => navigate({ view: 'match', matchId: id, year })}
              />
            : <div className="text-center py-20 text-slate-400">Loading bracket…</div>
        )}
        {tab === '2026' && subTab2026 === 'rankings' && (
          <FifaRankingsTab data={data2026} loading={loading} />
        )}
        {tab === '2022' && (
          <Tab2022
            data={data2022}
            loading={loading}
            onMatchClick={(id, year) => navigate({ view: 'match', matchId: id, year })}
            onAboutClick={() => navigate({ view: 'about2022' })}
          />
        )}
      </main>

      <footer className="border-t border-slate-200 bg-white mt-16">
        <div className="max-w-5xl mx-auto px-4 py-10">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 mb-8">
            {/* Branding */}
            <div>
              <p className="text-sm font-black text-slate-900 mb-1">2026 FIFA World Cup Predictions</p>
              <p className="text-xs text-slate-500 leading-relaxed">
                A machine learning model trained on 32,000+ international matches predicting
                outcomes for every 2026 World Cup game.
              </p>
              <p className="text-xs text-slate-400 mt-3">Not affiliated with FIFA.</p>
            </div>

            {/* Model */}
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">The Model</p>
              <ul className="space-y-2">
                <li>
                  <button
                    onClick={() => navigate({ view: 'about' })}
                    className="text-sm text-slate-600 hover:text-green-700 transition-colors"
                  >
                    About the predictions
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => navigate({ view: 'bracket' })}
                    className="text-sm text-slate-600 hover:text-green-700 transition-colors"
                  >
                    Predicted bracket
                  </button>
                </li>
              </ul>
            </div>

            {/* Author */}
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Author</p>
              <ul className="space-y-2">
                {[
                  { label: 'About the Author', href: 'https://www.joshuasolano.com' },
                  { label: "Author's Portfolio", href: 'https://joshuasolano.com/portfolio.html' },
                  { label: 'LinkedIn', href: 'https://www.linkedin.com/in/josh-solano/' },
                  { label: 'Email Author', href: 'mailto:jsolano5@student.byu.edu' },
                ].map(({ label, href }) => (
                  <li key={label}>
                    <a
                      href={href}
                      target={href.startsWith('mailto') ? undefined : '_blank'}
                      rel="noreferrer"
                      className="text-sm text-slate-600 hover:text-green-700 transition-colors"
                    >
                      {label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="border-t border-slate-100 pt-6 text-center text-xs text-slate-400">
            Built by Joshua Solano · 2026 FIFA World Cup Prediction Project
          </div>
        </div>
      </footer>
    </div>
  );
}
