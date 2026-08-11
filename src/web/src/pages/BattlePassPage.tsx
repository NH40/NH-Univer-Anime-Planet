import { CalendarOff, ChevronLeft, ChevronRight, Gift, Loader2 } from 'lucide-react'
import type { BattlePassPage as BattlePassPageData } from '../api'
import { BattlePassTile } from '../components/ui/BattlePassTile'
import { tileState } from '../service/battlePass'

export function BattlePassPage({
	data,
	loading,
	claiming,
	onPrev,
	onNext,
	onClaimLevel,
	onClaimAll,
}: {
	data: BattlePassPageData | null
	loading: boolean
	claiming: boolean
	onPrev: () => void
	onNext: () => void
	onClaimLevel: (track: 'free' | 'premium', level: number) => void
	onClaimAll: (track: 'free' | 'premium') => void
}) {
	if (loading && !data) {
		return (
			<div class='empty'>
				<Loader2 size={20} class='spin' /> Загрузка…
			</div>
		)
	}
	if (!data) {
		return (
			<div class='empty'>
				<CalendarOff size={20} /> Сейчас нет активного сезона.
			</div>
		)
	}

	const have = data.progress - data.level_floor
	const need = data.level_ceiling - data.level_floor
	const percent = need > 0 ? Math.round((100 * have) / need) : 100
	// "Забрать всё" зависит от high-water mark ветки целиком, не от того, что видно именно
	// на этой странице — незабранные уровни могут лежать на другой странице.
	const freeClaimAllAvailable = data.claimed_free_level < data.current_level
	const premiumClaimAllAvailable = data.is_premium && data.claimed_premium_level < data.current_level

	return (
		<div class='battle-pass-page'>
			<div class='battle-pass-summary'>
				<div class='battle-pass-summary-top'>
					<span>
						Уровень <b>{data.current_level}</b>
					</span>
					<span class='battle-pass-summary-need'>
						{have}/{need} до след.
					</span>
				</div>
				<div class='progress-bar-track'>
					<div class='progress-bar-fill' style={{ width: `${percent}%` }} />
				</div>
			</div>

			{/* Горизонтальная лента: колонка на уровень, в колонке — квадратик премиум-ветки
			    сверху (золотой градиент — "покруче" бесплатной) и бесплатной снизу. Тап по
			    доступному квадратику забирает НАГРАДУ ИМЕННО ЭТОЙ ЯЧЕЙКИ — можно кликать в
			    любом порядке (см. CLAUDE.md, "Сезонный пасс: клейм произвольной ячейки").
			    Колонка текущего уровня подсвечена (.bp-column-current). */}
			<div class='battle-pass-track'>
				{data.entries.map((entry) => {
					const freeState = tileState(entry.unlocked, entry.free_claimed)
					const premiumState = !data.is_premium
						? 'locked'
						: tileState(entry.unlocked, entry.premium_claimed)
					const isCurrent = entry.level === data.current_level
					return (
						<div class={isCurrent ? 'bp-column bp-column-current' : 'bp-column'} key={entry.level}>
							<BattlePassTile
								dust={entry.premium_dust}
								tickets={entry.premium_tickets}
								coins={entry.premium_coins}
								state={premiumState}
								premium
								onClick={
									!claiming && premiumState === 'ready'
										? () => onClaimLevel('premium', entry.level)
										: undefined
								}
							/>
							<BattlePassTile
								dust={entry.free_dust}
								tickets={entry.free_tickets}
								coins={0}
								state={freeState}
								premium={false}
								onClick={
									!claiming && freeState === 'ready' ? () => onClaimLevel('free', entry.level) : undefined
								}
							/>
							<div class='bp-level-label'>{entry.level}</div>
						</div>
					)
				})}
			</div>

			<div class='battle-pass-nav'>
				<button type='button' disabled={data.page <= 1} onClick={onPrev}>
					<ChevronLeft size={18} />
				</button>
				<span class='battle-pass-nav-page'>
					{data.page}/{data.total_pages}
				</span>
				<button type='button' disabled={data.page >= data.total_pages} onClick={onNext}>
					<ChevronRight size={18} />
				</button>
			</div>

			{(freeClaimAllAvailable || premiumClaimAllAvailable) && (
				<div class='battle-pass-claim-all'>
					{freeClaimAllAvailable && (
						<button type='button' disabled={claiming} onClick={() => onClaimAll('free')}>
							<Gift size={16} /> Забрать всё (бесплатная)
						</button>
					)}
					{premiumClaimAllAvailable && (
						<button type='button' disabled={claiming} onClick={() => onClaimAll('premium')}>
							<Gift size={16} /> Забрать всё (премиум)
						</button>
					)}
				</div>
			)}
		</div>
	)
}
