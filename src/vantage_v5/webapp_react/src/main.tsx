import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./styles.css";

function registerVantageServiceWorker() {
  const canRegister = "serviceWorker" in navigator;
  const isSecureContext =
    window.location.protocol === "https:" ||
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1";
  if (!canRegister || !isSecureContext) {
    return;
  }
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => undefined);
  });
}

registerVantageServiceWorker();

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
