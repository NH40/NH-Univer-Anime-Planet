import { Loader2, PartyPopper, Star } from 'lucide-react'
import { useEffect, useState } from 'preact/hooks'
import type { CardStack, Universe } from '../api'
import { TIER_INFO } from '../config'
import { EVENTS_TAB_CODE } from '../constants'
import { useCollection } from '../hooks/useCollection'

// Насколько рано (в пикселях до конца страницы) подгружать следующую порцию — тот же
// смысл, что у прежнего IntersectionObserver rootMargin.
const LOAD_MORE_THRESHOLD_PX = 400

export function CollectionPage({
	universes,
	selectedUniverse,
	onSelectUniverse,
	onOpenCard,
}: {
	universes: Universe[]
	selectedUniverse: string | null
	onSelectUniverse: (code: string) => void
	onOpenCard: (card: CardStack) => void
}) {
	const [search, setSearch] = useState('')
	const [tierFilter, setTierFilter] = useState<number | 'all'>('all')
	const { cards, hasMore, loading, loadMore } = useCollection(selectedUniverse, search, tierFilter)

	// Пагинация по скроллу — раньше на IntersectionObserver (сентинел внизу сетки), но в
	// Telegram Desktop Mini App WebView он ни разу не сработал (та же категория проблем,
	// что requestAnimationFrame у PageTransition — см. CLAUDE.md, 2026-08-17). Обычное
	// событие scroll не зависит от подобных API и надёжно работает везде.
	useEffect(() => {
		if (!hasMore) return
		function checkScroll() {
			const scrolledToBottom =
				document.documentElement.scrollHeight - (window.scrollY + window.innerHeight) < LOAD_MORE_THRESHOLD_PX
			if (scrolledToBottom) loadMore()
		}
		checkScroll() // короткая страница может не требовать скролла вовсе
		window.addEventListener('scroll', checkScroll, { passive: true })
		window.addEventListener('resize', checkScroll)
		return () => {
			window.removeEventListener('scroll', checkScroll)
			window.removeEventListener('resize', checkScroll)
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [hasMore, selectedUniverse, search, tierFilter])

	return (
		<>
			<nav class='universe-tabs'>
				{universes.map((universe) => (
					<button
						key={universe.code}
						type='button'
						class={universe.code === selectedUniverse ? 'tab active' : 'tab'}
						onClick={() => onSelectUniverse(universe.code)}
					>
						{universe.title}
					</button>
				))}
				<button
					type='button'
					class={selectedUniverse === EVENTS_TAB_CODE ? 'tab active' : 'tab'}
					onClick={() => onSelectUniverse(EVENTS_TAB_CODE)}
				>
					<PartyPopper size={14} /> Ивенты
				</button>
			</nav>

			{selectedUniverse === null ? (
				<div class='empty'>Пока нет ни одной карточки — крутите в боте!</div>
			) : (
				<>
					<div class='filters'>
						<div class='search-input-wrap'>
							<input
								class='search-input'
								type='search'
								placeholder='Поиск по имени…'
								value={search}
								onInput={(e) => setSearch((e.target as HTMLInputElement).value)}
							/>
						</div>
						<select
							class='tier-select'
							value={String(tierFilter)}
							onChange={(e) => {
								const value = (e.target as HTMLSelectElement).value
								setTierFilter(value === 'all' ? 'all' : Number(value))
							}}
						>
							<option value='all'>Все тиры</option>
							{Object.entries(TIER_INFO)
								.sort(([a], [b]) => Number(b) - Number(a))
								.map(([ubp, info]) => (
									<option key={ubp} value={ubp}>
										{info.name}
									</option>
								))}
						</select>
					</div>

					<div style={{ opacity: 0.6, fontSize: 11, marginBottom: 4 }}>
						DEBUG cards.length={cards.length} hasMore={String(hasMore)} loading={String(loading)}
					</div>
					{cards.length === 0 && !loading ? (
						<div class='empty'>Ничего не найдено.</div>
					) : (
						<>
							<div class='grid'>
								{cards.map((card) => {
									const tier = TIER_INFO[card.base_ubp]
									return (
										<button
											type='button'
											class='card'
											key={`${card.card_id}-${card.stars}`}
											onClick={() => onOpenCard(card)}
										>
											{tier && <span class='card-tier-dot' style={{ background: tier.color }} />}
											<img src={card.image_url} alt={card.name} loading='lazy' />
											<div class='card-name'>{card.name}</div>
											<div class='card-meta'>
												<span class='card-meta-stars'>
													<Star size={11} fill='currentColor' /> {card.stars}
												</span>
												<span>{card.base_ubp} UBP</span>
												<span>×{card.quantity}</span>
											</div>
										</button>
									)
								})}
							</div>
							{loading && (
								<div class='grid-loading' key='grid-loading'>
									<Loader2 size={18} class='spin' />
								</div>
							)}
						</>
					)}
				</>
			)}
		</>
	)
}
