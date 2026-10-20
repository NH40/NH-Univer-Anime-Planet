import { apiFetch, apiPost } from './api'
import type { Msg } from './game'

// Админ-панель Mini App — обёртки над api/routers/admin.py.

export interface Point {
	day: string
	value: number
}

export interface Dashboard {
	users: number
	online: number
	new_24h: number
	payments_count: number
	payments_rub: number
	server: { cpu: number; ram: number; ram_used: number; ram_total: number; disk: number }
	economy: Record<'dust' | 'coins' | 'tickets' | 'rolls' | 'subscribers' | 'banned' | 'cards', number>
	charts: Record<'registrations' | 'active' | 'rolls' | 'revenue', Point[]>
	recent: { id: number; name: string; created_at: string | null; ubp: number }[]
	season: { version: string; started_at: string | null } | null
	tech_mode: boolean
	is_super: boolean
}

export interface PlayerRow {
	id: number
	name: string
	username: string | null
	ubp: number
	banned: boolean
	admin: boolean
	last_active: string | null
}

export interface PlayerDetail {
	id: number
	name: string | null
	username: string | null
	universe: string | null
	clan: string | null
	ubp_season: number
	ubp_total: number
	dust: number
	coins: number
	tickets: number
	rolls: number
	banned: boolean
	admin: boolean
	config_admin: boolean
	subscription_until: string | null
	battle_pass: boolean
	created_at: string | null
	last_active: string | null
	cards_total: number
	cards_unique: number
	donated_rub: number
	referrals: number
	transactions: { currency: string; amount: number; reason: string; at: string | null; by_admin: boolean }[]
}

export interface AdminCard {
	id: number
	external_id: string
	name: string
	base_ubp: number
	image_url: string
	special: boolean
}

export interface Promo {
	code: string
	active: boolean
	deactivated: boolean
	dust: number
	coins: number
	tickets: number
	max_uses: number | null
	used: number
}

export interface Campaign {
	code: string
	visited: number
	playing: number
	subs: number
	passes: number
	donated: number
	link: string
}

export interface PaymentRow {
	id: number
	user_id: number
	name: string
	rub: number
	coins: number | null
	kind: string | null
	status: string
	at: string | null
}

const A = '/admin'
const id = (userId: number) => `${A}/players/${userId}`

export const admin = {
	dashboard: () => apiFetch<Dashboard>(`${A}/dashboard`),
	techMode: (enabled: boolean) => apiPost<Msg>(`${A}/tech-mode`, { enabled }),
	players: (q: string, offset = 0) =>
		apiFetch<{ items: PlayerRow[]; has_more: boolean }>(
			`${A}/players?q=${encodeURIComponent(q)}&offset=${offset}`,
		),
	player: (userId: number) => apiFetch<PlayerDetail>(id(userId)),
	currency: (userId: number, currency: string, amount: number) =>
		apiPost<Msg>(`${id(userId)}/currency`, { currency, amount }),
	battlePass: (userId: number) => apiPost<Msg>(`${id(userId)}/battle-pass`, {}),
	subscription: (userId: number, days: number) => apiPost<Msg>(`${id(userId)}/subscription`, { days }),
	ban: (userId: number, value: boolean) => apiPost<Msg>(`${id(userId)}/ban`, { value }),
	setAdmin: (userId: number, value: boolean) => apiPost<Msg>(`${id(userId)}/admin`, { value }),
	card: (userId: number, card_id: number, stars: number, qty: number) =>
		apiPost<Msg>(`${id(userId)}/card`, { card_id, stars, qty }),
	universeCollection: (userId: number, universe: string) =>
		apiPost<Msg>(`${id(userId)}/universe-collection`, { universe }),
	message: (userId: number, text: string) => apiPost<Msg>(`${id(userId)}/message`, { text }),
	deletePlayer: (userId: number) => apiPost<Msg>(`${id(userId)}/delete`, {}),
	universes: () =>
		apiFetch<{ code: string; title: string; active: boolean; event: boolean }[]>(`${A}/universes`),
	cards: (universe: string, q: string) =>
		apiFetch<AdminCard[]>(`${A}/cards?universe=${encodeURIComponent(universe)}&q=${encodeURIComponent(q)}`),
	massGrant: (currency: string, amount: number) => apiPost<Msg>(`${A}/mass-grant`, { currency, amount }),
	broadcast: (text: string) => apiPost<Msg>(`${A}/broadcast`, { text }),
	promos: () => apiFetch<Promo[]>(`${A}/promos`),
	createPromo: (code: string, type: string, param: string, reward: Record<string, number>) =>
		apiPost<Msg>(`${A}/promos`, { code, type, param, reward }),
	promoAction: (code: string, action: 'activate' | 'deactivate' | 'delete') =>
		apiPost<Msg>(`${A}/promos/${encodeURIComponent(code)}/${action}`, {}),
	referrals: () => apiFetch<Campaign[]>(`${A}/referrals`),
	createReferral: (code: string) => apiPost<Msg>(`${A}/referrals`, { code }),
	seasonNew: (version: string) => apiPost<Msg>(`${A}/season/new`, { version }),
	seasonBump: (version: string) => apiPost<Msg>(`${A}/season/bump`, { version }),
	events: () => apiFetch<{ code: string; title: string; active: boolean }[]>(`${A}/events`),
	eventToggle: (code: string, enabled: boolean) =>
		apiPost<Msg>(`${A}/events/${encodeURIComponent(code)}`, { enabled }),
	payments: (offset = 0) =>
		apiFetch<{ items: PaymentRow[]; has_more: boolean }>(`${A}/payments?offset=${offset}`),
	admins: () => apiFetch<{ id: number; name: string; super: boolean }[]>(`${A}/admins`),
}
