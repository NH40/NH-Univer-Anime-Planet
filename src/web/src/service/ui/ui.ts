import { getWebApp } from '../../telegram'

// Мини-шина UI без библиотек: тосты и запрос «обнови валюты в шапке» после любого действия,
// меняющего баланс. Страницы не знают про Header — они просто зовут run().

type ToastListener = (text: string, isError: boolean) => void
const toastListeners = new Set<ToastListener>()
const refreshListeners = new Set<() => void>()

export function onToast(fn: ToastListener): () => void {
	toastListeners.add(fn)
	return () => toastListeners.delete(fn)
}

export function onRefresh(fn: () => void): () => void {
	refreshListeners.add(fn)
	return () => refreshListeners.delete(fn)
}

export function toast(text: string, isError = false): void {
	for (const fn of toastListeners) fn(text, isError)
	getWebApp()?.HapticFeedback?.notificationOccurred(isError ? 'error' : 'success')
}

export function requestRefresh(): void {
	for (const fn of refreshListeners) fn()
}

/** Выполнить действие: тост с `message` (или ошибкой), затем обновить шапку. */
export async function run<T>(action: () => Promise<T>): Promise<T | null> {
	try {
		const result = await action()
		const message = (result as { message?: string } | null)?.message
		if (message) toast(message)
		requestRefresh()
		return result
	} catch (err) {
		toast(err instanceof Error ? err.message : String(err), true)
		return null
	}
}

export const fmt = (n: number | null | undefined): string => (n ?? 0).toLocaleString('ru-RU')

export function countdown(seconds: number | null | undefined): string {
	if (!seconds || seconds <= 0) return '0:00'
	const h = Math.floor(seconds / 3600)
	const m = Math.floor((seconds % 3600) / 60)
	const s = Math.floor(seconds % 60)
	const mm = String(m).padStart(h ? 2 : 1, '0')
	return `${h ? `${h}:` : ''}${mm}:${String(s).padStart(2, '0')}`
}
