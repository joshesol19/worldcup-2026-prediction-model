import type { Cache2026, Cache2022, FixtureData } from './types';

const BASE = '/api';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  get2026: () => get<Cache2026>('/predictions/2026'),
  get2022: () => get<Cache2022>('/predictions/2022'),
  getFixtures: () => get<FixtureData>('/fixtures'),
};
