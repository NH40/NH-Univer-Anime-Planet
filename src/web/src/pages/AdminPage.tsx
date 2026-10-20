import { ArrowLeft, Loader2, Search } from 'lucide-react'
import { useEffect, useState } from 'preact/hooks'
import {
	type AdminCard,
	type Campaign,
	type Dashboard,
	type PaymentRow,
	type PlayerDetail,
	type PlayerRow,
	type Point,
	type Promo,
	admin,
} from '../api'
import { Panel } from '../components/ui/Panel'
import { fmt, run, toast } from '../service/ui'

type Section = 'dash' | 'players' | 'promo' | 'mass' | 'season' | 'payments' | 'refs' | 'admins'
const SECTIONS: [Section, string][] = [
	['dash', 'Дашборд'],
	['players', 'Игроки'],
	['promo', 'Промокоды'],
	['mass', 'Рассылка'],
	['season', 'Сезон и ивенты'],
	['payments', 'Платежи'],
	['refs', 'Рефералы'],
	['admins', 'Админы'],
]

const dt = (iso: string | null) =>
	iso ? new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'

function Loading() {
	return (
		<div class='empty'>
			<Loader2 size={20} class='spin' /> Загрузка…
		</div>
	)
}

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

/** Кнопка с подтверждением вторым нажатием (для необратимых действий). */
function ConfirmButton({ label, onConfirm, cls = 'btn btn-danger btn-sm' }: { label: string; onConfirm: () => void; cls?: string }) {
	const [armed, setArmed] = useState(false)
	useEffect(() => {
		if (!armed) return
		const t = setTimeout(() => setArmed(false), 4000)
		return () => clearTimeout(t)
	}, [armed])
	return (
		<button type='button' class={cls} onClick={() => (armed ? (setArmed(false), onConfirm()) : setArmed(true))}>
			{armed ? 'Точно? Нажми ещё раз' : label}
		</button>
	)
}

export function AdminPage({ isSuper }: { isSuper: boolean }) {
	const [section, setSection] = useState<Section>('dash')
	const list = SECTIONS.filter(([s]) => s !== 'admins' || isSuper)
	return (
		<>
			<div class='page-title'>Админ-панель</div>
			<div class='chips'>
				{list.map(([s, title]) => (
					<button key={s} type='button' class={s === section ? 'chip active' : 'chip'} onClick={() => setSection(s)}>
						{title}
					</button>
				))}
			</div>
			{section === 'dash' && <DashboardSection />}
			{section === 'players' && <PlayersSection isSuper={isSuper} />}
			{section === 'promo' && <PromoSection />}
			{section === 'mass' && <MassSection />}
			{section === 'season' && <SeasonSection isSuper={isSuper} />}
			{section === 'payments' && <PaymentsSection />}
			{section === 'refs' && <RefsSection />}
			{section === 'admins' && <AdminsSection />}
		</>
	)
}

// ------------------------------------------------------------------ дашборд

function Chart({ title, points, suffix = '' }: { title: string; points: Point[]; suffix?: string }) {
	const max = Math.max(1, ...points.map((p) => p.value))
	const total = points.reduce((a, p) => a + p.value, 0)
	return (
		<Panel title={title}>
			<div class='row-between'>
				<span class='hint'>14 дней</span>
				<span style={{ fontWeight: 800 }}>
					Σ {fmt(total)}
					{suffix}
				</span>
			</div>
			<div class='bar-chart'>
				{points.map((p) => (
					<div
						key={p.day}
						style={{ height: `${(p.value / max) * 100}%` }}
						data-tip={`${p.day.slice(5)}: ${fmt(p.value)}${suffix}`}
					/>
				))}
			</div>
			<div class='row-between hint' style={{ marginTop: 4 }}>
				<span>{points[0]?.day.slice(5)}</span>
				<span>сегодня: {fmt(points[points.length - 1]?.value)}</span>
			</div>
		</Panel>
	)
}

