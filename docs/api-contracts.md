# API contracts

Status: binding baseline for backend, frontend, tests, Claude Code, and Codex.

This document defines the stable rules for communication between the React frontend and FastAPI backend. Product-specific resources are added only after the hackathon case is known. Unknown business contracts must not be invented in advance.

## 1. Sources of truth

The contract has three synchronized representations:

1. This document owns cross-cutting policy and explicit decisions.
2. FastAPI Pydantic schemas and generated OpenAPI own the executable HTTP shape.
3. The generated TypeScript client owns transport types on the frontend.

A change is incomplete if these representations disagree. Backend and frontend changes for one contract must land together or remain backward compatible during a documented transition.

Backend owns HTTP semantics, validation, authentication, authorization, and error codes. Frontend must not guess fields, statuses, permissions, defaults, or undocumented error behavior.

## 2. General HTTP contract

### 2.1 Transport

- Public application endpoints live under `/api`.
- JSON uses UTF-8 and `application/json`.
- Wire field names use `snake_case`; generated frontend types preserve the wire contract.
- Identifiers are opaque strings. UUID format may be used by the backend but clients must not derive meaning from it.
- Timestamps use ISO 8601 UTC with a `Z` suffix.
- Optional means the field may be absent. Nullable means the field may be present with `null`. These are not interchangeable.
- A list endpoint must be bounded. Its pagination contract is defined with the endpoint, not assumed by the frontend.
- API versioning is not added until a real compatibility boundary exists. A breaking contract requires an explicit migration or a versioned endpoint.

### 2.2 Response envelope

Every JSON application endpoint returns `ApiResponse[T]`:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "meta": {
    "request_id": "opaque-request-id"
  }
}
```

Failure response:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "stable_machine_code",
    "message": "Safe user-facing message",
    "details": null
  },
  "meta": {
    "request_id": "opaque-request-id"
  }
}
```

Invariants:

- `ok=true` means `error=null`.
- `ok=false` means `data=null` and `error` is present.
- `error.code` is stable and drives frontend behavior.
- `error.message` is safe to display but must not be parsed.
- `error.details` contains structured validation context only and never secrets, stack traces, SQL, tokens, or internal identifiers.
- `meta.request_id` matches the `X-Request-ID` response header when available.
- A successful operation with no resource result returns HTTP 200 with `data: null`; it does not use a bodyless 204 response.

### 2.3 Status and error mapping

| HTTP | Meaning                                        | Baseline code         |
| ---- | ---------------------------------------------- | --------------------- |
| 400  | Request is semantically invalid                | `bad_request`         |
| 401  | Authentication is missing or invalid           | `unauthorized`        |
| 403  | Identity is known but action is not allowed    | `forbidden`           |
| 404  | Resource is not visible or does not exist      | `not_found`           |
| 409  | State conflicts with the requested transition  | `conflict`            |
| 422  | Request shape or field validation failed       | `validation_error`    |
| 429  | A bounded rate limit was exceeded              | `rate_limited`        |
| 500  | Unexpected server failure                      | `internal_error`      |
| 503  | Required dependency is temporarily unavailable | `service_unavailable` |

FastAPI validation errors and unexpected errors must be normalized into the same envelope before feature endpoints are released. The frontend handles known `error.code` values and uses a safe generic fallback for unknown codes.

### 2.4 Request correlation and retries

- A client may send `X-Request-ID`; the backend returns it or creates one.
- Logs correlate by request ID but never contain credentials, cookies, raw tokens, or passwords.
- GET requests are safe and idempotent.
- Retryable mutations require an endpoint-specific idempotency contract before automatic retries are enabled.
- The frontend must not retry authentication failures, validation failures, or non-idempotent mutations automatically.

## 3. Authentication contract

### 3.1 Decision

Browser authentication uses a server-side opaque session. JWT access or refresh tokens are not exposed to JavaScript and are not stored in `localStorage`, `sessionStorage`, IndexedDB, URL parameters, or frontend state.

The backend sets one cookie:

```text
__Host-product_session=<opaque random token>;
Path=/;
Secure;
HttpOnly;
SameSite=Lax
```

The cookie has no `Domain` attribute. The raw token exists only in the browser cookie and transient backend request memory. Persistent storage contains a cryptographic hash of the token.

### 3.2 Ownership and invariants

The backend `auth` module owns credentials and sessions. A separate profile or permissions module is introduced only when the case requires distinct business ownership.

Mandatory invariants:

- Email comparison is normalized and case-insensitive.
- Passwords are hashed with Argon2id. Plaintext passwords are never logged, persisted, queued, or returned.
- Password length is 12-128 characters; spaces and Unicode are allowed; arbitrary composition rules are forbidden.
- A session belongs to exactly one account and has server-enforced expiry and revocation state.
- Session identifiers rotate after login and any privilege-sensitive identity transition.
- Logout revokes the current session. Logout-all revokes every session for the account.
- Password change revokes all existing sessions.
- Authentication errors do not reveal whether an account exists.
- Authorization is enforced by backend application policy. Hiding frontend controls is UX, not security.
- Unknown roles and permissions are denied by default.

