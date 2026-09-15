import { Check, Gem, Lock, Sparkles, Ticket } from 'lucide-react'
import type { TileState } from '../../service/battlePass'

// Награда не растёт с уровнем — на каждом уровне либо немного тикетов, либо немного пыли
// (см. CLAUDE.md, "Сезонный пасс"), никогда оба разом.
function RewardContent({ dust, tickets, coins }: { dust: number; tickets: number; coins: number }) {
	return (
		<span class='bp-tile-reward'>
			{tickets > 0 ? (
				<>
					<Ticket size={16} />
					{tickets}
				</>
			) : (
				<>
					<Sparkles size={16} />
					{dust}
				</>
			)}
			{coins > 0 && (
				<span class='bp-tile-coins'>
					<Gem size={11} />
					{coins}
				</span>
			)}
		</span>
	)
}

export function BattlePassTile({
	dust,
	tickets,
	coins,
	state,
	premium,
	onClick,
}: {
	dust: number
	tickets: number
	coins: number
	state: TileState
	premium: boolean
	onClick?: () => void
}) {
	const cls = ['bp-tile', premium ? 'bp-tile-premium' : 'bp-tile-free', `bp-tile-${state}`].join(
		' ',
	)
	return (
		<button type='button' class={cls} disabled={state !== 'ready'} onClick={onClick}>
			{state === 'locked' && (
				// Награда детерминирована по позиции в круге и не зависит от того, дошёл ли до неё
				// игрок — раньше локнутая ячейка показывала только замок, без превью того, что
				// ждёт на будущем уровне (жалоба пользователя 2026-09-15). Показываем и то, и
				// другое: замок остаётся основным сигналом "недоступно", награда — приглушённая
				// (тем же .bp-tile-locked{opacity:0.4}, что уже приглушал всю ячейку целиком).
				<span class='bp-tile-locked-content'>
					<Lock size={12} />
					<RewardContent dust={dust} tickets={tickets} coins={coins} />
				</span>
			)}
			{state === 'claimed' && <Check size={18} />}
			{state === 'ready' && <RewardContent dust={dust} tickets={tickets} coins={coins} />}
		</button>
	)
}
