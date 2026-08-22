import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The built SPA is served by the FastAPI app in `backend/app/main.py`, which
// mounts this directory at `/`. Keeping the output inside `backend/` means a
// single Render service ships both the API and the frontend.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "backend/static",
    emptyOutDir: true,
  },
  server: {
    // `npm run dev` serves the SPA on 5173 and forwards API calls to the
    // FastAPI dev server, so the frontend uses same-origin `/api/*` paths in
    // development exactly as it does in production.
    proxy: {
      "/api": {
        target: process.env.VITE_DEV_API_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
