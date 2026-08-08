import { Globe } from 'lucide-react'
import type { UniverseProgress } from '../api'

export function ProgressPage({ progress }: { progress: UniverseProgress[] }) {
	if (progress.length === 0) {
		return <div class='empty'>Пока нет ни одной карточки — крутите в боте!</div>
	}
	return (
		<div class='progress-page'>
			{progress.map((p) => (
				<div class='progress-row' key={p.code}>
					<div class='progress-row-header'>
						<span class='progress-row-title'>
							<Globe size={14} /> {p.title}
						</span>
						<span class='progress-row-count'>
							{p.owned}/{p.total}
						</span>
					</div>
					<div class='progress-bar-track'>
						<div class='progress-bar-fill' style={{ width: `${p.percent}%` }} />
					</div>
					<div class='progress-row-percent'>{p.percent}%</div>
				</div>
			))}
		</div>
	)
}
