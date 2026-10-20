import { apiFetch, apiPost } from './api'

// Игровые экраны Mini App (2026-10-20) — тонкие обёртки над api/routers/game.py. Вся логика
// (атомарные списания, локи, шансы) остаётся в сервисах бота, сюда приходят только итоги.

export interface Msg {
	message: string
}

export interface GameCard {
	card_id: number
	external_id: string
	name: string
	base_ubp: number
	universe: string
	is_celestial: boolean
	is_divine: boolean
	image_url: string
	image_full: string
	stars?: number
	is_new?: boolean
	divine?: GameCard[]
	celestial?: "owner" | "challenger" | null
	owner?: string | null
	challenger?: string | null
	battle?: string | null
	mine?: boolean
}

export interface UniverseRef {
	code: string
	title: string
}

export interface RollInfo {
	universe: string | null
	universes: UniverseRef[]
	tickets: number
	cap: number
	next_in: number | null
	chances: { tier: number; name: string; percent: number }[]
	mass_counts: number[]
	mass_max: number
}

export interface RollResult {
	cards: GameCard[]
	tickets: number
	requested: number
	ubp: number
	new: number
	tiers: { tier: number; name: string; count: number }[]
}

export interface QuestSlot {
	slot: number
	text: string
	progress: number
	target: number
	dust: number
	tickets: number
	claimed: boolean
	done: boolean
}

export interface QuestsInfo {
	slots: QuestSlot[]
	reroll_all: boolean
	rerolls_left: number
	bonus: {
		streak: number
		claimable: boolean
		next_in: number | null
		rewards: { day: number; dust: number; tickets: number }[]
	}
}

export interface TopInfo {
	universe: string | null
	universes: UniverseRef[]
	rows: { place: number; user_id: number; name: string; ubp: number; is_me: boolean }[]
	me: number | null
}

export interface ShopInfo {
	dust: number
	coins: number
	dust_price: number
	coin_price: number
	presets: number[]
}

export interface CelestialInfo {
	universes: { code: string; title: string; cards: GameCard[] }[]
}

export interface ClanInfo {
	clan: null | {
		name: string
		ubp_season: number
		ubp_total: number
		members: number
		top10: boolean
		list: { id: number; name: string; ubp: number; rank: string; is_me: boolean }[]
	}
}

export const fetchRollInfo = () => apiFetch<RollInfo>('/roll')
export const doRoll = (count: string) => apiPost<RollResult>('/roll', { count })
export const selectUniverse = (code: string) => apiPost<Msg>('/universe', { code })

export const mergeCard = (card_id: number, stars: number, target_stars: number, single: boolean) =>
	apiPost<Msg>('/merge', { card_id, stars, target_stars, single })
export const mergeAll = (universe: string) => apiPost<Msg>('/merge/all', { universe })
export type DustMode = 'amount' | 'duplicates' | 'all' | 'owned_duplicates' | 'owned_all'
export const distill = (mode: DustMode, card_id?: number, stars?: number, amount?: number) =>
	apiPost<Msg>('/dust', { mode, card_id, stars, amount })

export const fetchQuests = () => apiFetch<QuestsInfo>('/quests')
export const questAction = (action: string, slot?: number) =>
	apiPost<Msg>(`/quests/${action}`, { slot })

export const fetchTop = (universe?: string) =>
	apiFetch<TopInfo>(universe ? `/top?universe=${encodeURIComponent(universe)}` : '/top')
export const fetchShop = () => apiFetch<ShopInfo>('/shop')
export const buyTickets = (currency: 'dust' | 'coins', quantity: number) =>
	apiPost<Msg>('/shop/tickets', { currency, quantity })
export const fetchCelestial = () => apiFetch<CelestialInfo>('/celestial')
export const fetchClan = () => apiFetch<ClanInfo>('/clan')
