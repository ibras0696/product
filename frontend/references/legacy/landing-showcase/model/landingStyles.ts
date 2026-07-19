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
  {
    id: "chrome",
    name: "Chrome",
    note: "Cold luxury product hardware",
    dials: "7 / 5 / 3",
  },
  {
    id: "bauhaus",
    name: "Bauhaus",
    note: "Geometric primary composition",
    dials: "9 / 4 / 5",
  },
  {
    id: "sumi",
    name: "Sumi",
    note: "Japanese restraint and rhythm",
    dials: "6 / 2 / 3",
  },
  {
    id: "nocturne",
    name: "Nocturne",
    note: "Cinematic dark direction",
    dials: "8 / 6 / 3",
  },
  {
    id: "kinetic",
    name: "Kinetic",
    note: "Sports editorial momentum",
    dials: "10 / 7 / 5",
  },
  {
    id: "orbit",
    name: "Orbit",
    note: "Spatial browser interface",
    dials: "9 / 6 / 4",
  },
  {
    id: "play",
    name: "Play",
    note: "Creative modular workspace",
    dials: "9 / 5 / 6",
  },
  {
    id: "ledger",
    name: "Ledger",
    note: "Financial editorial precision",
    dials: "6 / 3 / 7",
  },
  {
    id: "riviera",
    name: "Riviera",
    note: "Bold optimistic consumer brand",
    dials: "8 / 4 / 4",
  },
  {
    id: "industrial",
    name: "Industrial",
    note: "Engineered utilitarian system",
    dials: "7 / 3 / 7",
  },
] as const;

export type LandingStyleId = (typeof landingStyles)[number]["id"];

export function isLandingStyleId(
  value: string | null,
): value is LandingStyleId {
  return landingStyles.some((style) => style.id === value);
}
