import { useState } from "react";

import {
  isLandingStyleId,
  landingStyles,
  type LandingStyleId,
} from "../model/landingStyles";
import { LandingContent } from "./LandingContent";
import { StyleSwitcher } from "./StyleSwitcher";
import "./landing-content.css";
import "./landing-showcase.css";
import "./landing-themes.css";

function initialStyle(): LandingStyleId {
  const fromUrl = new URLSearchParams(window.location.search).get("style");
  return isLandingStyleId(fromUrl) ? fromUrl : "signal";
}

export function LandingShowcase() {
  const [activeStyle, setActiveStyle] = useState<LandingStyleId>(initialStyle);
  const selected = landingStyles.find((style) => style.id === activeStyle);

  function changeStyle(style: LandingStyleId) {
    setActiveStyle(style);
    const url = new URL(window.location.href);
    url.searchParams.set("style", style);
    window.history.replaceState({}, "", url);
  }

  return (
    <main className="showcase" data-theme={activeStyle}>
      <nav className="site-nav" aria-label="Основная навигация">
        <a className="brand" href="#top" aria-label="Product Lab, наверх">
          PRODUCT/LAB
        </a>
        <div className="nav-links">
          <a href="#principles">Подход</a>
          <a href="#cases">Кейсы</a>
          <a href="/api/docs">API</a>
        </div>
      </nav>
      <StyleSwitcher activeStyle={activeStyle} onChange={changeStyle} />
      <LandingContent selected={selected} />
    </main>
  );
}
