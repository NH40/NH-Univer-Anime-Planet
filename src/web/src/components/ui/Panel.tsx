import type { ComponentChildren } from 'preact'

/** Неоновая панель с плашкой-заголовком по центру верхней рамки (дизайн 2026-10-20). */
export function Panel({
	title,
	gold,
	children,
}: {
	title?: string
	gold?: boolean
	children: ComponentChildren
}) {
	return (
		<section class={gold ? 'panel panel-gold' : 'panel'}>
			{title && <div class='panel-badge'>{title}</div>}
			{children}
		</section>
	)
}
