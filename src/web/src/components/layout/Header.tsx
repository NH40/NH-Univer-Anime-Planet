import { Gem, Sparkles, Ticket } from 'lucide-react'
import type { Profile } from '../../api'
import { fmt } from '../../service/ui'

/** Шапка: имя игрока и три валюты (🎫 тикеты, ✨ пыль, 💎 коины — те же, что в боте). */
export function Header({ profile }: { profile: Profile | null }) {
	return (
		<header class='top-bar'>
			<div class='top-name'>{profile?.display_name ?? 'Игрок'}</div>
			<div class='currencies'>
				<span class='cur' title='Тикеты'>
					<Ticket size={13} /> {fmt(profile?.tickets)}
				</span>
				<span class='cur' title='Пыль'>
					<Sparkles size={13} /> {fmt(profile?.dust)}
				</span>
				<span class='cur' title='Коины'>
					<Gem size={13} /> {fmt(profile?.coins)}
				</span>
			</div>
		</header>
	)
}
