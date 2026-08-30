import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";

// Migrated from Create React App (react-scripts 5). Notes for anyone
// wiring up a deploy:
//   - dev server runs on :3000 to match the old `npm start` and the
//     backend's CORS allow-list (main.py: http://localhost:3000)
//   - build output goes to build/ (not Vite's default dist/) so existing
//     Vercel / static-host config keeps working without a change
//   - env vars are import.meta.env.VITE_* now, not process.env.REACT_APP_*
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 3000,
    open: true,
  },
  build: {
    outDir: "build",
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/setupTests.js",
    css: true,
  },
});
