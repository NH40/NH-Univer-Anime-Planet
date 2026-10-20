import { Dices, Loader2, X } from 'lucide-react'
import { useEffect, useState } from 'preact/hooks'
import { type RollInfo, type RollResult, doRoll, fetchRollInfo, selectUniverse } from '../api'
import { Panel } from '../components/ui/Panel'
import { TierCard, tierColor } from '../components/ui/TierCard'
import { TIER_INFO } from '../config'
import { countdown, fmt, requestRefresh, run, toast } from '../service/ui'

export function RollPage() {
	const [info, setInfo] = useState<RollInfo | null>(null)
	const [busy, setBusy] = useState(false)
	const [result, setResult] = useState<RollResult | null>(null)
	const [lastCount, setLastCount] = useState('1')

	const load = () => fetchRollInfo().then(setInfo).catch((e) => toast(String(e.message ?? e), true))
	useEffect(() => {
		load()
	}, [])

	const roll = async (count: string) => {
		if (busy) return
		setBusy(true)
		setLastCount(count)
		try {
			const res = await doRoll(count)
			setResult(res)
			setInfo((cur) => (cur ? { ...cur, tickets: res.tickets } : cur))
			requestRefresh()
		} catch (e) {
			toast(e instanceof Error ? e.message : String(e), true)
		} finally {
			setBusy(false)
		}
	}

	const pickUniverse = async (code: string) => {
		if (await run(() => selectUniverse(code))) load()
	}

	if (!info) {
		return (
			<div class='empty'>
				<Loader2 size={20} class='spin' /> Загрузка…
			</div>
		)
	}

	const allCount = Math.min(info.tickets, info.mass_max)
	return (
		<>
			<div class='page-title'>Открытие карт</div>
			<div class='chips'>
				{info.universes.map((u) => (
					<button
						key={u.code}
						type='button'
						class={u.code === info.universe ? 'chip active' : 'chip'}
						onClick={() => pickUniverse(u.code)}
					>
						{u.title}
					</button>
				))}
			</div>

			<Panel title='Тикеты'>
				<div class='roll-hero'>
					<div class='roll-tickets'>
						{fmt(info.tickets)}
						<span class='hint'> / {info.cap}</span>
					</div>
					{info.next_in ? (
						<div class='hint'>Следующий тикет через {countdown(info.next_in)}</div>
					) : (
						<div class='hint'>Реген на максимуме</div>
					)}
				</div>
				<button
					type='button'
					class='btn btn-big btn-gold'
					disabled={busy || info.tickets < 1 || !info.universe}
					onClick={() => roll('1')}
				>
					{busy ? <Loader2 size={18} class='spin' /> : <Dices size={20} />} Крутить
				</button>
				<div class='grid-btns' style={{ marginTop: 8 }}>
					{info.mass_counts.map((n) => (
						<button
							key={n}
							type='button'
							class='btn'
							disabled={busy || info.tickets < n}
							onClick={() => roll(String(n))}
						>
							×{n}
						</button>
					))}
					<button
						type='button'
						class='btn'
						disabled={busy || info.tickets < 2}
						onClick={() => roll('all')}
					>
						Все ({allCount})
					</button>
				</div>
				{!info.universe && <div class='hint'>Сначала выбери вселенную выше.</div>}
			</Panel>

			<Panel title='Шансы'>
				{info.chances.map((c) => (
					<div class='chance-row' key={c.tier}>
						<span style={{ color: TIER_INFO[c.tier]?.color }}>● {c.name}</span>
						<span>{c.percent}%</span>
					</div>
				))}
				<div class='hint' style={{ marginTop: 6 }}>
					Небесные и ивент-карты выпадают отдельным редким шансом поверх обычного.
				</div>
			</Panel>

			{result && (
				<RollResultOverlay
					result={result}
					busy={busy}
					canRepeat={result.tickets >= (lastCount === 'all' ? 2 : Number(lastCount))}
					onRepeat={() => roll(lastCount)}
					onClose={() => setResult(null)}
				/>
			)}
		</>
	)
}

