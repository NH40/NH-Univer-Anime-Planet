import { useEffect, useState } from "preact/hooks";
import { type CardStack, type Profile, type Universe, fetchCollection, fetchProfile, fetchUniverses } from "./api";
import { applyTelegramTheme, getWebApp } from "./telegram";

export function App() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [universes, setUniverses] = useState<Universe[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [cards, setCards] = useState<CardStack[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    applyTelegramTheme();
    const webApp = getWebApp();
    webApp?.ready();
    webApp?.expand();

    Promise.all([fetchProfile(), fetchUniverses()])
      .then(([profileData, universesData]) => {
        setProfile(profileData);
        setUniverses(universesData);
        if (universesData.length > 0) {
          setSelected(universesData[0].code);
        }
      })
      .catch((err: unknown) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    fetchCollection(selected)
      .then(setCards)
      .catch((err: unknown) => setError(String(err)));
  }, [selected]);

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

      {universes.length === 0 ? (
        <div class="empty">Пока нет ни одной карточки — крутите в боте!</div>
      ) : (
        <>
          <nav class="universe-tabs">
            {universes.map((universe) => (
              <button
                key={universe.code}
                type="button"
                class={universe.code === selected ? "tab active" : "tab"}
                onClick={() => setSelected(universe.code)}
              >
                {universe.title}
              </button>
            ))}
          </nav>

          <div class="grid">
            {cards.map((card) => (
              <div class="card" key={`${card.card_id}-${card.stars}`}>
                <img src={card.image_url} alt={card.name} loading="lazy" />
                <div class="card-name">{card.name}</div>
                <div class="card-meta">
                  {"★".repeat(card.stars)} · {card.base_ubp} UBP · x{card.quantity}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
