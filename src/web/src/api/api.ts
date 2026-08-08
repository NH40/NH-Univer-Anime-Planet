import { getInitData } from '../telegram'

const API_BASE = '/api'

async function apiFetch<T>(path: string): Promise<T> {
	const response = await fetch(`${API_BASE}${path}`, {
		headers: { 'X-Telegram-Init-Data': getInitData() },
	})
	if (!response.ok) {
		throw new Error(`API error ${response.status}: ${await response.text()}`)
	}
	return response.json() as Promise<T>
}

// Первый write-запрос Mini App (см. CLAUDE.md, "Mini App") — используется только для
// /battle-pass/claim, остальной API по-прежнему read-only через apiFetch выше.
async function apiPost<T>(path: string, body: unknown): Promise<T> {
	const response = await fetch(`${API_BASE}${path}`, {
		method: 'POST',
		headers: {
			'X-Telegram-Init-Data': getInitData(),
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(body),
	})
	if (!response.ok) {
		throw new Error(`API error ${response.status}: ${await response.text()}`)
	}
	return response.json() as Promise<T>
}

export interface Profile {
	id: number
	display_name: string | null
	universe_selected: string | null
	ubp_season: number
	ubp_total: number
	dust: number
	coins: number
}

export interface Universe {
	code: string
	title: string
}

export interface CardStack {
	card_id: number
	external_id: string
	name: string
	description: string | null
	base_ubp: number
	stars: number
	quantity: number
	image_url: string
}

export interface UniverseProgress {
	code: string
	title: string
	owned: number
	total: number
	percent: number
}

export interface BattlePassLevel {
	level: number
	free_dust: number
	free_tickets: number
	premium_dust: number
	premium_tickets: number
	premium_coins: number
	unlocked: boolean
	free_claimed: boolean
	premium_claimed: boolean
}

export interface BattlePassPage {
	entries: BattlePassLevel[]
	page: number
	total_pages: number
	current_level: number
	is_premium: boolean
	progress: number
	level_floor: number
	level_ceiling: number
}

export interface BattlePassClaimResult {
	dust: number
	tickets: number
	coins: number
}

export function fetchProfile(): Promise<Profile> {
	return apiFetch<Profile>('/me')
}

export function fetchUniverses(): Promise<Universe[]> {
	return apiFetch<Universe[]>('/universes')
}

export function fetchCollection(universeCode: string): Promise<CardStack[]> {
	return apiFetch<CardStack[]>(`/collection/${encodeURIComponent(universeCode)}`)
}

export function fetchEventCollection(): Promise<CardStack[]> {
	return apiFetch<CardStack[]>('/collection/events')
}

export function fetchProgress(): Promise<UniverseProgress[]> {
	return apiFetch<UniverseProgress[]>('/progress')
}

export function fetchBattlePassPage(page: number): Promise<BattlePassPage> {
	return apiFetch<BattlePassPage>(`/battle-pass?page=${page}`)
}

export function claimBattlePass(track: 'free' | 'premium'): Promise<BattlePassClaimResult> {
	return apiPost<BattlePassClaimResult>('/battle-pass/claim', { track })
}
