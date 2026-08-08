export type TileState = 'locked' | 'claimed' | 'ready'

export function tileState(unlocked: boolean, claimed: boolean): TileState {
	if (!unlocked) return 'locked'
	return claimed ? 'claimed' : 'ready'
}