function DashboardSection() {
	const { data, load } = useLoad<Dashboard>(admin.dashboard)
	if (!data) return <Loading />
	const stat = (value: string | number, label: string) => (
		<div class='stat'>
			<div class='stat-value'>{typeof value === 'number' ? fmt(value) : value}</div>
			<div class='stat-label'>{label}</div>
		</div>
	)
	return (
		<>
			<Panel title='Игроки'>
				<div class='stat-grid'>
					{stat(data.users, 'Всего')}
					{stat(data.online, 'Активны 24ч')}
					{stat(data.new_24h, 'Новых 24ч')}
					{stat(data.economy.subscribers, 'Подписчиков')}
					{stat(data.economy.banned, 'В бане')}
					{stat(data.economy.rolls, 'Круток')}
				</div>
			</Panel>
			<Panel title='Экономика' gold>
				<div class='stat-grid'>
					{stat(data.economy.dust, '✨ Пыль')}
					{stat(data.economy.coins, '💎 Коины')}
					{stat(data.economy.tickets, '🎫 Тикеты')}
					{stat(data.economy.cards, 'Карт у игроков')}
					{stat(data.payments_count, 'Платежей')}
					{stat(`${fmt(data.payments_rub)}₽`, 'Доход')}
				</div>
			</Panel>
			<Chart title='Регистрации' points={data.charts.registrations} />
			<Chart title='Активность' points={data.charts.active} />
			<Chart title='Крутки' points={data.charts.rolls} />
			<Chart title='Доход' points={data.charts.revenue} suffix='₽' />
			<Panel title='Сервер'>
				<div class='kv'><span>CPU</span><span>{data.server.cpu}%</span></div>
				<div class='kv'><span>RAM</span><span>{data.server.ram}% ({data.server.ram_used}/{data.server.ram_total} МБ)</span></div>
				<div class='kv'><span>Диск</span><span>{data.server.disk}%</span></div>
				<div class='kv'><span>Сезон</span><span>{data.season ? data.season.version : 'нет'}</span></div>
				<div class='row-between' style={{ marginTop: 10 }}>
					<span style={{ fontWeight: 800 }}>Техрежим: {data.tech_mode ? '🔧 включён' : 'выключен'}</span>
					<button
						type='button'
						class={data.tech_mode ? 'btn btn-sm' : 'btn btn-sm btn-danger'}
						onClick={async () => {
							await run(() => admin.techMode(!data.tech_mode))
							load()
						}}
					>
						{data.tech_mode ? 'Выключить' : 'Включить'}
					</button>
				</div>
			</Panel>
			<Panel title='Новые игроки'>
				{data.recent.map((p) => (
					<div class='list-row' key={p.id}>
						<div class='list-main'>
							<div class='list-title'>{p.name}</div>
							<div class='list-sub'>id {p.id} · {dt(p.created_at)}</div>
						</div>
						<span style={{ fontWeight: 800 }}>{fmt(p.ubp)}</span>
					</div>
				))}
			</Panel>
		</>
	)
}

// ------------------------------------------------------------------ игроки

function PlayersSection({ isSuper }: { isSuper: boolean }) {
	const [q, setQ] = useState('')
	const [query, setQuery] = useState('')
	const [items, setItems] = useState<PlayerRow[]>([])
	const [hasMore, setHasMore] = useState(false)
	const [openId, setOpenId] = useState<number | null>(null)

	const search = (offset = 0) =>
		admin
			.players(query, offset)
			.then((r) => {
				setItems((cur) => (offset ? [...cur, ...r.items] : r.items))
				setHasMore(r.has_more)
			})
			.catch((e) => toast(String(e.message ?? e), true))
	useEffect(() => {
		search()
	}, [query])

	if (openId !== null) return <PlayerCard userId={openId} isSuper={isSuper} onBack={() => setOpenId(null)} />
	return (
		<>
			<form
				class='row'
				style={{ marginTop: 12, flexWrap: 'nowrap' }}
				onSubmit={(e) => {
					e.preventDefault()
					setQuery(q)
				}}
			>
				<input class='input' placeholder='id, @username или имя' value={q} onInput={(e) => setQ((e.target as HTMLInputElement).value)} />
				<button type='submit' class='btn'>
					<Search size={16} />
				</button>
			</form>
			<div style={{ marginTop: 12 }}>
				{items.map((p) => (
					<button type='button' class='list-row' key={p.id} onClick={() => setOpenId(p.id)}>
						<div class='list-main'>
							<div class='list-title'>
								{p.banned ? '⛔ ' : ''}
								{p.admin ? '👑 ' : ''}
								{p.name}
							</div>
							<div class='list-sub'>
								id {p.id}
								{p.username ? ` · @${p.username}` : ''} · {dt(p.last_active)}
							</div>
						</div>
						<span style={{ fontWeight: 800 }}>{fmt(p.ubp)}</span>
					</button>
				))}
				{items.length === 0 && <div class='empty'>Никого не найдено.</div>}
				{hasMore && (
					<button type='button' class='btn btn-ghost btn-block' style={{ marginTop: 8 }} onClick={() => search(items.length)}>
						Показать ещё
					</button>
				)}
			</div>
		</>
	)
}

