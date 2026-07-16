import type { LandingStyleId } from "../model/landingStyles";
import { landingStyles } from "../model/landingStyles";

interface StyleSwitcherProps {
  activeStyle: LandingStyleId;
  onChange: (style: LandingStyleId) => void;
}

export function StyleSwitcher({ activeStyle, onChange }: StyleSwitcherProps) {
  return (
    <section className="style-switcher" aria-labelledby="style-switcher-title">
      <div className="style-switcher-copy">
        <p id="style-switcher-title">10 дизайн-систем</p>
        <span>Выберите направление</span>
      </div>
      <div className="style-options" aria-label="Варианты дизайна">
        {landingStyles.map((style, index) => (
          <button
            className="style-option"
            data-active={style.id === activeStyle}
            key={style.id}
            onClick={() => {
              onChange(style.id);
            }}
            type="button"
            aria-pressed={style.id === activeStyle}
            title={`${style.note}. Динамика: ${style.dials}`}
          >
            <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
            {style.name}
          </button>
        ))}
      </div>
    </section>
  );
}
