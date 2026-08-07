import { PartyPopper, Search, Star } from "lucide-react";
import { useMemo, useState } from "preact/hooks";
import type { CardStack, Universe } from "../api";
import { EVENTS_TAB_CODE, TIER_INFO } from "../constants";

export function CollectionPage({
  universes,
  selectedUniverse,
  onSelectUniverse,
  cards,
  onOpenCard,
}: {
  universes: Universe[];
  selectedUniverse: string | null;
  onSelectUniverse: (code: string) => void;
  cards: CardStack[];
  onOpenCard: (card: CardStack) => void;
}) {
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState<number | "all">("all");

  const visibleCards = useMemo(() => {
    const query = search.trim().toLowerCase();
    return cards.filter((card) => {
      if (tierFilter !== "all" && card.base_ubp !== tierFilter) return false;
      if (query && !card.name.toLowerCase().includes(query)) return false;
      return true;
    });
  }, [cards, search, tierFilter]);

  return (
    <>
      <nav class="universe-tabs">
        {universes.map((universe) => (
          <button
            key={universe.code}
            type="button"
            class={universe.code === selectedUniverse ? "tab active" : "tab"}
            onClick={() => onSelectUniverse(universe.code)}
          >
            {universe.title}
          </button>
        ))}
        <button
          type="button"
          class={selectedUniverse === EVENTS_TAB_CODE ? "tab active" : "tab"}
          onClick={() => onSelectUniverse(EVENTS_TAB_CODE)}
        >
          <PartyPopper size={14} /> Ивенты
        </button>
      </nav>

      {selectedUniverse === null ? (
        <div class="empty">Пока нет ни одной карточки — крутите в боте!</div>
      ) : (
        <>
          <div class="filters">
            <div class="search-input-wrap">
              <Search size={15} class="search-input-icon" />
              <input
                class="search-input"
                type="search"
                placeholder="Поиск по имени…"
                value={search}
                onInput={(e) => setSearch((e.target as HTMLInputElement).value)}
              />
            </div>
            <select
              class="tier-select"
              value={String(tierFilter)}
              onChange={(e) => {
                const value = (e.target as HTMLSelectElement).value;
                setTierFilter(value === "all" ? "all" : Number(value));
              }}
            >
              <option value="all">Все тиры</option>
              {Object.entries(TIER_INFO)
                .sort(([a], [b]) => Number(b) - Number(a))
                .map(([ubp, info]) => (
                  <option key={ubp} value={ubp}>
                    {info.name}
                  </option>
                ))}
            </select>
          </div>

          {visibleCards.length === 0 ? (
            <div class="empty">Ничего не найдено.</div>
          ) : (
            <div class="grid">
              {visibleCards.map((card) => {
                const tier = TIER_INFO[card.base_ubp];
                return (
                  <button
                    type="button"
                    class="card"
                    key={`${card.card_id}-${card.stars}`}
                    onClick={() => onOpenCard(card)}
                  >
                    {tier && <span class="card-tier-dot" style={{ background: tier.color }} />}
                    <img src={card.image_url} alt={card.name} loading="lazy" />
                    <div class="card-name">{card.name}</div>
                    <div class="card-meta">
                      <span class="card-meta-stars">
                        <Star size={11} fill="currentColor" /> {card.stars}
                      </span>
                      <span>{card.base_ubp} UBP</span>
                      <span>×{card.quantity}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </>
      )}
    </>
  );
}