function PlayerCard({ userId, isSuper, onBack }: { userId: number; isSuper: boolean; onBack: () => void }) {
	const { data: p, load } = useLoad<PlayerDetail>(() => admin.player(userId), [userId])
	const [cur, setCur] = useState('dust')
	const [amount, setAmount] = useState('')
	const [days, setDays] = useState('30')
	const [msg, setMsg] = useState('')
	const [giveCard, setGiveCard] = useState(false)

	const act = async (fn: () => Promise<unknown>) => {
		if (await run(fn)) load()
	}
	if (!p) return <Loading />
	if (giveCard) return <GiveCard userId={userId} onBack={() => (setGiveCard(false), load())} />

	return (
		<>
			<button type='button' class='btn btn-ghost btn-sm' style={{ marginTop: 12 }} onClick={onBack}>
				<ArrowLeft size={16} /> К списку
			</button>
			<Panel title={p.name ?? `id ${p.id}`} gold={p.admin}>
				<div class='kv'><span>ID</span><span>{p.id}{p.username ? ` · @${p.username}` : ''}</span></div>
				<div class='kv'><span>Статус</span><span>{p.banned ? '⛔ Забанен' : 'Активен'}{p.admin ? ' · 👑 админ' : ''}</span></div>
				<div class='kv'><span>Клан</span><span>{p.clan ?? '—'}</span></div>
				<div class='kv'><span>Вселенная</span><span>{p.universe ?? '—'}</span></div>
				<div class='kv'><span>UBP сезон / всего</span><span>{fmt(p.ubp_season)} / {fmt(p.ubp_total)}</span></div>
				<div class='kv'><span>✨ / 💎 / 🎫</span><span>{fmt(p.dust)} / {fmt(p.coins)} / {fmt(p.tickets)}</span></div>
				<div class='kv'><span>Круток</span><span>{fmt(p.rolls)}</span></div>
				<div class='kv'><span>Карт (уник.)</span><span>{fmt(p.cards_total)} ({fmt(p.cards_unique)})</span></div>
				<div class='kv'><span>Донат</span><span>{fmt(p.donated_rub)}₽</span></div>
				<div class='kv'><span>Рефералов</span><span>{p.referrals}</span></div>
				<div class='kv'><span>Подписка до</span><span>{dt(p.subscription_until)}</span></div>
				<div class='kv'><span>Battle Pass</span><span>{p.battle_pass ? 'есть' : 'нет'}</span></div>
				<div class='kv'><span>Регистрация</span><span>{dt(p.created_at)}</span></div>
				<div class='kv'><span>Был в сети</span><span>{dt(p.last_active)}</span></div>
			</Panel>

			<Panel title='Валюта'>
				<div class='hint'>Отрицательное число — списать (баланс не уйдёт ниже 0).</div>
				<div class='row' style={{ marginTop: 8, flexWrap: 'nowrap' }}>
					<select class='input' style={{ width: 120 }} value={cur} onChange={(e) => setCur((e.target as HTMLSelectElement).value)}>
						<option value='dust'>✨ Пыль</option>
						<option value='coins'>💎 Коины</option>
						<option value='tickets'>🎫 Тикеты</option>
					</select>
					<input class='input' type='number' placeholder='±количество' value={amount} onInput={(e) => setAmount((e.target as HTMLInputElement).value)} />
					<button type='button' class='btn' disabled={!Number(amount)} onClick={() => act(() => admin.currency(userId, cur, Number(amount)))}>
						OK
					</button>
				</div>
			</Panel>

			<Panel title='Выдачи'>
				<div class='col'>
					<button type='button' class='btn' onClick={() => setGiveCard(true)}>🃏 Карты</button>
					<button type='button' class='btn' disabled={p.battle_pass} onClick={() => act(() => admin.battlePass(userId))}>
						🎫 Выдать Battle Pass
					</button>
					<div class='row' style={{ flexWrap: 'nowrap' }}>
						<input class='input' type='number' value={days} onInput={(e) => setDays((e.target as HTMLInputElement).value)} />
						<button type='button' class='btn' style={{ whiteSpace: 'nowrap' }} disabled={!Number(days)} onClick={() => act(() => admin.subscription(userId, Number(days)))}>
							⭐ Подписка (дн.)
						</button>
					</div>
				</div>
			</Panel>

			<Panel title='Сообщение игроку'>
				<textarea class='input' placeholder='Текст (HTML можно)' value={msg} onInput={(e) => setMsg((e.target as HTMLTextAreaElement).value)} />
				<button
					type='button'
					class='btn btn-block'
					style={{ marginTop: 8 }}
					disabled={!msg.trim()}
					onClick={async () => {
						if (await run(() => admin.message(userId, msg))) setMsg('')
					}}
				>
					Отправить в бота
				</button>
			</Panel>

			<Panel title='Управление'>
				<div class='row'>
					{!p.config_admin && (
						<button type='button' class={p.banned ? 'btn btn-sm' : 'btn btn-sm btn-danger'} onClick={() => act(() => admin.ban(userId, !p.banned))}>
							{p.banned ? 'Разбанить' : 'Забанить'}
						</button>
					)}
					{isSuper && !p.config_admin && (
						<button type='button' class='btn btn-sm btn-gold' onClick={() => act(() => admin.setAdmin(userId, !p.admin))}>
							{p.admin ? 'Снять админа' : 'Сделать админом'}
						</button>
					)}
					{!p.config_admin && (
						<ConfirmButton
							label='Удалить аккаунт'
							onConfirm={async () => {
								if (await run(() => admin.deletePlayer(userId))) onBack()
							}}
						/>
					)}
				</div>
			</Panel>

			<Panel title='Последние транзакции'>
				{p.transactions.length === 0 && <div class='hint'>Пусто.</div>}
				{p.transactions.map((t, i) => (
					<div class='kv' key={i}>
						<span>
							{dt(t.at)} · {t.reason}
							{t.by_admin ? ' 👑' : ''}
						</span>
						<span style={{ color: t.amount < 0 ? 'var(--bad)' : 'var(--good)' }}>
							{t.amount > 0 ? '+' : ''}
							{fmt(t.amount)} {t.currency}
						</span>
					</div>
				))}
			</Panel>
		</>
	)
}

