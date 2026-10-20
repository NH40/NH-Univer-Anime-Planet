import { Check, Gift, Loader2, RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'preact/hooks'
import { type QuestsInfo, fetchQuests, questAction } from '../api'
import { Panel } from '../components/ui/Panel'
import { countdown, fmt, run, toast } from '../service/ui'

export function QuestsPage() {
	const [data, setData] = useState<QuestsInfo | null>(null)
	const [busy, setBusy] = useState(false)

	const load = () => fetchQuests().then(setData).catch((e) => toast(String(e.message ?? e), true))
	useEffect(() => {
		load()
	}, [])

	const act = async (action: string, slot?: number) => {
		setBusy(true)
		await run(() => questAction(action, slot))
		await load()
		setBusy(false)
	}

	if (!data) {
		return (
			<div class='empty'>
				<Loader2 size={20} class='spin' /> Загрузка…
			</div>
		)
	}
	const { bonus } = data
	const anyDone = data.slots.some((s) => s.done && !s.claimed)

	return (
		<>
			<div class='page-title'>Задания</div>

			<Panel title='Ежедневный бонус' gold>
				<div class='tgrid tgrid-5' style={{ gridTemplateColumns: 'repeat(7, 1fr)' }}>
					{bonus.rewards.map((r) => {
						const taken = r.day <= bonus.streak
						const next = r.day === bonus.streak + 1
						return (
							<div
								key={r.day}
								class='stat'
								style={{
									padding: '6px 2px',
									borderColor: next ? 'var(--gold)' : undefined,
									opacity: taken ? 0.55 : 1,
								}}
							>
								<div class='stat-label'>Д{r.day}</div>
								<div style={{ fontSize: 11, fontWeight: 800 }}>
									{taken ? <Check size={14} /> : `✨${r.dust}`}
								</div>
								{!taken && r.tickets > 0 && (
									<div style={{ fontSize: 11, fontWeight: 800 }}>🎫{r.tickets}</div>
								)}
							</div>
						)
					})}
				</div>
				<button
					type='button'
					class='btn btn-gold btn-block'
					style={{ marginTop: 10 }}
					disabled={busy || !bonus.claimable}
					onClick={() => act('bonus')}
				>
					<Gift size={16} />
					{bonus.claimable ? 'Забрать бонус' : `Следующий через ${countdown(bonus.next_in)}`}
				</button>
			</Panel>

			<Panel title='Задания дня'>
				{data.slots.map((s) => (
					<div class='list-row' key={s.slot} style={{ flexWrap: 'wrap' }}>
						<div class='list-main'>
							<div class='list-title' style={{ whiteSpace: 'normal' }}>
								{s.text}
							</div>
							<div class='list-sub'>
								{fmt(s.progress)}/{fmt(s.target)} · ✨{s.dust}
								{s.tickets ? ` · 🎫${s.tickets}` : ''}
							</div>
							<div class={s.done ? 'progress-thin done' : 'progress-thin'}>
								<div style={{ width: `${Math.min(100, (s.progress / s.target) * 100)}%` }} />
							</div>
						</div>
						{s.claimed ? (
							<span class='hint'>
								<Check size={16} />
							</span>
						) : s.done ? (
							<button
								type='button'
								class='btn btn-sm btn-gold'
								disabled={busy}
								onClick={() => act('claim', s.slot)}
							>
								Забрать
							</button>
						) : (
							<button
								type='button'
								class='btn btn-sm btn-ghost'
								disabled={busy || data.rerolls_left < 1}
								title='Заменить задание'
								onClick={() => act('reroll', s.slot)}
							>
								<RefreshCw size={14} />
							</button>
						)}
					</div>
				))}
				<div class='row' style={{ marginTop: 10 }}>
					<button
						type='button'
						class='btn'
						disabled={busy || !anyDone}
						onClick={() => act('claim-all')}
					>
						Забрать всё
					</button>
					<button
						type='button'
						class='btn btn-ghost'
						disabled={busy || !data.reroll_all}
						onClick={() => act('reroll-all')}
					>
						<RefreshCw size={14} /> Новый набор
					</button>
				</div>
				<div class='hint' style={{ marginTop: 6 }}>
					Замен осталось: {data.rerolls_left}
				</div>
			</Panel>
		</>
	)
}
