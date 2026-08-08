// Те же 6 тиров/названия/цвета, что и в боте (см. src/bot/texts/deck/deck.py:
// TIER_NAMES/TIER_EMOJI) — фиксированный список, дублировать через общий пакет с ботом
// для 6 записей избыточно. Живёт в config/, а не в constants/ — это визуальный баланс
// тиров (зеркало игровых чисел бота), не строка-идентификатор для ==/startswith.
export const TIER_INFO: Record<number, { name: string; color: string }> = {
	1000: { name: 'Обычный', color: '#9aa0a6' },
	2000: { name: 'Необычный', color: '#3fb950' },
	3000: { name: 'Редкий', color: '#3b82f6' },
	4000: { name: 'Эпический', color: '#a855f7' },
	5000: { name: 'Легендарный', color: '#f59e0b' },
	6000: { name: 'Мифический', color: '#ef4444' },
}