function GiveCard({ userId, onBack }: { userId: number; onBack: () => void }) {
	const { data: universes } = useLoad(admin.universes)
	const [universe, setUniverse] = useState('')
	const [q, setQ] = useState('')
	const [cards, setCards] = useState<AdminCard[]>([])
	const [picked, setPicked] = useState<AdminCard | null>(null)
	const [stars, setStars] = useState('1')
	const [qty, setQty] = useState('1')

	useEffect(() => {
		if (!universe) return
		const t = setTimeout(
			() =>
				admin
					.cards(universe, q)
					.then(setCards)
					.catch((e) => toast(String(e.message ?? e), true)),
			250,
		)
		return () => clearTimeout(t)
	}, [universe, q])

	return (
		<>
			<button type='button' class='btn btn-ghost btn-sm' style={{ marginTop: 12 }} onClick={onBack}>
				<ArrowLeft size={16} /> К игроку
			</button>
			<Panel title='Вселенная'>
				<div class='chips'>
					{universes?.map((u) => (
						<button key={u.code} type='button' class={u.code === universe ? 'chip active' : 'chip'} onClick={() => (setUniverse(u.code), setPicked(null))}>
							{u.title}
							{u.event ? ' 🎉' : ''}
						</button>
					))}
				</div>
				{universe && (
					<ConfirmButton
						cls='btn btn-sm btn-gold'
						label='Выдать всю вселенную (по 1★)'
						onConfirm={() => run(() => admin.universeCollection(userId, universe))}
					/>
				)}
			</Panel>
			{universe && (
				<Panel title='Карта'>
					<input class='input' placeholder='Поиск по имени или id' value={q} onInput={(e) => setQ((e.target as HTMLInputElement).value)} />
					<div style={{ marginTop: 8, maxHeight: 320, overflowY: 'auto' }}>
						{cards.map((c) => (
							<button type='button' key={c.id} class={picked?.id === c.id ? 'list-row me' : 'list-row'} onClick={() => setPicked(c)}>
								<img src={c.image_url} alt='' style={{ width: 32, height: 48, objectFit: 'cover', borderRadius: 6 }} loading='lazy' />
								<div class='list-main'>
									<div class='list-title'>{c.name}</div>
									<div class='list-sub'>#{c.external_id} · {fmt(c.base_ubp)} UBP{c.special ? ' · особая' : ''}</div>
								</div>
							</button>
						))}
					</div>
				</Panel>
			)}
			{picked && (
				<Panel title={picked.name} gold>
					<div class='hint'>Отрицательное количество — забрать.</div>
					<div class='row' style={{ marginTop: 8, flexWrap: 'nowrap' }}>
						<select class='input' style={{ width: 90 }} value={stars} onChange={(e) => setStars((e.target as HTMLSelectElement).value)}>
							{[1, 2, 3, 4, 5].map((s) => (
								<option key={s} value={s}>★{s}</option>
							))}
						</select>
						<input class='input' type='number' value={qty} onInput={(e) => setQty((e.target as HTMLInputElement).value)} />
						<button type='button' class='btn' disabled={!Number(qty)} onClick={() => run(() => admin.card(userId, picked.id, Number(stars), Number(qty)))}>
							OK
						</button>
					</div>
				</Panel>
			)}
		</>
	)
}

