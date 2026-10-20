import { ArrowLeft, Combine, Sparkles } from 'lucide-react'
import { useState } from 'preact/hooks'
import { type CardStack, distill, mergeCard } from '../api'
import { Panel } from '../components/ui/Panel'
import { TierCard, tierColor } from '../components/ui/TierCard'
import { TIER_INFO } from '../config'
import { fmt, run } from '../service/ui'

// Зеркало config/game.py бота: MAX_STARS, MERGE_COPIES_REQUIRED, dust_for_stars().
const MAX_STARS = 5
const MERGE_COPIES = 5
const dustFor = (baseUbp: number, stars: number) =>
	Math.floor(baseUbp / 1000) * MERGE_COPIES ** (stars - 1)

export function CardPage({
	card,
	universeTitle,
	onBack,
	onChanged,
}: {
	card: CardStack
	universeTitle: string
	onBack: () => void
	onChanged: () => void
}) {
	const [busy, setBusy] = useState(false)
	const [amount, setAmount] = useState('1')
	const [confirm, setConfirm] = useState<null | { label: string; action: () => Promise<unknown> }>(
		null,
	)
	const tier = TIER_INFO[card.base_ubp]
	// Небесные/божественные (10000+ UBP) — без слияния и распыления, как в боте.
	const relic = card.base_ubp >= 10000
	const canMerge = !relic && card.stars < MAX_STARS && card.quantity >= MERGE_COPIES
	const perCard = dustFor(card.base_ubp, card.stars)

	const act = async (action: () => Promise<unknown>) => {
		setBusy(true)
		setConfirm(null)
		const res = await run(action)
		setBusy(false)
		if (res) onChanged()
	}
	const ask = (label: string, action: () => Promise<unknown>) => setConfirm({ label, action })
	const n = Math.max(1, Math.min(card.quantity, Number(amount) || 1))

	return (
		<div class='card-page'>
			<button type='button' class='btn btn-ghost btn-sm' onClick={onBack}>
				<ArrowLeft size={16} /> Назад
			</button>
			<div class='big-card'>
				<TierCard
					name={card.name}
					image={card.image_full || card.image_url}
					baseUbp={card.base_ubp}
					stars={card.stars}
				/>
			</div>
			<div style={{ textAlign: 'center' }}>
				<div class='display' style={{ fontWeight: 800, fontSize: 18 }}>
					{card.name}
				</div>
				<div style={{ color: tierColor(card.base_ubp), fontWeight: 800 }}>
					{tier?.name ?? 'Особая'} · {'★'.repeat(card.stars)}
				</div>
			</div>

			<Panel title='Карта'>
				<div class='kv'>
					<span>ID</span>
					<span>#{card.external_id}</span>
				</div>
				<div class='kv'>
					<span>Вселенная</span>
					<span>{universeTitle}</span>
				</div>
				<div class='kv'>
					<span>Очки</span>
					<span>{fmt(card.base_ubp)} UBP</span>
				</div>
				<div class='kv'>
					<span>Копий</span>
					<span>×{card.quantity}</span>
				</div>
				{card.description && (
					<p class='hint' style={{ marginTop: 10 }}>
						{card.description}
					</p>
				)}
			</Panel>

			{!relic && (
				<Panel title='Слияние'>
					<div class='hint'>
						5 копий ★{card.stars} → 1 копия ★{card.stars + 1}. Максимум ★{MAX_STARS}.
					</div>
					<div class='row' style={{ marginTop: 10 }}>
						<button
							type='button'
							class='btn'
							disabled={busy || !canMerge}
							onClick={() => act(() => mergeCard(card.card_id, card.stars, card.stars + 1, true))}
						>
							<Combine size={16} /> Слить 5 → ★{card.stars + 1}
						</button>
						<button
							type='button'
							class='btn btn-ghost'
							disabled={busy || !canMerge}
							onClick={() => act(() => mergeCard(card.card_id, card.stars, MAX_STARS, false))}
						>
							Слить всё до макс.
						</button>
					</div>
				</Panel>
			)}

			{!relic && (
				<Panel title='Распыление'>
					<div class='hint'>
						Одна копия — {fmt(perCard)} пыли. Необратимо.
					</div>
					<div class='row' style={{ marginTop: 10 }}>
						<input
							class='input'
							style={{ width: 90 }}
							type='number'
							min={1}
							max={card.quantity}
							value={amount}
							onInput={(e) => setAmount((e.target as HTMLInputElement).value)}
						/>
						<button
							type='button'
							class='btn'
							disabled={busy}
							onClick={() =>
								ask(`Распылить ${n} шт. за ${fmt(n * perCard)} пыли?`, () =>
									distill('amount', card.card_id, card.stars, n),
								)
							}
						>
							<Sparkles size={16} /> Распылить
						</button>
					</div>
					<div class='row' style={{ marginTop: 8 }}>
						<button
							type='button'
							class='btn btn-ghost btn-sm'
							disabled={busy || card.quantity < 2}
							onClick={() =>
								ask(`Распылить все дубликаты (оставить 1) за ${fmt((card.quantity - 1) * perCard)} пыли?`, () =>
									distill('duplicates', card.card_id, card.stars),
								)
							}
						>
							Все дубликаты
						</button>
						<button
							type='button'
							class='btn btn-ghost btn-sm'
							disabled={busy}
							onClick={() =>
								ask(`Распылить все ${card.quantity} шт. за ${fmt(card.quantity * perCard)} пыли?`, () =>
									distill('all', card.card_id, card.stars),
								)
							}
						>
							Все копии
						</button>
					</div>
					{confirm && (
						<div class='col' style={{ marginTop: 10 }}>
							<div style={{ fontWeight: 800 }}>{confirm.label}</div>
							<div class='row'>
								<button type='button' class='btn btn-danger' onClick={() => act(confirm.action)}>
									Да, распылить
								</button>
								<button type='button' class='btn btn-ghost' onClick={() => setConfirm(null)}>
									Отмена
								</button>
							</div>
						</div>
					)}
				</Panel>
			)}
		</div>
	)
}
