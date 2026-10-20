import { Loader2, PartyPopper } from 'lucide-react'
import { useState } from 'preact/hooks'
import type { CardStack, Universe } from '../api'
import { TIER_INFO } from '../config'
import { EVENTS_TAB_CODE } from '../constants'
import { TierCard } from '../components/ui/TierCard'
import { useCollection } from '../hooks/useCollection'

export function CollectionPage({
	universes,
	selectedUniverse,
	onSelectUniverse,
	onOpenCard,
	version,
}: {
	universes: Universe[]
	selectedUniverse: string | null
	onSelectUniverse: (code: string) => void
	onOpenCard: (card: CardStack) => void
	version: number
}) {
	const [search, setSearch] = useState('')
	const [tierFilter, setTierFilter] = useState<number | 'all'>('all')
	const { cards, hasMore, loading, loadMore } = useCollection(selectedUniverse, search, tierFilter, version)

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

					{cards.length === 0 && !loading ? (
						<div class='empty'>Ничего не найдено.</div>
					) : (
						<>
							<div class='tgrid'>
								{cards.map((card) => (
									<TierCard
										key={`${card.card_id}-${card.stars}`}
										name={card.name}
										image={card.image_url}
										baseUbp={card.base_ubp}
										stars={card.stars}
										quantity={card.quantity}
										onClick={() => onOpenCard(card)}
									/>
								))}
							</div>
							{loading && (
								<div class='grid-loading' key='grid-loading'>
									<Loader2 size={18} class='spin' />
								</div>
							)}
							{hasMore && !loading && (
								<button type='button' class='load-more-button' onClick={loadMore}>
									Показать ещё
								</button>
							)}
						</>
					)}
				</>
			)}
		</>
	)
}
