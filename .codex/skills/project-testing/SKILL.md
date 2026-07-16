---
name: project-testing
description: Design, add, repair, or review tests for this repository. Use whenever behavior changes, a bug is fixed, tests are requested, coverage is discussed, or an agent is about to claim a feature complete. Enforces behavior-oriented tests across multiple cooperating functions instead of one trivial test per function.
---

# Project Testing

## Choose the behavior

Write down the observable behavior, important invariant, relevant boundary, and failure being protected. A test may exercise many functions and make several related assertions when they prove that one behavior.

## Choose the lowest sufficient level

- Domain: invariants and transitions without frameworks.
- Application: complete use case, transaction, ports, and events.
- Integration: real database/cache/queue semantics.
- API/component: transport, validation, wiring, and visible result.
- E2E: a small number of critical user workflows.

Do not replace lower-level behavioral coverage with a large E2E suite.

## Test doubles

Mock only true outbound boundaries. Prefer state-based fakes over mocks that reproduce implementation call order. Never mock the subject under test or repository behavior in a test whose purpose is persistence correctness.

## Required scenarios

For an important capability, consider the happy path, main invariant/boundary, meaningful failure, authorization, retry/idempotency, and regression risk. Include only scenarios that protect real behavior.

## Reject weak tests

Reject arbitrary sleeps, ordering dependencies, giant snapshots, tautological assertions, tests of trivial getters, private-method tests, and coverage-only additions.

Run the narrow suite first, then the proportional broader gate. For a broad change, delegate a read-only test-gap review and reconcile it with the implementation before completion.
