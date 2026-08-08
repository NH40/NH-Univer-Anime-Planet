import { AlertTriangle, Loader2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'preact/hooks'
import { Route, Switch, useLocation } from 'wouter'
import type { CardStack } from './api'
import { Header } from './components/layout/Header'
import { NavTabs } from './components/layout/NavTabs'
import { PageTransition } from './components/layout/PageTransition'
import { EVENTS_TAB_CODE, ROUTE_BATTLE_PASS, ROUTE_COLLECTION, ROUTE_PROFILE } from './constants'
import { useAppData } from './hooks/useAppData'
import { useBattlePass } from './hooks/useBattlePass'
import { BattlePassPage } from './pages/BattlePassPage'
import { CardPage } from './pages/CardPage'
import { CollectionPage } from './pages/CollectionPage'
import { ProgressPage } from './pages/ProgressPage'
import { applyTelegramTheme, getWebApp } from './telegram'

export function App() {
	const [location] = useLocation()
	const [selectedCard, setSelectedCard] = useState<CardStack | null>(null)
	const [appError, setAppError] = useState<string | null>(null)

	const {
		profile,
		universes,
		progress,
		selectedUniverse,
		setSelectedUniverse,
		cards,
		loading,
		error,
	} = useAppData()
	const battlePass = useBattlePass(location === ROUTE_BATTLE_PASS, setAppError)

	useEffect(() => {
		applyTelegramTheme()
		const webApp = getWebApp()
		webApp?.ready()
		webApp?.expand()
	}, [])

	// Карточка — оверлей поверх текущего маршрута, а не отдельный роут (нет отдельного
	// API "карточка по id", она берётся из уже загруженного cards). Смена маршрута
	// (клик по NavTabs) закрывает её сама собой, открытие карточки маршрут не меняет.
	useEffect(() => {
		setSelectedCard(null)
	}, [location])

	// Нативная кнопка "Назад" Telegram — видна только когда открыта карточка, закрывает
	// её. Работает поверх обычной on-page кнопки (та остаётся и как fallback при открытии
	// вне Telegram, например в обычном браузере при разработке).
	useEffect(() => {
		const webApp = getWebApp()
		if (!webApp) return
		const onBack = () => setSelectedCard(null)
		if (selectedCard) {
			webApp.BackButton.show()
			webApp.BackButton.onClick(onBack)
		} else {
			webApp.BackButton.hide()
		}
		return () => webApp.BackButton.offClick(onBack)
	}, [selectedCard])

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

	const transitionId = selectedCard
		? `card-${selectedCard.card_id}-${selectedCard.stars}`
		: location

	return (
		<div class='screen'>
			<Header profile={profile} />
			<NavTabs />

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
					/>
				) : (
					<Switch>
						<Route path={ROUTE_PROFILE}>
							<ProgressPage progress={progress} />
						</Route>
						<Route path={ROUTE_BATTLE_PASS}>
							<BattlePassPage
								data={battlePass.page}
								loading={battlePass.loading}
								claiming={battlePass.claiming}
								onPrev={battlePass.prevPage}
								onNext={battlePass.nextPage}
								onClaim={battlePass.claim}
							/>
						</Route>
						<Route path={ROUTE_COLLECTION}>
							<CollectionPage
								universes={universes}
								selectedUniverse={selectedUniverse}
								onSelectUniverse={setSelectedUniverse}
								cards={cards}
								onOpenCard={setSelectedCard}
							/>
						</Route>
					</Switch>
				)}
			</PageTransition>
		</div>
	)
}
