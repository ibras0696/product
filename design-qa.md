# Design QA — «Паутина истории Чечни»

Status: passed
Date: 2026-07-18

## Source of truth

- Reference: latest 2048×1093 image attached by the user in the conversation.
- Implementation: `http://127.0.0.1:8080/`.
- Desktop capture: `frontend/references/implementation/chechnya-atlas-desktop.png`.
- Mobile capture: `frontend/references/implementation/chechnya-atlas-mobile.png`.

## Matched composition

- Fixed left editorial navigation with gold typography and project action.
- Interactive satellite relief clipped by the real Chechnya boundary.
- Visible settlements, selected-node glow, relation lines and map controls.
- Independent right-hand Nozhay-Yurt panel with topics, four related cards and six key dates.
- Four-section bottom navigation with the active gold state.
- Mobile layout preserves the same hierarchy without horizontal overflow.

## Verification

- Desktop visual comparison completed at the reference viewport, 2048×1093.
- Satellite/street basemaps, pan, zoom, selection, search and details flow remain interactive.
- Axe reports no serious or critical violations at 390px and 1440px.
- Format, ESLint, TypeScript, module boundaries, 38 unit tests and the production build pass.
