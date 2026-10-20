import {
	Crown,
	Gem,
	Loader2,
	Shield,
	ShoppingBag,
	Sparkles,
	Star,
	Ticket,
	Trophy,
	User,
	Wrench,
} from 'lucide-react'
import type { ComponentType } from 'preact'
import { useEffect, useState } from 'preact/hooks'
import { Link } from 'wouter'
import {
	type CelestialInfo,
	type ClanInfo,
	type Profile,
	type ShopInfo,
	type TopInfo,
	buyTickets,
	fetchCelestial,
	fetchClan,
	fetchShop,
	fetchTop,
} from '../api'
import { Panel } from '../components/ui/Panel'
import { TierCard } from '../components/ui/TierCard'
import {
	ROUTE_ADMIN,
	ROUTE_BATTLE_PASS,
	ROUTE_CELESTIAL,
	ROUTE_CLAN,
	ROUTE_PROFILE,
	ROUTE_SHOP,
	ROUTE_TOP,
} from '../constants'
import { fmt, run, toast } from '../service/ui'

function Loading() {
	return (
		<div class='empty'>
			<Loader2 size={20} class='spin' /> Загрузка…
		</div>
	)
}

/** Загрузить данные страницы один раз (+ reload после действий). */
function useLoad<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
	const [data, setData] = useState<T | null>(null)
	const load = () =>
		fetcher()
			.then(setData)
			.catch((e) => toast(String(e.message ?? e), true))
	useEffect(() => {
		load()
	}, deps)
	return { data, load }
}

// ------------------------------------------------------------------ Ещё

type TileDef = { href: string; title: string; sub: string; Icon: ComponentType<{ size?: number }>; gold?: boolean }

export function MorePage({ profile }: { profile: Profile | null }) {
	const tiles: TileDef[] = [
		{ href: ROUTE_PROFILE, title: 'Профиль', sub: 'Прогресс по вселенным', Icon: User },
		{ href: ROUTE_BATTLE_PASS, title: 'Battle Pass', sub: 'Награды сезона', Icon: Ticket, gold: true },
		{ href: ROUTE_CELESTIAL, title: 'Небесные карты', sub: '10 уникальных карт', Icon: Sparkles, gold: true },
		{ href: ROUTE_TOP, title: 'Топ', sub: 'Рейтинг вселенной', Icon: Trophy },
		{ href: ROUTE_SHOP, title: 'Магазин', sub: 'Тикеты за пыль и коины', Icon: ShoppingBag },
		{ href: ROUTE_CLAN, title: 'Клан', sub: 'Состав и UBP', Icon: Shield },
	]
	if (profile?.is_admin) {
		tiles.push({ href: ROUTE_ADMIN, title: 'Админ-панель', sub: 'Управление ботом', Icon: Wrench, gold: true })
	}
	return (
		<>
			<div class='page-title'>Ещё</div>
			<div class='stat-grid' style={{ marginBottom: 14 }}>
				<div class='stat'>
					<div class='stat-value'>{fmt(profile?.ubp_season)}</div>
					<div class='stat-label'>UBP сезона</div>
				</div>
				<div class='stat'>
					<div class='stat-value'>{fmt(profile?.ubp_total)}</div>
					<div class='stat-label'>UBP всего</div>
				</div>
				<div class='stat'>
					<div class='stat-value'>{fmt(profile?.tickets)}</div>
					<div class='stat-label'>Тикеты</div>
				</div>
			</div>
			<div class='tiles'>
				{tiles.map((t) => (
					<Link key={t.href} href={t.href} class={t.gold ? 'tile tile-gold' : 'tile'}>
						<t.Icon size={22} />
						<span class='tile-title'>{t.title}</span>
						<span class='tile-sub'>{t.sub}</span>
					</Link>
				))}
			</div>
		</>
	)
}

// ------------------------------------------------------------------ Топ

export function TopPage() {
	const [universe, setUniverse] = useState<string | undefined>(undefined)
	const { data } = useLoad<TopInfo>(() => fetchTop(universe), [universe])
	if (!data) return <Loading />
	return (
		<>
			<div class='page-title'>Топ сезона</div>
			<div class='chips'>
				{data.universes.map((u) => (
					<button
						key={u.code}
						type='button'
						class={u.code === data.universe ? 'chip active' : 'chip'}
						onClick={() => setUniverse(u.code)}
					>
						{u.title}
					</button>
				))}
			</div>
			<Panel title='Рейтинг' gold>
				{data.rows.length === 0 && <div class='hint'>Пока пусто.</div>}
				{data.rows.map((r) => (
					<div class={r.is_me ? 'list-row me' : 'list-row'} key={r.user_id}>
						<span class='place'>{r.place <= 3 ? ['🥇', '🥈', '🥉'][r.place - 1] : r.place}</span>
						<div class='list-main'>
							<div class='list-title'>{r.name}</div>
						</div>
						<span style={{ fontWeight: 800 }}>
							<Star size={12} /> {fmt(r.ubp)}
						</span>
					</div>
				))}
				{data.me && <div class='hint' style={{ marginTop: 8 }}>Твоё место: {data.me}</div>}
			</Panel>
		</>
	)
}

// ------------------------------------------------------------------ Магазин

