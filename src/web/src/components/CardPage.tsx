import { ArrowLeft, BookOpen, Fingerprint, Gem, Globe, Package, Star, UserRound } from "lucide-react";
import type { CardStack } from "../api";
import { TIER_INFO } from "../constants";

export function CardPage({
  card,
  universeTitle,
  onBack,
}: {
  card: CardStack;
  universeTitle: string;
  onBack: () => void;
}) {
  const tier = TIER_INFO[card.base_ubp];
  return (
    <div class="card-page">
      <button type="button" class="back-button" onClick={onBack}>
        <ArrowLeft size={16} /> Назад
      </button>
      <img class="card-page-image" src={card.image_url} alt={card.name} />
      <div class="card-page-body">
        <div class="card-page-row">
          <span class="card-page-label">
            <Fingerprint size={15} /> ID
          </span>
          <span>{card.external_id}</span>
        </div>
        <div class="card-page-row">
          <span class="card-page-label">
            <UserRound size={15} /> Персонаж
          </span>
          <span>{card.name}</span>
        </div>
        <div class="card-page-row">
          <span class="card-page-label">
            <Globe size={15} /> Вселенная
          </span>
          <span>{universeTitle}</span>
        </div>
        <div class="card-page-row">
          <span class="card-page-label">
            <Gem size={15} /> Очки
          </span>
          <span>{card.base_ubp}</span>
        </div>
        {card.description && (
          <p class="card-page-description">
            <BookOpen size={14} /> {card.description}
          </p>
        )}
        <div class="card-page-row">
          <span class="card-page-label">
            <Package size={15} /> Количество
          </span>
          <span>{card.quantity}</span>
        </div>
        {tier && (
          <div class="card-page-row">
            <span class="card-page-label">
              <span class="tier-dot" style={{ background: tier.color }} /> Ранг
            </span>
            <span>{tier.name}</span>
          </div>
        )}
        <div class="card-page-row">
          <span class="card-page-label">
            <Star size={15} /> Звёзды
          </span>
          <span class="star-row">
            {Array.from({ length: card.stars }).map((_, i) => (
              <Star key={i} size={14} fill="currentColor" />
            ))}
          </span>
        </div>
      </div>
    </div>
  );
}
