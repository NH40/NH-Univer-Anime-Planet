import { render } from 'preact'
import { App } from './App'
import { ROUTE_BATTLE_PASS, ROUTE_PROFILE } from './constants'
import './styles.css'

// Бот открывает Mini App через query-параметр (?view=battlepass/profile, см.
// keyboards/battle_pass, keyboards/profile) — конвертируем в настоящий путь ДО того, как
// это увидит роутер wouter (useLocation читает location.pathname), иначе первый рендер
// на кадр показал бы коллекцию вместо запрошенной вкладки.
const initialView = new URLSearchParams(window.location.search).get('view')
if (initialView === 'battlepass') {
	window.history.replaceState(null, '', ROUTE_BATTLE_PASS)
} else if (initialView === 'profile') {
	window.history.replaceState(null, '', ROUTE_PROFILE)
}

const root = document.getElementById('app')
if (root) {
	render(<App />, root)
}
