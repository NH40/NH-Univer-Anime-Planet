import { useEffect, useMemo, useState } from "preact/hooks";
import {
  type CardStack,
  type Profile,
  type Universe,
  type UniverseProgress,
  fetchCollection,
  fetchProfile,
  fetchProgress,
  fetchUniverses,
} from "./api";
import { applyTelegramTheme, getWebApp } from "./telegram";

// Те же 6 тиров/названия/цвета, что и в боте (см. src/bot/texts/deck/deck.py:
// TIER_NAMES/TIER_EMOJI) — фиксированный список, дублировать через общий пакет
// с ботом для 6 записей избыточно.
const TIER_INFO: Record<number, { name: string; emoji: string }> = {
  1000: { name: "Обычный", emoji: "⚪" },
  2000: { name: "Необычный", emoji: "🟢" },
  3000: { name: "Редкий", emoji: "🔵" },
  4000: { name: "Эпический", emoji: "🟣" },
  5000: { name: "Легендарный", emoji: "🟠" },
  6000: { name: "Мифический", emoji: "🔴" },
};

type View = "collection" | "profile" | "card";

function initialView(): View {
  const params = new URLSearchParams(window.location.search);
  return params.get("view") === "profile" ? "profile" : "collection";
}

export function App() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [universes, setUniverses] = useState<Universe[]>([]);
  const [progress, setProgress] = useState<UniverseProgress[]>([]);
  const [selectedUniverse, setSelectedUniverse] = useState<string | null>(null);
  const [cards, setCards] = useState<CardStack[]>([]);
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState<number | "all">("all");
  const [view, setView] = useState<View>(initialView);
  const [selectedCard, setSelectedCard] = useState<CardStack | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    applyTelegramTheme();
    const webApp = getWebApp();
    webApp?.ready();
    webApp?.expand();

    Promise.all([fetchProfile(), fetchUniverses(), fetchProgress()])
      .then(([profileData, universesData, progressData]) => {
        setProfile(profileData);
        setUniverses(universesData);
        setProgress(progressData);
        if (universesData.length > 0) {
          setSelectedUniverse(universesData[0].code);
        }
      })
      .catch((err: unknown) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedUniverse) return;
    fetchCollection(selectedUniverse)
      .then(setCards)
      .catch((err: unknown) => setError(String(err)));
  }, [selectedUniverse]);

  // Нативная кнопка "Назад" Telegram — видна только на экране карточки, возвращает
  // в коллекцию. Работает поверх обычной on-page кнопки (та остаётся и как fallback
  // при открытии вне Telegram, например в обычном браузере при разработке).
  useEffect(() => {
    const webApp = getWebApp();
    if (!webApp) return;
    const onBack = () => setView("collection");
    if (view === "card") {
      webApp.BackButton.show();
      webApp.BackButton.onClick(onBack);
    } else {
      webApp.BackButton.hide();
    }
    return () => webApp.BackButton.offClick(onBack);
  }, [view]);

  const universeTitleByCode = useMemo(() => {
    const map = new Map<string, string>();
    for (const u of universes) map.set(u.code, u.title);
    return map;
  }, [universes]);

  const visibleCards = useMemo(() => {
    const query = search.trim().toLowerCase();
    return cards.filter((card) => {
      if (tierFilter !== "all" && card.base_ubp !== tierFilter) return false;
      if (query && !card.name.toLowerCase().includes(query)) return false;
      return true;
    });
  }, [cards, search, tierFilter]);

  function openCard(card: CardStack) {
    setSelectedCard(card);
    setView("card");
  }

  if (loading) {
    return <div class="screen center">Загрузка…</div>;
  }
  if (error) {
    return <div class="screen center error">{error}</div>;
  }

  return (
    <div class="screen">
      <header class="profile">
        <div class="profile-name">{profile?.display_name ?? "Игрок"}</div>
        <div class="profile-stats">
          <span>⭐ {profile?.ubp_season} UBP сезона</span>
          <span>🏆 {profile?.ubp_total} UBP всего</span>
        </div>
      </header>

      <nav class="view-tabs">
        <button type="button" class={view !== "profile" ? "view-tab active" : "view-tab"} onClick={() => setView("collection")}>
          📚 Коллекция
        </button>
        <button type="button" class={view === "profile" ? "view-tab active" : "view-tab"} onClick={() => setView("profile")}>
          👤 Профиль
        </button>
      </nav>

      {view === "profile" && <ProgressPage progress={progress} />}

      {view === "card" && selectedCard && (
        <CardPage
          card={selectedCard}
          universeTitle={universeTitleByCode.get(selectedUniverse ?? "") ?? ""}
          onBack={() => setView("collection")}
        />
      )}

      {view === "collection" &&
        (universes.length === 0 ? (
          <div class="empty">Пока нет ни одной карточки — крутите в боте!</div>
        ) : (
          <>
            <nav class="universe-tabs">
              {universes.map((universe) => (
                <button
                  key={universe.code}
                  type="button"
                  class={universe.code === selectedUniverse ? "tab active" : "tab"}
                  onClick={() => setSelectedUniverse(universe.code)}
                >
                  {universe.title}
                </button>
              ))}
            </nav>

            <div class="filters">
              <input
                class="search-input"
                type="search"
                placeholder="🔍 Поиск по имени…"
                value={search}
                onInput={(e) => setSearch((e.target as HTMLInputElement).value)}
              />
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
                      {info.emoji} {info.name}
                    </option>
                  ))}
              </select>
            </div>

            {visibleCards.length === 0 ? (
              <div class="empty">Ничего не найдено.</div>
            ) : (
              <div class="grid">
                {visibleCards.map((card) => (
                  <button
                    type="button"
                    class="card"
                    key={`${card.card_id}-${card.stars}`}
                    onClick={() => openCard(card)}
                  >
                    <img src={card.image_url} alt={card.name} loading="lazy" />
                    <div class="card-name">{card.name}</div>
                    <div class="card-meta">
                      {"★".repeat(card.stars)} · {card.base_ubp} UBP · x{card.quantity}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </>
        ))}
    </div>
  );
}

function ProgressPage({ progress }: { progress: UniverseProgress[] }) {
  if (progress.length === 0) {
    return <div class="empty">Пока нет ни одной карточки — крутите в боте!</div>;
  }
  return (
    <div class="progress-page">
      {progress.map((p) => (
        <div class="progress-row" key={p.code}>
          <div class="progress-row-header">
            <span class="progress-row-title">🌌 {p.title}</span>
            <span class="progress-row-count">
              {p.owned}/{p.total}
            </span>
          </div>
          <div class="progress-bar-track">
            <div class="progress-bar-fill" style={{ width: `${p.percent}%` }} />
          </div>
          <div class="progress-row-percent">{p.percent}%</div>
        </div>
      ))}
    </div>
  );
}

function CardPage({ card, universeTitle, onBack }: { card: CardStack; universeTitle: string; onBack: () => void }) {
  const tier = TIER_INFO[card.base_ubp];
  return (
    <div class="card-page">
      <button type="button" class="back-button" onClick={onBack}>
        ← Назад
      </button>
      <img class="card-page-image" src={card.image_url} alt={card.name} />
      <div class="card-page-body">
        <div class="card-page-row">
          <span class="card-page-label">🆔 ID</span>
          <span>{card.external_id}</span>
        </div>
        <div class="card-page-row">
          <span class="card-page-label">🎴 Персонаж</span>
          <span>{card.name}</span>
        </div>
        <div class="card-page-row">
          <span class="card-page-label">🌌 Вселенная</span>
          <span>{universeTitle}</span>
        </div>
        <div class="card-page-row">
          <span class="card-page-label">💠 Очки</span>
          <span>{card.base_ubp}</span>
        </div>
        {card.description && <p class="card-page-description">📖 {card.description}</p>}
        <div class="card-page-row">
          <span class="card-page-label">📦 Количество</span>
          <span>{card.quantity}</span>
        </div>
        {tier && (
          <div class="card-page-row">
            <span class="card-page-label">{tier.emoji} Ранг</span>
            <span>{tier.name}</span>
          </div>
        )}
        <div class="card-page-row">
          <span class="card-page-label">🌟 Звёзды</span>
          <span>{"🌟".repeat(card.stars)}</span>
        </div>
      </div>
    </div>
  );
}
