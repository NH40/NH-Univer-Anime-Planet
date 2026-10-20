import { AlertTriangle, Loader2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'preact/hooks'
import { Route, Switch, useLocation } from 'wouter'
import type { CardStack } from './api'
import { Header } from './components/layout/Header'
import { NavTabs } from './components/layout/NavTabs'
import { PageTransition } from './components/layout/PageTransition'
import { Toast } from './components/layout/Toast'
import {
	EVENTS_TAB_CODE,
	ROUTE_ADMIN,
	ROUTE_BATTLE_PASS,
	ROUTE_CELESTIAL,
	ROUTE_CLAN,
	ROUTE_COLLECTION,
	ROUTE_MERGE,
	ROUTE_MORE,
	ROUTE_PROFILE,
	ROUTE_QUESTS,
	ROUTE_ROLL,
	ROUTE_SHOP,
	ROUTE_TOP,
} from './constants'
import { useAppData } from './hooks/useAppData'
import { useBattlePass } from './hooks/useBattlePass'
import { AdminPage } from './pages/AdminPage'
import { BattlePassPage } from './pages/BattlePassPage'
import { CardPage } from './pages/CardPage'
import { CollectionPage } from './pages/CollectionPage'
import { MergePage } from './pages/MergePage'
import { CelestialPage, ClanPage, MorePage, ShopPage, TopPage } from './pages/MorePages'
import { ProgressPage } from './pages/ProgressPage'
import { QuestsPage } from './pages/QuestsPage'
import { RollPage } from './pages/RollPage'
import { onRefresh } from './service/ui'
import { getWebApp } from './telegram'

export function App() {
	const [location] = useLocation()
	const [selectedCard, setSelectedCard] = useState<CardStack | null>(null)
	const [appError, setAppError] = useState<string | null>(null)
	// Растёт после любого действия, меняющего коллекцию/баланс, — коллекция перезапрашивается.
	const [version, setVersion] = useState(0)

	const {
		profile,
		reloadProfile,
		universes,
		progress,
		selectedUniverse,
		setSelectedUniverse,
		loading,
		error,
	} = useAppData()
	const battlePass = useBattlePass(location === ROUTE_BATTLE_PASS, setAppError)

	useEffect(() => {
		// Тема фиксированная неоновая (дизайн 2026-10-20) — Telegram-тему не применяем, только
		// красим системные полосы WebView в цвет фона.
		const webApp = getWebApp()
		webApp?.ready()
		webApp?.expand()
		webApp?.setHeaderColor?.('#050814')
		webApp?.setBackgroundColor?.('#050814')
	}, [])

	useEffect(
		() =>
			onRefresh(() => {
				reloadProfile()
				setVersion((v) => v + 1)
			}),
		[],
	)

	useEffect(() => {
		setSelectedCard(null)
		window.scrollTo(0, 0)
	}, [location])

	// Нативная кнопка «Назад» Telegram: закрывает карточку, иначе с вложенных экранов «Ещё»
	// возвращает в «Ещё».
	useEffect(() => {
		const webApp = getWebApp()
		if (!webApp) return
		const nested = ![ROUTE_ROLL, ROUTE_COLLECTION, ROUTE_MERGE, ROUTE_QUESTS, ROUTE_MORE].includes(location)
		const onBack = () => {
			if (selectedCard) setSelectedCard(null)
			else window.history.back()
		}
		if (selectedCard || nested) {
			webApp.BackButton.show()
			webApp.BackButton.onClick(onBack)
		} else {
			webApp.BackButton.hide()
		}
		return () => webApp.BackButton.offClick(onBack)
	}, [selectedCard, location])

	const universeTitleByCode = useMemo(() => {
		const map = new Map<string, string>()
		for (const u of universes) map.set(u.code, u.title)
		return map
	}, [universes])

	if (loading) {
		return (
			<div class='screen center'>
				<Loader2 size={22} class='spin' /> Загрузка…
			</div>
		)
	}
	const fatalError = error ?? appError
	if (fatalError) {
		return (
			<div class='screen center error'>
				<AlertTriangle size={20} /> {fatalError}
			</div>
		)
	}

	const transitionId = selectedCard ? `card-${selectedCard.card_id}-${selectedCard.stars}` : location

	return (
		<div class='screen'>
			<Header profile={profile} />

			<PageTransition id={transitionId}>
				{selectedCard ? (
					<CardPage
						card={selectedCard}
						universeTitle={
							selectedUniverse === EVENTS_TAB_CODE
								? 'Ивент'
								: (universeTitleByCode.get(selectedUniverse ?? '') ?? '')
						}
						onBack={() => setSelectedCard(null)}
						onChanged={() => setSelectedCard(null)}
					/>
				) : (
					<Switch>
						<Route path={ROUTE_ROLL}>
							<RollPage />
						</Route>
						<Route path={ROUTE_MERGE}>
							<MergePage universes={universes} />
						</Route>
						<Route path={ROUTE_QUESTS}>
							<QuestsPage />
						</Route>
						<Route path={ROUTE_MORE}>
							<MorePage profile={profile} />
						</Route>
						<Route path={ROUTE_CELESTIAL}>
							<CelestialPage />
						</Route>
						<Route path={ROUTE_TOP}>
							<TopPage />
						</Route>
						<Route path={ROUTE_SHOP}>
							<ShopPage />
						</Route>
						<Route path={ROUTE_CLAN}>
							<ClanPage />
						</Route>
						<Route path={ROUTE_ADMIN}>
							{profile?.is_admin ? (
								<AdminPage isSuper={profile.is_super_admin} />
							) : (
								<div class='empty'>Нет доступа.</div>
							)}
						</Route>
						<Route path={ROUTE_PROFILE}>
							<div class='page-title'>Прогресс коллекции</div>
							<ProgressPage progress={progress} />
						</Route>
						<Route path={ROUTE_BATTLE_PASS}>
							<BattlePassPage
								data={battlePass.page}
								loading={battlePass.loading}
								claiming={battlePass.claiming}
								onPrev={battlePass.prevPage}
								onNext={battlePass.nextPage}
								onClaimLevel={battlePass.claimLevel}
								onClaimAll={battlePass.claimAll}
							/>
						</Route>
						<Route>
							<CollectionPage
								universes={universes}
								selectedUniverse={selectedUniverse}
								onSelectUniverse={setSelectedUniverse}
								onOpenCard={setSelectedCard}
								version={version}
							/>
						</Route>
					</Switch>
				)}
			</PageTransition>
			<NavTabs />
			<Toast />
		</div>
	)
}
