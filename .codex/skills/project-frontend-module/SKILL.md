---
name: project-frontend-module
description: Build or refactor React and TypeScript frontend functionality in this repository using isolated domain modules, public module APIs, mobile-first responsive design, accessible UI, TanStack Query, React Hook Form, Zod, and behavior tests. Use for every page, component, hook, feature, form, route, or frontend API integration.
---

# Project Frontend Module

1. Read the active platform contract in `.codex/config.toml` or `.claude/CLAUDE.md`.
2. Identify the owning domain module and the user-visible job of the change.
3. Load the design skill for visual work, React best-practices skill for implementation, and testing skill for behavior verification.
4. Keep app composition in `src/app`, business ownership in `src/modules/<domain>`, and domain-neutral primitives in `src/shared`.
5. Expose a minimal module `index.ts`; never deep-import another module's internals.
6. Wrap generated transport clients in module queries/mutations. Keep server state in TanStack Query and form state in React Hook Form.
7. Separate rendering from workflow orchestration. Avoid effect-driven state, giant components, and global stores used as shortcuts.
8. Design mobile-first at 360px, then verify 390, 768, 1280, and 1440px where tooling permits. Preserve keyboard use, focus, semantics, reduced motion, and 44px touch targets.
9. Test complete interactions and meaningful states, not each trivial component or helper.
10. Run types, lint, boundary checks, tests, build, responsive browser verification, and final diff review.

For a substantial screen, delegate independent visual/accessibility review and test-gap review. Subagents must receive the applicable instructions and selected skills.
