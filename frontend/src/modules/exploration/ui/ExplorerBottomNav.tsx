import {
  CompassIcon,
  HouseIcon,
  MagnifyingGlassIcon,
  StarIcon,
} from "@phosphor-icons/react";

const items = [
  { label: "Главная", href: "#atlas", icon: HouseIcon },
  { label: "Исследовать", href: "#atlas-map", icon: CompassIcon },
  { label: "Избранное", href: "#entity-panel-title", icon: StarIcon },
  { label: "Поиск", href: "#atlas-search", icon: MagnifyingGlassIcon },
] as const;

export function ExplorerBottomNav() {
  return (
    <nav className="hx-bottom-nav" aria-label="Основная навигация">
      {items.map((item, index) => {
        const Icon = item.icon;
        return (
          <a
            key={item.label}
            className={index === 0 ? "hx-bottom-nav-active" : undefined}
            href={item.href}
          >
            <Icon
              size={24}
              weight={index === 0 ? "fill" : "regular"}
              aria-hidden="true"
            />
            <span>{item.label}</span>
          </a>
        );
      })}
    </nav>
  );
}
