import { Combine, Dices, LayoutGrid, ListChecks, Menu } from 'lucide-react'
import { Link, useLocation } from 'wouter'
import {
	ROUTE_COLLECTION,
	ROUTE_MERGE,
	ROUTE_MORE,
	ROUTE_QUESTS,
	ROUTE_ROLL,
} from '../../constants'
import type { NavTab } from '../../types'

const TABS: NavTab[] = [
	{ path: ROUTE_ROLL, label: 'Крутка', Icon: Dices },
	{ path: ROUTE_COLLECTION, label: 'Коллекция', Icon: LayoutGrid },
	{ path: ROUTE_MERGE, label: 'Слияния', Icon: Combine },
	{ path: ROUTE_QUESTS, label: 'Задания', Icon: ListChecks },
	{ path: ROUTE_MORE, label: 'Ещё', Icon: Menu },
]

// Пути из «Ещё» (профиль, пасс, топ, ...) подсвечивают вкладку «Ещё».
const MAIN_PATHS = new Set(TABS.map((t) => t.path))

export function NavTabs() {
	const [location] = useLocation()
	const active = MAIN_PATHS.has(location) ? location : ROUTE_MORE
	return (
		<nav class='bottom-nav'>
			{TABS.map((tab) => (
				<Link
					key={tab.path}
					href={tab.path}
					class={tab.path === active ? 'bottom-tab active' : 'bottom-tab'}
				>
					<tab.Icon size={20} />
					<span>{tab.label}</span>
				</Link>
			))}
		</nav>
	)
}
