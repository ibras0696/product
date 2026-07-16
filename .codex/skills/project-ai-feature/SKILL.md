---
name: project-ai-feature
description: Implement or review AI-powered product functionality in this repository, including LLM providers, prompts, structured output, streaming, background inference, retrieval, embeddings, evaluations, token budgets, retries, and safety. Use for every AI feature or provider integration.
---

# Project AI Feature

1. Read the active platform contract in `.codex/config.toml` or `.claude/CLAUDE.md`.
2. Define the user outcome, acceptable failure, latency budget, cost/token budget, data sensitivity, and deterministic fallback before choosing a provider API.
3. Keep provider SDKs in infrastructure adapters behind a narrow application port. Domain and UI code never call a provider directly.
4. Version prompts or prompt templates as code. Separate trusted instructions from untrusted user/retrieved content.
5. Prefer structured typed output and validate it. Treat model output as untrusted external input.
6. Add timeouts, cancellation, bounded retries, observability, and idempotency for queued work. Do not hold DB transactions during inference.
7. Never send secrets or unnecessary personal data to a provider. Document retention and redaction assumptions.
8. Test orchestration with deterministic fakes. Keep paid/live-provider tests opt-in. Add evaluation cases for behavior that unit tests cannot capture.
9. Expose clear pending, partial, retry, and failure states in the UI.
10. Run the project quality gate and report model-dependent uncertainty honestly.

For substantial AI work, delegate independent prompt/evaluation and security/privacy reviews. Give those subagents this skill and bounded read-only scopes.
