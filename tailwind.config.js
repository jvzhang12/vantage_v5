/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/vantage_v5/webapp_react/**/*.{html,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        graphite: "#080A0C",
        "graphite-panel": "#101317",
        "graphite-panel-2": "#12161A",
        ivory: "#F3EFE6",
        "ivory-muted": "rgba(243,239,230,0.62)",
        cyan: "#7FE7F0",
        gold: "#E8C66A",
      },
      boxShadow: {
        vantage: "0 24px 80px rgba(0, 0, 0, 0.42)",
        "vantage-soft": "0 18px 48px rgba(0, 0, 0, 0.28)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
