// Псевдо-код вселенной для вкладки "Ивенты" — агрегирует карточки СРАЗУ из всех
// ивентовых вселенных (см. CLAUDE.md, "Ивенты"), а не из одной конкретной, поэтому не
// берётся из /api/universes (та отдаёт только обычные вселенные) и бьёт в отдельный
// эндпоинт /api/collection/events.
export const EVENTS_TAB_CODE = '__events__'

// Пути маршрутов wouter — сравниваются в NavTabs (подсветка активной вкладки по
// location) и используются в Link/navigate, тот же принцип, что CB_ в боте: значение
// задаётся один раз здесь, а не дублируется строковым литералом в App.tsx/NavTabs.tsx.
export const ROUTE_COLLECTION = '/'
export const ROUTE_PROFILE = '/profile'
export const ROUTE_BATTLE_PASS = '/battlepass'
