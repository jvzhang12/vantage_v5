import { defineConfig, type UserConfig } from "vite";
import react from "@vitejs/plugin-react";

const config = {
  root: "src/vantage_v5/webapp_react",
  base: "/static/generated/",
  plugins: [react()],
  build: {
    outDir: "../webapp/generated",
    emptyOutDir: true,
    sourcemap: true,
    rollupOptions: {
      output: {
        entryFileNames: "assets/app.js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    css: true,
  },
};

export default defineConfig(config as UserConfig);