// ------------------------------------------------------------------ промокоды

function PromoSection() {
	const { data, load } = useLoad<Promo[]>(admin.promos)
	const [code, setCode] = useState('')
	const [type, setType] = useState('uses')
	const [param, setParam] = useState('100')
	const [reward, setReward] = useState({ dust: '', coins: '', tickets: '' })

	const create = async () => {
		const r: Record<string, number> = {}
		for (const [k, v] of Object.entries(reward)) if (Number(v)) r[k] = Number(v)
		if (await run(() => admin.createPromo(code, type, param, r))) {
			setCode('')
			load()
		}
	}
	const act = async (c: string, a: 'activate' | 'deactivate' | 'delete') => {
		await run(() => admin.promoAction(c, a))
		load()
	}
	return (
		<>
			<Panel title='Новый промокод' gold>
				<div class='col'>
					<input class='input' placeholder='КОД' value={code} onInput={(e) => setCode((e.target as HTMLInputElement).value)} />
					<div class='row' style={{ flexWrap: 'nowrap' }}>
						<select class='input' style={{ width: 150 }} value={type} onChange={(e) => setType((e.target as HTMLSelectElement).value)}>
							<option value='uses'>По активациям</option>
							<option value='time'>По времени (ч)</option>
							<option value='users'>Для username</option>
						</select>
						<input
							class='input'
							placeholder={type === 'users' ? 'nick1, nick2' : type === 'time' ? 'часов' : 'активаций'}
							value={param}
							onInput={(e) => setParam((e.target as HTMLInputElement).value)}
						/>
					</div>
					<div class='row' style={{ flexWrap: 'nowrap' }}>
						{(['dust', 'coins', 'tickets'] as const).map((k) => (
							<input
								key={k}
								class='input'
								type='number'
								placeholder={{ dust: '✨ пыль', coins: '💎 коины', tickets: '🎫 тикеты' }[k]}
								value={reward[k]}
								onInput={(e) => setReward({ ...reward, [k]: (e.target as HTMLInputElement).value })}
							/>
						))}
					</div>
					<div class='hint'>Отрицательная награда — штраф (баланс не уйдёт ниже 0).</div>
					<button type='button' class='btn btn-gold' disabled={!code.trim()} onClick={create}>
						Создать
					</button>
				</div>
			</Panel>
			<Panel title='Промокоды'>
				{!data && <Loading />}
				{data?.length === 0 && <div class='hint'>Пока нет.</div>}
				{data?.map((p) => (
					<div class='list-row' key={p.code} style={{ flexWrap: 'wrap' }}>
						<div class='list-main'>
							<div class='list-title'>
								{p.active ? '✅' : '❌'} {p.code}
							</div>
							<div class='list-sub'>
								{[p.dust && `✨${p.dust}`, p.coins && `💎${p.coins}`, p.tickets && `🎫${p.tickets}`].filter(Boolean).join(' ')} ·{' '}
								{p.used}
								{p.max_uses ? `/${p.max_uses}` : ''} акт.
							</div>
						</div>
						<button type='button' class='btn btn-sm btn-ghost' onClick={() => act(p.code, p.deactivated ? 'activate' : 'deactivate')}>
							{p.deactivated ? 'Вкл' : 'Выкл'}
						</button>
						<ConfirmButton label='Удалить' onConfirm={() => act(p.code, 'delete')} />
					</div>
				))}
			</Panel>
		</>
	)
}