Initial session lifetime is 7 days of inactivity with a 30-day absolute maximum. These values are configuration, not frontend constants.

### 3.3 Browser request rules

- Frontend calls same-origin `/api` endpoints and allows the browser to attach the cookie.
- Unsafe cookie-authenticated requests must pass same-origin `Origin` validation.
- CORS with credentials is disabled unless a concrete separate frontend origin is approved.
- If cross-site clients are introduced, CSRF protection and cookie policy must be redesigned explicitly.
- API endpoints return JSON errors; they never redirect an unauthenticated API request to an HTML login page.

### 3.4 Initial endpoints

#### `POST /api/auth/register`

Request:

```json
{
  "email": "person@example.com",
  "password": "long user supplied password"
}
```

Creates an account and authenticated session atomically. Returns HTTP 201, sets the session cookie, and returns `ApiResponse[CurrentAccount]`.

Possible errors: `validation_error`, `email_already_registered`, `rate_limited`.

#### `POST /api/auth/login`

Uses the same request shape. Returns HTTP 200, replaces any presented session cookie, and returns `ApiResponse[CurrentAccount]`.

Invalid email or password always returns HTTP 401 with `invalid_credentials` and the same public message.

#### `GET /api/auth/me`

Returns HTTP 200 with `ApiResponse[CurrentAccount]` for a valid session. Missing, expired, or revoked sessions return HTTP 401 with `unauthorized`.

#### `POST /api/auth/logout`

Revokes the current session, clears the cookie, and returns HTTP 200 with successful `data: null`. The operation is idempotent.

#### `POST /api/auth/logout-all`

Requires a valid session, revokes every session for the account, clears the current cookie, and returns HTTP 200 with successful `data: null`.

### 3.5 Current account shape

The initial public shape is intentionally small:

```json
{
  "id": "opaque-account-id",
  "email": "person@example.com",
  "status": "active"
}
```

Fields such as roles, display name, avatar, subscription, and provider identities are not added until a use case owns them.

### 3.6 Abuse and failure behavior

- Registration and login are rate-limited by both source and normalized account key.
- Initial baseline: 5 failed login attempts per 15 minutes for one source and account key. Production configuration may be stricter.
- A limited response returns HTTP 429, `rate_limited`, and a `Retry-After` header.
- Redis unavailability must fail safely without allowing an unbounded authentication attack. Exact degraded behavior must be covered by an integration test.
- Database or session-store failure returns `service_unavailable` or `internal_error`; it never creates a partial account or session.

## 4. Frontend contract

The owning module is `frontend/src/modules/auth`. Other modules import only its public `index.ts`.

Frontend rules:

- A module API adapter unwraps `ApiResponse[T]` and maps known errors into typed frontend failures.
- `GET /api/auth/me` is server state and belongs in TanStack Query.
- Login and registration forms use React Hook Form plus Zod for immediate format feedback. Backend validation remains authoritative.
- Login success invalidates or replaces the `me` query.
- HTTP 401 from `me` represents the anonymous state and does not create a global error notification.
- A protected route waits for the initial `me` result before rendering or redirecting.
- Redirect after login uses a validated same-origin path, never an arbitrary external URL.
- Logout clears cached account data only after the backend request completes or returns the documented idempotent result.
- Frontend never decodes cookies, infers permissions, or persists the current account as an authentication source of truth.

## 5. Contract change workflow

Every API change follows this order:

1. Record the decision or endpoint contract in this document when it changes shared policy.
2. Implement Pydantic request, response, and error schemas.
3. Regenerate and review OpenAPI.
4. Regenerate the TypeScript transport client.
5. Update the owning frontend adapter and user-visible states.
6. Add scenario tests at the appropriate backend, component, and E2E levels.
7. Verify no undocumented field, status, cookie, or error-code dependency remains.

Manual duplicate TypeScript interfaces for backend responses are forbidden once client generation is configured. Generated files are not edited by hand.

## 6. Required authentication scenarios

One scenario may exercise several functions and assertions. Coverage must include:

- registration creates one account, one session, a protected cookie, and a usable `me` response;
- duplicate normalized email is rejected without a partial session;
- valid login succeeds and invalid credentials return the same public failure;
- missing, expired, and revoked sessions cannot access protected behavior;
- logout is idempotent and logout-all revokes parallel sessions;
- unsafe requests with an invalid origin are rejected;
- rate limiting is bounded and returns retry information;
- frontend restores an existing session, handles anonymous state, displays login failure, and completes logout;
- authorization tests prove forbidden behavior on the backend even when requests bypass the UI.

## 7. Explicitly open decisions

These items are not approved for implementation yet:

- email verification;
- password reset and outbound email provider;
- Google, GitHub, Telegram, or other OAuth/OIDC providers;
- roles, permissions, organizations, and multi-tenancy;
- native-mobile token flow;
- account deletion and regulatory retention periods;
- session management UI beyond logout-all.

When the case makes one of these necessary, update this document before implementation and add traceable acceptance scenarios.
