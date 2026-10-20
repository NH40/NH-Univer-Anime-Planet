import { useEffect, useState } from 'preact/hooks'
import { onToast } from '../../service/ui'

export function Toast() {
	const [item, setItem] = useState<{ text: string; err: boolean; id: number } | null>(null)

	useEffect(
		() =>
			onToast((text, err) => {
				const id = Date.now()
				setItem({ text, err, id })
				setTimeout(() => setItem((cur) => (cur?.id === id ? null : cur)), 3200)
			}),
		[],
	)

	if (!item) return null
	return (
		<div class={item.err ? 'toast err' : 'toast'} key={item.id} onClick={() => setItem(null)}>
			{item.text}
		</div>
	)
}
