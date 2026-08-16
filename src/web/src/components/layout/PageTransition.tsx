import type { ComponentChildren } from 'preact'

// Лёгкий fade+slide на смену вкладки — CSS @keyframes-анимация (см. styles.css:
// .page-transition), проигрывается сама при монтировании узла, `key={id}` пересоздаёт узел
// при смене вкладки, чтобы анимация перезапускалась. Раньше держали на requestAnimationFrame
// (переключить класс через кадр отрисовки, чтобы transition сыграл) — в Telegram Desktop
// Mini App WebView rAF иногда не срабатывал вовсе, и контент навсегда оставался at
// opacity: 0 — экран выглядел пустым при переключении вкладок (см. CLAUDE.md, баг
// "пустой экран при переключении вкладок", 2026-08-16). CSS-анимация не зависит от JS-таймингов.
export function PageTransition({ id, children }: { id: string; children: ComponentChildren }) {
	return (
		<div class='page-transition' key={id}>
			{children}
		</div>
	)
}
