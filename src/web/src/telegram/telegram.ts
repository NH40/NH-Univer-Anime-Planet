// Тонкая обёртка над window.Telegram.WebApp — единственный источник initData (авторизация,
// см. src/api/auth.py) и темы оформления.

export interface TelegramWebApp {
	initData: string
	initDataUnsafe: Record<string, unknown>
	colorScheme: 'light' | 'dark'
	themeParams: Record<string, string>
	ready: () => void
	expand: () => void
	close: () => void
	BackButton: {
		show: () => void
		hide: () => void
		onClick: (cb: () => void) => void
		offClick: (cb: () => void) => void
	}
}

declare global {
	interface Window {
		Telegram?: { WebApp: TelegramWebApp }
	}
}

export function getWebApp(): TelegramWebApp | null {
	return window.Telegram?.WebApp ?? null
}

export function getInitData(): string {
	return getWebApp()?.initData ?? ''
}

// Telegram НЕ проставляет CSS-переменные темы сам — читаем themeParams и выставляем их
// вручную, чтобы styles.css мог использовать var(--tg-theme-*, fallback).
export function applyTelegramTheme(): void {
	const webApp = getWebApp()
	if (!webApp) return

	const root = document.documentElement
	for (const [key, value] of Object.entries(webApp.themeParams)) {
		root.style.setProperty(`--tg-theme-${key.replace(/_/g, '-')}`, value)
	}
	root.dataset.colorScheme = webApp.colorScheme
}