// ------------------------------------------------------------------ рассылка и массовые выдачи

function MassSection() {
	const [text, setText] = useState('')
	const [cur, setCur] = useState('tickets')
	const [amount, setAmount] = useState('')
	return (
		<>
			<Panel title='Рассылка'>
				<textarea class='input' placeholder='Текст для всех игроков (HTML можно)' value={text} onInput={(e) => setText((e.target as HTMLTextAreaElement).value)} />
				<div class='hint' style={{ margin: '6px 0' }}>Идёт в фоне батчами; итог придёт тебе в бота.</div>
				{text.trim() && (
					<ConfirmButton
						cls='btn btn-block'
						label='Отправить всем'
						onConfirm={async () => {
							if (await run(() => admin.broadcast(text))) setText('')
						}}
					/>
				)}
			</Panel>
			<Panel title='Выдать всем' gold>
				<div class='row' style={{ flexWrap: 'nowrap' }}>
					<select class='input' style={{ width: 120 }} value={cur} onChange={(e) => setCur((e.target as HTMLSelectElement).value)}>
						<option value='tickets'>🎫 Тикеты</option>
						<option value='dust'>✨ Пыль</option>
						<option value='coins'>💎 Коины</option>
					</select>
					<input class='input' type='number' placeholder='количество' value={amount} onInput={(e) => setAmount((e.target as HTMLInputElement).value)} />
				</div>
				{Number(amount) > 0 && (
					<div style={{ marginTop: 8 }}>
						<ConfirmButton cls='btn btn-gold btn-block' label={`Выдать ${amount} всем игрокам`} onConfirm={() => run(() => admin.massGrant(cur, Number(amount)))} />
					</div>
				)}
			</Panel>
		</>
	)
}

// ------------------------------------------------------------------ сезон и ивенты

function SeasonSection({ isSuper }: { isSuper: boolean }) {
	const { data: dash, load: loadDash } = useLoad<Dashboard>(admin.dashboard)
	const { data: events, load } = useLoad(admin.events)
	const [version, setVersion] = useState('')
	return (
		<>
			<Panel title='Сезон'>
				<div class='kv'><span>Текущий</span><span>{dash?.season ? dash.season.version : 'нет'}</span></div>
				<div class='kv'><span>Начат</span><span>{dt(dash?.season?.started_at ?? null)}</span></div>
				<input class='input' style={{ marginTop: 10 }} placeholder='Версия, например 1.3.0' value={version} onInput={(e) => setVersion((e.target as HTMLInputElement).value)} />
				<div class='row' style={{ marginTop: 8 }}>
					<button
						type='button'
						class='btn btn-sm'
						disabled={!version.trim() || !dash?.season}
						onClick={async () => {
							await run(() => admin.seasonBump(version))
							loadDash()
						}}
					>
						Сменить версию
					</button>
					{isSuper && version.trim() && (
						<ConfirmButton
							label='Начать новый сезон'
							onConfirm={async () => {
								await run(() => admin.seasonNew(version))
								loadDash()
							}}
						/>
					)}
				</div>
				<div class='hint' style={{ marginTop: 6 }}>
					Новый сезон: UBP сезона → в «всего», награды топ-10 по каждой вселенной, пуш всем.
				</div>
			</Panel>
			<Panel title='Ивенты' gold>
				{events?.map((e) => (
					<div class='list-row' key={e.code}>
						<div class='list-main'>
							<div class='list-title'>
								{e.active ? '🟢' : '⚪'} {e.title}
							</div>
						</div>
						<button
							type='button'
							class={e.active ? 'btn btn-sm btn-ghost' : 'btn btn-sm btn-gold'}
							onClick={async () => {
								await run(() => admin.eventToggle(e.code, !e.active))
								load()
							}}
						>
							{e.active ? 'Выключить' : 'Включить'}
						</button>
					</div>
				))}
				<div class='hint' style={{ marginTop: 6 }}>Активен максимум один; при включении — анонс всем игрокам.</div>
			</Panel>
		</>
	)
}

