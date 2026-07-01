# Chrome Web Store Pre-Launch Checklist

Status as of 2026-07-01. Items already fixed this session are marked done; the rest need a decision or asset before submission.

## Done (this session)

- [x] Basic API-key auth wired (`app/auth.py`, `app/api/routes.py`) — not strong security (the key ships in the public extension), but stops casual scraping/free-riding by other extensions.
- [x] Rate limiting added (`slowapi`, `ANALYZE_RATE_LIMIT` env var, default 20/minute per IP).
- [x] CORS tightened: dropped `allow_credentials`, restricted methods/headers.
- [x] Per-review length cap (5000 chars) and request-size caps (500 reviews, 20 batch products) enforced at the schema level.
- [x] `.env.example` fixed (stale English model default, real `EXTENSION_API_KEY`/`ANALYZE_RATE_LIMIT`/`CORS_ORIGINS` documented).
- [x] `scripts/package_extension.sh` — builds a store-upload zip with only runtime files (excludes `extension/e2e/`, `mock_server.py`).
- [x] Integration + e2e test coverage, ≤3s performance target verified (ADR-0006).

## Blocks submission — needs your decision

- [ ] **Deploy the backend somewhere real, over HTTPS.** `extension/background.js`'s `API_BASE` and `manifest.json`'s `host_permissions` are still `http://127.0.0.1:8001` — the extension does not work for any real installed user until this points at a deployed host. Once you pick a provider, update both files (both hold the same URL) and regenerate `EXTENSION_API_KEY` for that environment.
- [ ] **Decide the monetization model.** `app/db/database.py` has a half-built per-API-key quota/billing scaffold (SQLite, `authenticate_and_charge`) that is currently unused and has a known race condition (quota check-then-update isn't atomic — needs `UPDATE ... WHERE used_quota + ? <= monthly_quota` or a transaction/lock) and a hardcoded demo key (`DEMO-SITE-KEY-12345`) that should be removed before real use. Note Chrome Web Store no longer has a native in-store payments API (discontinued) — a paid model means your own billing (Stripe, etc.) gating either the extension itself or backend access.
- [ ] **Real icon design.** `extension/icons/*.png` are solid-color placeholders, not a designed icon — this is a first-impression/professionalism issue for a paid listing.
- [ ] **Privacy policy.** Chrome Web Store requires a published privacy policy URL for any extension that transmits page content off-device (this one sends scraped review text to your backend). Needs your company/contact details to draft properly.
- [ ] **Store listing assets.** At least one screenshot (1280×800 or 640×400); a 440×280 promo tile is recommended. None exist yet.
- [ ] Once the backend has a real, stable host, tighten `host_permissions` in `manifest.json` to that exact origin (currently scoped to trendyol.com/hepsiburada.com/localhost — the localhost entry needs to be swapped for the real API origin, not just added to).

## Known limitation, not blocking

- The `X-API-KEY` scheme is an abuse-prevention speed bump, not real security — anyone can extract it from the unpacked extension. If usage costs become a real concern, per-user auth (e.g., a lightweight signup/license-key flow) is the actual fix, not a stronger shared secret.
