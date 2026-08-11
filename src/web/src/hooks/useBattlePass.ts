import { useEffect, useState } from 'preact/hooks'
import {
	type BattlePassPage,
	claimBattlePassAll,
	claimBattlePassLevel,
	fetchBattlePassPage,
} from '../api'

// Изолирует всё состояние вкладки Battle Pass (страница ленты, загрузка, клейм) —
// подгружается лениво, только когда вкладка реально открыта (см. `active`).
export function useBattlePass(active: boolean, onError: (err: string) => void) {
	const [page, setPage] = useState<BattlePassPage | null>(null)
	// undefined — "открыть на странице с первым незабранным уровнем" (сервер сам решает,
	// см. api/routers/battle_pass.py); после первой загрузки держим явный номер страницы,
	// чтобы Prev/Next и повторная загрузка после клейма оставались на месте.
	const [pageNum, setPageNum] = useState<number | undefined>(undefined)
	const [loading, setLoading] = useState(false)
	const [claiming, setClaiming] = useState(false)

	useEffect(() => {
		if (!active) return
		setLoading(true)
		fetchBattlePassPage(pageNum)
			.then((data) => {
				setPage(data)
				setPageNum(data.page)
			})
			.catch((err: unknown) => onError(String(err)))
			.finally(() => setLoading(false))
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [active, pageNum])

	function reload(nextPage: number) {
		setLoading(true)
		fetchBattlePassPage(nextPage)
			.then((data) => {
				setPage(data)
				setPageNum(data.page)
			})
			.catch((err: unknown) => onError(String(err)))
			.finally(() => setLoading(false))
	}

	// Тап по одной ячейке — забирает только её награду и остаётся на той же странице (см.
	// CLAUDE.md, "Сезонный пасс: клейм произвольной ячейки").
	function claimLevel(track: 'free' | 'premium', level: number) {
		if (pageNum === undefined) return
		const current = pageNum
		setClaiming(true)
		claimBattlePassLevel(track, level)
			.then(() => reload(current))
			.catch((err: unknown) => {
				onError(String(err))
				setClaiming(false)
			})
			.finally(() => setClaiming(false))
	}

	// "Забрать всё" по ветке — редирект на страницу с текущим уровнем (сервер сам считает
	// её и возвращает в ответе, см. api/routers/battle_pass.py).
	function claimAll(track: 'free' | 'premium') {
		setClaiming(true)
		claimBattlePassAll(track)
			.then((result) => reload(result.page))
			.catch((err: unknown) => {
				onError(String(err))
				setClaiming(false)
			})
			.finally(() => setClaiming(false))
	}

	return {
		page,
		loading,
		claiming,
		claimLevel,
		claimAll,
		prevPage: () => pageNum !== undefined && setPageNum(Math.max(1, pageNum - 1)),
		nextPage: () => page && pageNum !== undefined && setPageNum(Math.min(page.total_pages, pageNum + 1)),
	}
}
