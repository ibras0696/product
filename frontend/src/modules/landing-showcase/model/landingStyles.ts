export const landingStyles = [
  {
    id: "signal",
    name: "Signal",
    note: "Swiss grid, clear hierarchy",
    dials: "5 / 3 / 5",
  },
  {
    id: "terminal",
    name: "Terminal",
    note: "Dark developer tool",
    dials: "6 / 4 / 7",
  },
  {
    id: "editorial",
    name: "Editorial",
    note: "Technology publication",
    dials: "7 / 3 / 3",
  },
  {
    id: "brutal",
    name: "Brutal",
    note: "Sharp startup energy",
    dials: "9 / 5 / 6",
  },
  {
    id: "cobalt",
    name: "Cobalt",
    note: "Geometric product studio",
    dials: "7 / 5 / 4",
  },
  {
    id: "glass",
    name: "Glass",
    note: "Cold translucent layers",
    dials: "8 / 6 / 3",
  },
  {
    id: "index",
    name: "Index",
    note: "Research lab clarity",
    dials: "6 / 2 / 6",
  },
  {
    id: "velocity",
    name: "Velocity",
    note: "Performance and motion",
    dials: "9 / 7 / 5",
  },
  {
    id: "forest",
    name: "Forest",
    note: "Calm responsible tech",
    dials: "5 / 3 / 4",
  },
  {
    id: "soft",
    name: "Soft",
    note: "Friendly consumer utility",
    dials: "6 / 4 / 4",
  },
] as const;

export type LandingStyleId = (typeof landingStyles)[number]["id"];

export function isLandingStyleId(
  value: string | null,
): value is LandingStyleId {
  return landingStyles.some((style) => style.id === value);
}
