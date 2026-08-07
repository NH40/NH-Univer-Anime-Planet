import { Check, Gem, Lock, Sparkles, Ticket } from "lucide-react";

export type TileState = "locked" | "claimed" | "ready";

export function tileState(unlocked: boolean, claimed: boolean): TileState {
  if (!unlocked) return "locked";
  return claimed ? "claimed" : "ready";
}

// Награда не растёт с уровнем — на каждом уровне либо немного тикетов, либо немного пыли
// (см. CLAUDE.md, "Сезонный пасс"), никогда оба разом.
function RewardContent({ dust, tickets, coins }: { dust: number; tickets: number; coins: number }) {
  return (
    <span class="bp-tile-reward">
      {tickets > 0 ? (
        <>
          <Ticket size={16} />
          {tickets}
        </>
      ) : (
        <>
          <Sparkles size={16} />
          {dust}
        </>
      )}
      {coins > 0 && (
        <span class="bp-tile-coins">
          <Gem size={11} />
          {coins}
        </span>
      )}
    </span>
  );
}

export function BattlePassTile({
  dust,
  tickets,
  coins,
  state,
  premium,
  onClick,
}: {
  dust: number;
  tickets: number;
  coins: number;
  state: TileState;
  premium: boolean;
  onClick?: () => void;
}) {
  const cls = ["bp-tile", premium ? "bp-tile-premium" : "bp-tile-free", `bp-tile-${state}`].join(" ");
  return (
    <button type="button" class={cls} disabled={state !== "ready"} onClick={onClick}>
      {state === "locked" && <Lock size={16} />}
      {state === "claimed" && <Check size={18} />}
      {state === "ready" && <RewardContent dust={dust} tickets={tickets} coins={coins} />}
    </button>
  );
}
