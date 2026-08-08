import { useEffect, useState } from 'preact/hooks'
import { type BattlePassPage, claimBattlePass, fetchBattlePassPage } from '../api'

// Изолирует всё состояние вкладки Battle Pass (страница ленты, загрузка, клейм) —
// подгружается лениво, только когда вкладка реально открыта (см. `active`).
export function useBattlePass(active: boolean, onError: (err: string) => void) {
	const [page, setPage] = useState<BattlePassPage | null>(null)
	const [pageNum, setPageNum] = useState(1)
	const [loading, setLoading] = useState(false)
	const [claiming, setClaiming] = useState(false)

	useEffect(() => {
		if (!active) return
		setLoading(true)
		fetchBattlePassPage(pageNum)
			.then(setPage)
			.catch((err: unknown) => onError(String(err)))
			.finally(() => setLoading(false))
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [active, pageNum])

	function claim(track: 'free' | 'premium') {
		setClaiming(true)
		claimBattlePass(track)
			.then(() => fetchBattlePassPage(pageNum))
			.then(setPage)
			.catch((err: unknown) => onError(String(err)))
			.finally(() => setClaiming(false))
	}

	return {
		page,
		pageNum,
		loading,
		claiming,
		claim,
		prevPage: () => setPageNum((p) => Math.max(1, p - 1)),
		nextPage: () => setPageNum((p) => (page ? Math.min(page.total_pages, p + 1) : p)),
	}
}
