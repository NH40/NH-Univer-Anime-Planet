import { getInitData } from "./telegram";

const API_BASE = "/api";

async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "X-Telegram-Init-Data": getInitData() },
  });
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${await response.text()}`);
  }
  return response.json() as Promise<T>;
}

export interface Profile {
  id: number;
  display_name: string | null;
  universe_selected: string | null;
  ubp_season: number;
  ubp_total: number;
  dust: number;
  coins: number;
}

export interface Universe {
  code: string;
  title: string;
}

export interface CardStack {
  card_id: number;
  external_id: string;
  name: string;
  description: string | null;
  base_ubp: number;
  stars: number;
  quantity: number;
  image_url: string;
}

export interface UniverseProgress {
  code: string;
  title: string;
  owned: number;
  total: number;
  percent: number;
}

export function fetchProfile(): Promise<Profile> {
  return apiFetch<Profile>("/me");
}

export function fetchUniverses(): Promise<Universe[]> {
  return apiFetch<Universe[]>("/universes");
}

export function fetchCollection(universeCode: string): Promise<CardStack[]> {
  return apiFetch<CardStack[]>(`/collection/${encodeURIComponent(universeCode)}`);
}

export function fetchProgress(): Promise<UniverseProgress[]> {
  return apiFetch<UniverseProgress[]>("/progress");
}
