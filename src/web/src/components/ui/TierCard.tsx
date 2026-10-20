import { TIER_INFO } from '../../config'

const CELESTIAL_COLOR = '#f5c96a'
const DIVINE_COLOR = '#ff7ad9'

export function tierColor(baseUbp: number, celestial?: boolean, divine?: boolean): string {
	if (divine) return DIVINE_COLOR
	if (celestial) return CELESTIAL_COLOR
	return TIER_INFO[baseUbp]?.color ?? '#6b7a99'
}

/** Карта в рамке цвета тира со свечением — общий вид для коллекции, крутки, небесных. */
export function TierCard({
	name,
	image,
	baseUbp,
	stars,
	quantity,
	isNew,
	celestial,
	divine,
	reveal,
	delay = 0,
	onClick,
}: {
	name: string
	image: string
	baseUbp: number
	stars?: number
	quantity?: number
	isNew?: boolean
	celestial?: boolean
	divine?: boolean
	reveal?: boolean
	delay?: number
	onClick?: () => void
}) {
	return (
		<button
			type='button'
			class={reveal ? 'tcard reveal' : 'tcard'}
			style={{ '--tier': tierColor(baseUbp, celestial, divine), animationDelay: `${delay}ms` }}
			onClick={onClick}
		>
			<img
				src={image}
				alt={name}
				loading='lazy'
				decoding='async'
				onError={(e) => {
					// Превью генерируется на первом запросе — при разовом сбое пробуем ещё раз.
					const img = e.currentTarget as HTMLImageElement
					if (img.dataset.retry) return
					img.dataset.retry = '1'
					setTimeout(() => {
						img.src = `${image}${image.includes('?') ? '&' : '?'}r=1`
					}, 700)
				}}
			/>
			{isNew && <span class='tcard-badge tcard-new'>NEW</span>}
			{(stars || quantity) && (
				<span class='tcard-badge'>
					{stars ? `★${stars}` : ''}
					{quantity && quantity > 1 ? ` ×${quantity}` : ''}
				</span>
			)}
			<span class='tcard-label'>{name}</span>
		</button>
	)
}
