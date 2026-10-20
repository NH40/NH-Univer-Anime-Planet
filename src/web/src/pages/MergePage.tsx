import { Combine, Sparkles } from 'lucide-react'
import { useState } from 'preact/hooks'
import { Link } from 'wouter'
import { type Universe, distill, mergeAll } from '../api'
import { Panel } from '../components/ui/Panel'
import { ROUTE_COLLECTION } from '../constants'
import { run } from '../service/ui'

/** Массовые слияния/распыление. Точечные действия — на экране карты в коллекции. */
export function MergePage({ universes }: { universes: Universe[] }) {
	const [universe, setUniverse] = useState(universes[0]?.code ?? '')
	const [busy, setBusy] = useState(false)
	const [confirm, setConfirm] = useState<null | 'dups' | 'all'>(null)

	const act = async (action: () => Promise<unknown>) => {
		setBusy(true)
		setConfirm(null)
		await run(action)
		setBusy(false)
	}

	return (
		<>
			<div class='page-title'>Слияния и распыление</div>
			<div class='hint'>
				Чтобы слить или распылить конкретную карту — открой её в{' '}
				<Link href={ROUTE_COLLECTION} style={{ color: '#7fd4ff' }}>
					коллекции
				</Link>
				.
			</div>

			<Panel title='Слить всё'>
				<div class='hint'>
					Сливает все стопки выбранной вселенной (по 5 копий) до ★5. UBP за каждое слияние
					начисляется как обычно.
				</div>
				<div class='chips' style={{ marginTop: 10 }}>
					{universes.map((u) => (
						<button
							key={u.code}
							type='button'
							class={u.code === universe ? 'chip active' : 'chip'}
							onClick={() => setUniverse(u.code)}
						>
							{u.title}
						</button>
					))}
				</div>
				<button
					type='button'
					class='btn btn-big'
					style={{ marginTop: 10 }}
					disabled={busy || !universe}
					onClick={() => act(() => mergeAll(universe))}
				>
					<Combine size={18} /> Слить всё до макс.
				</button>
			</Panel>

			<Panel title='Распыление' gold>
				<div class='hint'>
					По всей коллекции, все вселенные и ивент-карты. Небесные и божественные не
					распыляются. Действие необратимо.
				</div>
				<div class='col' style={{ marginTop: 10 }}>
					<button
						type='button'
						class='btn'
						disabled={busy}
						onClick={() => setConfirm('dups')}
					>
						<Sparkles size={16} /> Все повторки (оставить по 1)
					</button>
					<button
						type='button'
						class='btn btn-danger'
						disabled={busy}
						onClick={() => setConfirm('all')}
					>
						Распылить всю коллекцию
					</button>
				</div>
				{confirm && (
					<div class='col' style={{ marginTop: 12 }}>
						<div style={{ fontWeight: 800 }}>
							{confirm === 'dups'
								? 'Распылить все повторки во всей коллекции?'
								: 'Распылить ВСЕ карты коллекции? Их не вернуть.'}
						</div>
						<div class='row'>
							<button
								type='button'
								class='btn btn-danger'
								onClick={() =>
									act(() => distill(confirm === 'dups' ? 'owned_duplicates' : 'owned_all'))
								}
							>
								Да
							</button>
							<button type='button' class='btn btn-ghost' onClick={() => setConfirm(null)}>
								Отмена
							</button>
						</div>
					</div>
				)}
			</Panel>
		</>
	)
}
