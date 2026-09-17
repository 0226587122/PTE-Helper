import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// In development the API runs separately; relative /api calls are proxied to it.
// On App Platform the same relative URLs are routed to the API service.
const apiTarget = process.env.VITE_API_PROXY ?? "http://localhost:8010";

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.VITE_PORT ?? 5174),
    strictPort: true,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
