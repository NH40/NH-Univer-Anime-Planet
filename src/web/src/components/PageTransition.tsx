import type { ComponentChildren } from "preact";
import { useEffect, useState } from "preact/hooks";

// Лёгкий fade+slide на смену вкладки — без анимационной библиотеки, чистый CSS-переход,
// перезапускается через `id` (см. styles.css: .page-transition/.page-transition-in).
export function PageTransition({ id, children }: { id: string; children: ComponentChildren }) {
  const [entered, setEntered] = useState(false);

  useEffect(() => {
    setEntered(false);
    const raf = requestAnimationFrame(() => setEntered(true));
    return () => cancelAnimationFrame(raf);
  }, [id]);

  return <div class={entered ? "page-transition page-transition-in" : "page-transition"}>{children}</div>;
}
