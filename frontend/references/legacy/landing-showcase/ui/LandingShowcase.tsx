import { useState, type ReactNode } from "react";

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
import "./landing-themes-new.css";

function initialStyle(): LandingStyleId {
  const fromUrl = new URLSearchParams(window.location.search).get("style");
  return isLandingStyleId(fromUrl) ? fromUrl : "signal";
}

interface LandingShowcaseProps {
  accountSlot?: ReactNode;
}

export function LandingShowcase({ accountSlot }: LandingShowcaseProps) {
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
      <a className="skip-link" href="#page-title">
        К содержанию
      </a>
      <nav className="site-nav" aria-label="Основная навигация">
        <a className="brand" href="#top" aria-label="Product Lab, наверх">
          PRODUCT/LAB
        </a>
        <div className="nav-links">
          <a href="#principles">Подход</a>
          <a href="#cases">Кейсы</a>
          <a href="/api/docs">API</a>
          {accountSlot}
        </div>
      </nav>
      <StyleSwitcher activeStyle={activeStyle} onChange={changeStyle} />
      <LandingContent selected={selected} />
    </main>
  );
}
