import { AlertTriangle, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "preact/hooks";
import type { CardStack } from "./api";
import { BattlePassPage } from "./components/BattlePassPage";
import { CardPage } from "./components/CardPage";
import { CollectionPage } from "./components/CollectionPage";
import { Header } from "./components/Header";
import { NavTabs } from "./components/NavTabs";
import { PageTransition } from "./components/PageTransition";
import { ProgressPage } from "./components/ProgressPage";
import { EVENTS_TAB_CODE } from "./constants";
import { useAppData } from "./hooks/useAppData";
import { useBattlePass } from "./hooks/useBattlePass";
import { applyTelegramTheme, getWebApp } from "./telegram";
import type { View } from "./types";

function initialView(): View {
  const params = new URLSearchParams(window.location.search);
  const view = params.get("view");
  if (view === "profile" || view === "battlepass") return view;
  return "collection";
}

export function App() {
  const [view, setView] = useState<View>(initialView);
  const [selectedCard, setSelectedCard] = useState<CardStack | null>(null);
  const [appError, setAppError] = useState<string | null>(null);

  const { profile, universes, progress, selectedUniverse, setSelectedUniverse, cards, loading, error } = useAppData();
  const battlePass = useBattlePass(view === "battlepass", setAppError);

  useEffect(() => {
    applyTelegramTheme();
    const webApp = getWebApp();
    webApp?.ready();
    webApp?.expand();
  }, []);

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

  function openCard(card: CardStack) {
    setSelectedCard(card);
    setView("card");
  }

  if (loading) {
    return (
      <div class="screen center">
        <Loader2 size={22} class="spin" /> Загрузка…
      </div>
    );
  }
  const fatalError = error ?? appError;
  if (fatalError) {
    return (
      <div class="screen center error">
        <AlertTriangle size={20} /> {fatalError}
      </div>
    );
  }

  return (
    <div class="screen">
      <Header profile={profile} />
      <NavTabs view={view} onChange={setView} />

      <PageTransition id={view}>
        {view === "profile" && <ProgressPage progress={progress} />}

        {view === "battlepass" && (
          <BattlePassPage
            data={battlePass.page}
            loading={battlePass.loading}
            claiming={battlePass.claiming}
            onPrev={battlePass.prevPage}
            onNext={battlePass.nextPage}
            onClaim={battlePass.claim}
          />
        )}

        {view === "card" && selectedCard && (
          <CardPage
            card={selectedCard}
            universeTitle={
              selectedUniverse === EVENTS_TAB_CODE ? "Ивент" : universeTitleByCode.get(selectedUniverse ?? "") ?? ""
            }
            onBack={() => setView("collection")}
          />
        )}

        {view === "collection" && (
          <CollectionPage
            universes={universes}
            selectedUniverse={selectedUniverse}
            onSelectUniverse={setSelectedUniverse}
            cards={cards}
            onOpenCard={openCard}
          />
        )}
      </PageTransition>
    </div>
  );
}
