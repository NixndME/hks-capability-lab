import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api and /health/ready to the FastAPI backend so the
// frontend never needs to know its own deployed origin. In production the
// backend serves the built frontend directly (see ../Containerfile) so no
// proxy is needed there.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8080",
      "/health": "http://127.0.0.1:8080",
      "/ready": "http://127.0.0.1:8080",
    },
  },
  build: {
    outDir: "dist",
  },
});
