/// <reference types="vite/client" />

import { describe, expect, it } from "vitest";
import reactIndexHtml from "../index.html?raw";
import viteConfigSource from "../../../../vite.config.ts?raw";

describe("React frontend entrypoints", () => {
  it("keeps Vite pointed at the React source and generated static bundle path", () => {
    expect(viteConfigSource).toContain('root: "src/vantage_v5/webapp_react"');
    expect(viteConfigSource).toContain('base: "/static/generated/"');
    expect(viteConfigSource).toContain('outDir: "../webapp/generated"');
    expect(viteConfigSource).toContain('entryFileNames: "assets/app.js"');
    expect(viteConfigSource).toContain('chunkFileNames: "assets/[name].js"');
    expect(viteConfigSource).toContain('assetFileNames: "assets/[name][extname]"');
  });

  it("uses the React mount point and Vite dev module in source HTML", () => {
    expect(reactIndexHtml).toContain('<div id="root"></div>');
    expect(reactIndexHtml).toContain('src="/src/main.tsx"');
    expect(reactIndexHtml).not.toContain("/static/app.js");
    expect(reactIndexHtml).not.toContain("/static/styles.css");
  });
});
