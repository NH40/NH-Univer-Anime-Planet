import { LayoutGrid, Ticket, User } from 'lucide-react'
import { Link, useLocation } from 'wouter'
import { ROUTE_BATTLE_PASS, ROUTE_COLLECTION, ROUTE_PROFILE } from '../../constants'
import type { NavTab } from '../../types'

const TABS: NavTab[] = [
	{ path: ROUTE_COLLECTION, label: 'Коллекция', Icon: LayoutGrid },
	{ path: ROUTE_PROFILE, label: 'Профиль', Icon: User },
	{ path: ROUTE_BATTLE_PASS, label: 'Battle Pass', Icon: Ticket },
]

export function NavTabs() {
	const [location] = useLocation()
	return (
		<nav class='view-tabs'>
			{TABS.map((tab) => (
				<Link
					key={tab.path}
					href={tab.path}
					class={tab.path === location ? 'view-tab active' : 'view-tab'}
				>
					<tab.Icon size={16} />
					<span>{tab.label}</span>
				</Link>
			))}
		</nav>
	)
}
