import { Star, Trophy } from "lucide-react";
import type { Profile } from "../api";

export function Header({ profile }: { profile: Profile | null }) {
  return (
    <header class="app-header">
      <div class="app-header-name">{profile?.display_name ?? "Игрок"}</div>
      <div class="app-header-stats">
        <span class="stat-pill" title="UBP сезона">
          <Star size={14} />
          {profile?.ubp_season ?? 0}
        </span>
        <span class="stat-pill" title="UBP всего">
          <Trophy size={14} />
          {profile?.ubp_total ?? 0}
        </span>
      </div>
    </header>
  );
}
