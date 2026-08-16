import { useEffect, useRef, useState } from 'preact/hooks'
import { type CardStack, fetchCollection, fetchEventCollection } from '../api'
import { EVENTS_TAB_CODE } from '../constants'

// 20 карт за раз, следующая порция — по кнопке "Показать ещё" внизу сетки (см.
// CollectionPage) — не вся коллекция вселенной одним ответом (см. CLAUDE.md, "Долгая
// загрузка карт в Mini App"). Автоматическая подгрузка по скроллу (IntersectionObserver,
// потом обычное scroll-событие) в Telegram Desktop Mini App WebView ни разу не сработала —
// явная кнопка не зависит от таких особенностей конкретного WebView (2026-08-17).
const PAGE_SIZE = 20
// Поиск не долбит API на каждое нажатие клавиши — та же идея, что debounce везде.
const SEARCH_DEBOUNCE_MS = 350

function fetchPage(universe: string, offset: number, search: string, tier: number | 'all') {
	const query = {
		offset,
		limit: PAGE_SIZE,
		search: search || undefined,
		tier: tier === 'all' ? undefined : tier,
	}
	return universe === EVENTS_TAB_CODE
		? fetchEventCollection(query)
		: fetchCollection(universe, query)
}

// Владеет своей пагинацией/поиском/фильтром — отдельно от useAppData (тот только про
// bootstrap-экран профиля/вселенных/прогресса, коллекция теперь целиком локальна
// странице, где и живёт её UI-состояние).
export function useCollection(
	selectedUniverse: string | null,
	search: string,
	tier: number | 'all',
) {
	const [cards, setCards] = useState<CardStack[]>([])
	const [hasMore, setHasMore] = useState(false)
	const [loading, setLoading] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const offsetRef = useRef(0)
	const requestIdRef = useRef(0)

	useEffect(() => {
		if (!selectedUniverse) {
			setCards([])
			setHasMore(false)
			return
		}

		const requestId = ++requestIdRef.current
		const timer = setTimeout(
			() => {
				setLoading(true)
				fetchPage(selectedUniverse, 0, search, tier)
					.then((page) => {
						if (requestId !== requestIdRef.current) return // устарел — вселенную/фильтр уже сменили
						setCards(page.items)
						setHasMore(page.has_more)
						offsetRef.current = page.items.length
					})
					.catch((err: unknown) => setError(String(err)))
					.finally(() => {
						if (requestId === requestIdRef.current) setLoading(false)
					})
			},
			search ? SEARCH_DEBOUNCE_MS : 0,
		)

		return () => clearTimeout(timer)
	}, [selectedUniverse, search, tier])

	function loadMore() {
		if (!selectedUniverse || loading || !hasMore) return
		const requestId = requestIdRef.current
		setLoading(true)
		fetchPage(selectedUniverse, offsetRef.current, search, tier)
			.then((page) => {
				if (requestId !== requestIdRef.current) return
				setCards((prev) => [...prev, ...page.items])
				setHasMore(page.has_more)
				offsetRef.current += page.items.length
			})
			.catch((err: unknown) => setError(String(err)))
			.finally(() => {
				if (requestId === requestIdRef.current) setLoading(false)
			})
	}

	return { cards, hasMore, loading, error, loadMore }
}
