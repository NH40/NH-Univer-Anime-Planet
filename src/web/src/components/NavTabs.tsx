import { LayoutGrid, Ticket, User } from "lucide-react";
import type { View } from "../types";

const TABS: { view: View; activeMatch: View[]; label: string; Icon: typeof User }[] = [
  { view: "collection", activeMatch: ["collection", "card"], label: "Коллекция", Icon: LayoutGrid },
  { view: "profile", activeMatch: ["profile"], label: "Профиль", Icon: User },
  { view: "battlepass", activeMatch: ["battlepass"], label: "Battle Pass", Icon: Ticket },
];

export function NavTabs({ view, onChange }: { view: View; onChange: (view: View) => void }) {
  return (
    <nav class="view-tabs">
      {TABS.map((tab) => {
        const active = tab.activeMatch.includes(view);
        return (
          <button
            key={tab.view}
            type="button"
            class={active ? "view-tab active" : "view-tab"}
            onClick={() => onChange(tab.view)}
          >
            <tab.Icon size={16} />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
