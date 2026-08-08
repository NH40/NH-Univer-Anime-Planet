import type { ComponentType } from 'preact/compat'

export interface NavTab {
	path: string
	label: string
	Icon: ComponentType<{ size?: number }>
}