// ------------------------------------------------------------------ платежи / рефералы / админы

function PaymentsSection() {
	const [items, setItems] = useState<PaymentRow[]>([])
	const [hasMore, setHasMore] = useState(false)
	const load = (offset = 0) =>
		admin
			.payments(offset)
			.then((r) => {
				setItems((cur) => (offset ? [...cur, ...r.items] : r.items))
				setHasMore(r.has_more)
			})
			.catch((e) => toast(String(e.message ?? e), true))
	useEffect(() => {
		load()
	}, [])
	return (
		<Panel title='Платежи'>
			{items.length === 0 && <div class='hint'>Пока нет.</div>}
			{items.map((p) => (
				<div class='list-row' key={p.id}>
					<div class='list-main'>
						<div class='list-title'>{p.name}</div>
						<div class='list-sub'>
							{dt(p.at)} · {p.kind ?? 'donate'} · {p.status}
						</div>
					</div>
					<span style={{ fontWeight: 800 }}>{fmt(p.rub)}₽</span>
				</div>
			))}
			{hasMore && (
				<button type='button' class='btn btn-ghost btn-block' style={{ marginTop: 8 }} onClick={() => load(items.length)}>
					Ещё
				</button>
			)}
		</Panel>
	)
}

function RefsSection() {
	const { data, load } = useLoad<Campaign[]>(admin.referrals)
	const [code, setCode] = useState('')
	return (
		<>
			<Panel title='Новая кампания'>
				<div class='row' style={{ flexWrap: 'nowrap' }}>
					<input class='input' placeholder='код (латиница)' value={code} onInput={(e) => setCode((e.target as HTMLInputElement).value)} />
					<button
						type='button'
						class='btn'
						disabled={!code.trim()}
						onClick={async () => {
							if (await run(() => admin.createReferral(code))) {
								setCode('')
								load()
							}
						}}
					>
						Создать
					</button>
				</div>
			</Panel>
			<Panel title='Кампании' gold>
				{!data && <Loading />}
				{data?.length === 0 && <div class='hint'>Пока нет.</div>}
				{data?.map((c) => (
					<div key={c.code} style={{ marginBottom: 12 }}>
						<div class='row-between'>
							<span style={{ fontWeight: 800 }}>{c.code}</span>
							<button
								type='button'
								class='btn btn-sm btn-ghost'
								onClick={() => navigator.clipboard?.writeText(c.link).then(() => toast('Ссылка скопирована'))}
							>
								Копировать
							</button>
						</div>
						<div class='list-sub'>
							Перешло {c.visited} · играет {c.playing} · подписок {c.subs} · пассов {c.passes} · донат {fmt(c.donated)}₽
						</div>
					</div>
				))}
			</Panel>
		</>
	)
}

function AdminsSection() {
	const { data } = useLoad(admin.admins)
	return (
		<Panel title='Администраторы' gold>
			{data?.map((a) => (
				<div class='list-row' key={a.id}>
					<div class='list-main'>
						<div class='list-title'>{a.name}</div>
						<div class='list-sub'>id {a.id} · {a.super ? 'супер-админ (.env)' : 'админ'}</div>
					</div>
				</div>
			))}
			<div class='hint' style={{ marginTop: 8 }}>Выдать/снять права — в карточке игрока (раздел «Игроки»).</div>
		</Panel>
	)
}