function RollResultOverlay({
	result,
	busy,
	canRepeat,
	onRepeat,
	onClose,
}: {
	result: RollResult
	busy: boolean
	canRepeat: boolean
	onRepeat: () => void
	onClose: () => void
}) {
	const single = result.cards.length === 1 ? result.cards[0] : null
	const specials = result.cards.filter((c) => c.celestial || (c.divine && c.divine.length))
	return (
		<div class='overlay'>
			<div class='overlay-inner'>
				<div class='row-between'>
					<div class='page-title'>
						{single ? 'Выпала карта' : `Открыто карт: ${result.cards.length}`}
					</div>
					<button type='button' class='btn btn-ghost btn-sm' onClick={onClose}>
						<X size={16} />
					</button>
				</div>

				{single ? (
					<div class='big-card' key={`${single.card_id}-${result.tickets}`}>
						<TierCard
							name={single.name}
							image={single.image_full || single.image_url}
							baseUbp={single.base_ubp}
							stars={single.stars}
							isNew={single.is_new}
							celestial={single.is_celestial}
							divine={single.is_divine}
							reveal
						/>
						<div style={{ textAlign: 'center', marginTop: 10 }}>
							<div class='display' style={{ fontWeight: 800, fontSize: 18 }}>
								{single.name}
							</div>
							<div
								style={{
									color: tierColor(single.base_ubp, single.is_celestial, single.is_divine),
									fontWeight: 800,
								}}
							>
								{single.is_celestial
									? 'Небесная карта'
									: (TIER_INFO[single.base_ubp]?.name ?? '')}{' '}
								· +{fmt(single.base_ubp)} UBP
							</div>
						</div>
					</div>
				) : (
					<>
						<div class='stat-grid'>
							<div class='stat'>
								<div class='stat-value'>+{fmt(result.ubp)}</div>
								<div class='stat-label'>UBP</div>
							</div>
							<div class='stat'>
								<div class='stat-value'>{result.new}</div>
								<div class='stat-label'>Новых</div>
							</div>
							<div class='stat'>
								<div class='stat-value'>{fmt(result.tickets)}</div>
								<div class='stat-label'>Тикетов</div>
							</div>
						</div>
						<div class='chips' style={{ marginTop: 10 }}>
							{result.tiers.map((t) => (
								<span class='chip' key={t.tier} style={{ color: TIER_INFO[t.tier]?.color }}>
									{t.name}: {t.count}
								</span>
							))}
						</div>
						<div class='tgrid tgrid-5' style={{ marginTop: 10 }}>
							{result.cards.map((c, i) => (
								<TierCard
									key={`${i}-${c.card_id}`}
									name={c.name}
									image={c.image_url}
									baseUbp={c.base_ubp}
									isNew={c.is_new}
									celestial={c.is_celestial}
									divine={c.is_divine}
									reveal
									delay={Math.min(i * 40, 1200)}
								/>
							))}
						</div>
						{result.cards.length < result.requested && (
							<div class='hint' style={{ marginTop: 8 }}>
								Тикеты закончились — открыто, сколько хватило.
							</div>
						)}
					</>
				)}

				{specials.map((c) => (
					<Panel title='Событие' gold key={`sp-${c.card_id}`}>
						{c.celestial === 'owner' && <div>🌌 Небесная карта «{c.name}» теперь твоя!</div>}
						{c.celestial === 'challenger' && (
							<div>
								⚔️ «{c.name}» занята — ты претендент. Владелец решает 6 часов: бой или отдать карту.
							</div>
						)}
						{c.divine?.map((d) => (
							<div key={d.card_id}>🔱 Божественная карта «{d.name}»!</div>
						))}
					</Panel>
				))}

				<div class='col' style={{ marginTop: 14 }}>
					<button
						type='button'
						class='btn btn-big btn-gold'
						disabled={busy || !canRepeat}
						onClick={onRepeat}
					>
						{busy ? <Loader2 size={18} class='spin' /> : <Dices size={20} />} Крутить ещё
					</button>
					<button type='button' class='btn btn-ghost' onClick={onClose}>
						Закрыть
					</button>
				</div>
			</div>
		</div>
	)
}
