import preact from "@preact/preset-vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [preact()],
  base: "/",
  build: {
    outDir: "dist",
  },
  server: {
    // Только для `npm run dev` вне Docker — в проде Caddy сам проксирует /api на сервис
    // api (см. Caddyfile), этот прокси тут не участвует.
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
