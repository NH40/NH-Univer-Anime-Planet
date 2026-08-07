import { useEffect, useState } from "preact/hooks";
import {
  type CardStack,
  type Profile,
  type Universe,
  type UniverseProgress,
  fetchCollection,
  fetchEventCollection,
  fetchProfile,
  fetchProgress,
  fetchUniverses,
} from "../api";
import { EVENTS_TAB_CODE } from "../constants";

// Собирает данные, нужные для первого экрана (профиль/список вселенных/прогресс
// коллекции) плюс карточки текущей выбранной вселенной — общее состояние для
// Header/CollectionPage/ProgressPage, поэтому живёт одним хуком, а не размазано по App.
export function useAppData() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [universes, setUniverses] = useState<Universe[]>([]);
  const [progress, setProgress] = useState<UniverseProgress[]>([]);
  const [selectedUniverse, setSelectedUniverse] = useState<string | null>(null);
  const [cards, setCards] = useState<CardStack[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
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
    const fetcher = selectedUniverse === EVENTS_TAB_CODE ? fetchEventCollection() : fetchCollection(selectedUniverse);
    fetcher.then(setCards).catch((err: unknown) => setError(String(err)));
  }, [selectedUniverse]);

  return { profile, universes, progress, selectedUniverse, setSelectedUniverse, cards, loading, error };
}