export function ShopPage() {
	const { data, load } = useLoad<ShopInfo>(fetchShop)
	const [busy, setBusy] = useState(false)
	if (!data) return <Loading />

	const buy = async (currency: 'dust' | 'coins', quantity: number) => {
		setBusy(true)
		await run(() => buyTickets(currency, quantity))
		await load()
		setBusy(false)
	}
	const block = (currency: 'dust' | 'coins', price: number, balance: number, title: string) => (
		<Panel title={title} gold={currency === 'coins'}>
			<div class='hint'>
				1 тикет = {fmt(price)} {currency === 'dust' ? '✨ пыли' : '💎 коинов'} · у тебя {fmt(balance)}
			</div>
			<div class='grid-btns' style={{ marginTop: 10, gridTemplateColumns: 'repeat(4, 1fr)' }}>
				{data.presets.map((q) => (
					<button
						key={q}
						type='button'
						class='btn btn-sm'
						disabled={busy || balance < q * price}
						onClick={() => buy(currency, q)}
					>
						🎫{q}
					</button>
				))}
			</div>
			{Math.floor(balance / price) > 0 && (
				<button
					type='button'
					class='btn btn-ghost btn-block'
					style={{ marginTop: 8 }}
					disabled={busy}
					onClick={() => buy(currency, Math.floor(balance / price))}
				>
					Максимум: 🎫{fmt(Math.floor(balance / price))}
				</button>
			)}
		</Panel>
	)
	return (
		<>
			<div class='page-title'>Магазин</div>
			{block('dust', data.dust_price, data.dust, 'За пыль')}
			{block('coins', data.coin_price, data.coins, 'За коины')}
			<div class='hint'>
				<Gem size={12} /> Коины, подписка и слоты хранилища — через бота (оплата Telegram).
			</div>
		</>
	)
}

// ------------------------------------------------------------------ Небесные

export function CelestialPage() {
	const { data } = useLoad<CelestialInfo>(fetchCelestial)
	const [code, setCode] = useState<string | null>(null)
	if (!data) return <Loading />
	const current = data.universes.find((u) => u.code === code) ?? data.universes[0]
	return (
		<>
			<div class='page-title'>Небесные карты</div>
			<div class='hint'>
				10 уникальных карт на весь бот. У каждой один владелец; выпала тебе, когда она занята, —
				бой за владение. Бои и решения — в боте.
			</div>
			<div class='chips' style={{ marginTop: 10 }}>
				{data.universes.map((u) => (
					<button
						key={u.code}
						type='button'
						class={u.code === current?.code ? 'chip active' : 'chip'}
						onClick={() => setCode(u.code)}
					>
						{u.title} · {u.cards.filter((c) => c.owner).length}/{u.cards.length}
					</button>
				))}
			</div>
			{!current && <div class='empty'>Небесных карт пока нет.</div>}
			{current?.cards.map((c) => (
				<div class='list-row' key={c.card_id} style={{ marginTop: 10, borderColor: 'rgba(245,185,66,.45)' }}>
					<div style={{ width: 70, flexShrink: 0 }}>
						<TierCard name={c.name} image={c.image_url} baseUbp={c.base_ubp} celestial />
					</div>
					<div class='list-main'>
						<div class='list-title display'>{c.name}</div>
						<div class='list-sub'>#{c.external_id}</div>
						<div style={{ fontSize: 12, fontWeight: 700, color: '#cfe0ff' }}>
							Владелец: {c.mine ? 'ты' : (c.owner ?? 'никто')}
						</div>
						<div
							style={{
								fontSize: 12,
								fontWeight: 700,
								color: c.battle ? 'var(--bad)' : c.mine ? 'var(--gold)' : c.owner ? 'var(--good)' : '#7fd4ff',
							}}
						>
							{c.battle
								? `Бой с ${c.challenger}: ${c.battle}`
								: c.challenger
									? `Претендент: ${c.challenger}`
									: c.mine
										? 'Твоя'
										: c.owner
											? 'Свободна от споров'
											: 'Свободна — может выпасть'}
						</div>
					</div>
				</div>
			))}
			<Panel title='Божественные' gold>
				<div class='hint'>
					«000» — за полную коллекцию вселенной · «1000» — все 10 небесных сразу · «999» — все 10
					когда-либо. Небесные и божественные не входят в 100% коллекции.
				</div>
			</Panel>
		</>
	)
}

// ------------------------------------------------------------------ Клан

const RANKS: Record<string, string> = {
	owner: '👑 Глава',
	deputy: '⭐ Зам',
	captain: '🛡 Капитан',
	member: 'Участник',
}

export function ClanPage() {
	const { data } = useLoad<ClanInfo>(fetchClan)
	if (!data) return <Loading />
	const clan = data.clan
	if (!clan) {
		return (
			<>
				<div class='page-title'>Клан</div>
				<Panel title='Нет клана'>
					<div class='hint'>Ты пока не в клане. Найти или создать клан можно в боте: /clan.</div>
				</Panel>
			</>
		)
	}
	return (
		<>
			<div class='page-title'>
				{clan.top10 && <Crown size={18} color='#f5c96a' />} {clan.name}
			</div>
			<div class='stat-grid'>
				<div class='stat'>
					<div class='stat-value'>{fmt(clan.ubp_season)}</div>
					<div class='stat-label'>UBP сезона</div>
				</div>
				<div class='stat'>
					<div class='stat-value'>{fmt(clan.ubp_total)}</div>
					<div class='stat-label'>UBP всего</div>
				</div>
				<div class='stat'>
					<div class='stat-value'>{clan.members}</div>
					<div class='stat-label'>Участников</div>
				</div>
			</div>
			<Panel title='Состав'>
				{clan.list.map((m, i) => (
					<div class={m.is_me ? 'list-row me' : 'list-row'} key={m.id}>
						<span class='place'>{i + 1}</span>
						<div class='list-main'>
							<div class='list-title'>{m.name}</div>
							<div class='list-sub'>{RANKS[m.rank] ?? m.rank}</div>
						</div>
						<span style={{ fontWeight: 800 }}>{fmt(m.ubp)}</span>
					</div>
				))}
			</Panel>
			<div class='hint'>Заявки, обменник и войны — в боте.</div>
		</>
	)
}
