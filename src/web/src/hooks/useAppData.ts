import { useEffect, useState } from 'preact/hooks'
import {
	type Profile,
	type Universe,
	type UniverseProgress,
	fetchProfile,
	fetchProgress,
	fetchUniverses,
} from '../api'

// Собирает данные, нужные для первого экрана (профиль/список вселенных/прогресс) —
// карточки коллекции сюда больше не входят, у них своя пагинация (см. hooks/useCollection),
// владеет ей CollectionPage напрямую (см. CLAUDE.md, "Долгая загрузка карт в Mini App").
export function useAppData() {
	const [profile, setProfile] = useState<Profile | null>(null)
	const [universes, setUniverses] = useState<Universe[]>([])
	const [progress, setProgress] = useState<UniverseProgress[]>([])
	const [selectedUniverse, setSelectedUniverse] = useState<string | null>(null)
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		Promise.all([fetchProfile(), fetchUniverses(), fetchProgress()])
			.then(([profileData, universesData, progressData]) => {
				setProfile(profileData)
				setUniverses(universesData)
				setProgress(progressData)
				if (universesData.length > 0) {
					setSelectedUniverse(universesData[0].code)
				}
			})
			.catch((err: unknown) => setError(String(err)))
			.finally(() => setLoading(false))
	}, [])

	return {
		profile,
		universes,
		progress,
		selectedUniverse,
		setSelectedUniverse,
		loading,
		error,
	}
}
