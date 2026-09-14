import type { Cache2026, Cache2022, FixtureData } from './types';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  get2026: () => get<Cache2026>('/data/predictions_2026.json'),
  get2022: () => get<Cache2022>('/data/predictions_2022.json'),
  getFixtures: () => get<FixtureData>('/data/fixtures.json'),
};
