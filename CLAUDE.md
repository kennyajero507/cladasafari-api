# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

The Django 6 + Django REST Framework API behind the Clada Safari Bliss site (cladasafaribliss.com) and dashboard. The Next.js front end (public site plus `/admin` dashboard) is the sibling repo **cladasafari-web** (`../cladasafari-web`). Both started as copies of the Holidaybank Expeditions build; the web app depends on this API's endpoints and response shapes, so treat them as a contract.

## Commands

```bash
python -m venv .venv && .venv\Scripts\activate    # Python 3.12+ (CI uses 3.13)
pip install -r requirements.txt
cp .env.example .env              # DJANGO_DEBUG=true, ADMIN_PASSWORD (12+ chars)
python manage.py migrate
python manage.py seed             # --reset: wipe content and restore it from apps/seed/data/
python manage.py runserver 8001

python manage.py test tests                                          # all tests
python manage.py test tests.test_api.AuthTests                       # one class
python manage.py test tests.test_api.AuthTests.test_<name>           # one test
```

CI (`.github/workflows/ci.yml`) runs against PostgreSQL 16: `manage.py check`, `makemigrations --check --dry-run` (commit a migration with every model change), then `test tests`. SQLite is the default locally. Setting `DATABASE_URL` switches to Postgres. Code must behave the same on both. That's why countries, categories and tags are relational rather than Postgres arrays.

Tests (`tests/test_api.py`) are end-to-end HTTP tests. `setUpTestData` runs the real `seed` command, then `tests/fixtures.py` adds what the seed does not carry (destination pages, travel areas, a blog post, a stock photo, two enquiries). Assertions depend on seeded counts (e.g. 45 published tours of 49). If you change seed data (`apps/seed/data/`), expect to update those tests. The `APIClient` has to send `HTTP_ORIGIN='http://localhost:3001'`, or writes are rejected (see below).

Production is cPanel/DirectAdmin (Passenger, WSGI): `passenger_wsgi.py` is the entry point and restores the mount point Passenger strips, so the app works on its own subdomain or under `/api` on the site's domain. The Docker and Railway files are carried over and still work: `docker compose --env-file .env.docker up --build` runs Postgres, this API under gunicorn, and `../cladasafari-web`.

## Architecture

**Layout.** `config/` holds settings and the root URLconf. `apps/` has `common` (shared infrastructure), `accounts` (AdminUser, Role, AuditLog, auth), `catalog` (tours, categories, countries, destinations), `content` (blog, testimonials, FAQs, services, editable `Page`s, `SiteSettings` singleton), `enquiries`, `media` (`ImageAsset` and uploads) and `seed`. Every app's URLs are mounted under `/api/`. Unmatched `/api/*` paths return the JSON error envelope, even in DEBUG.

**Response envelope.** Every response is `{success: true, data, meta?}` or `{success: false, error: {message, code, details?}}`. Build responses with `send()`/`paginate()`/`page_meta()` from `apps/common/responses.py`. Raise `ApiError.not_found/conflict/forbidden/unauthorized(...)` (`apps/common/exceptions.py`) rather than returning error responses by hand. The DRF exception handler flattens validation errors into `error.details` as `{field: message}`.

**Validation.** DRF serializers are used only as schemas: `validate(Schema, request.data)` returns a cleaned dict. Wire field names are camelCase (what the web app sends). Each resource's `apply()`/`assign()` maps them onto snake_case model attributes. Don't use `source=`.

**Generic CRUD (`apps/common/crud.py`).** Most draft/published collections are declared once as a `Resource` in `apps/{catalog,content}/resources.py` and expanded by `build_views()` into:
- public list and detail by slug (published only)
- `admin/<path>` list/create and `admin/<path>/<uuid>` get/patch/delete
- `admin/<path>/<uuid>/status`
- `admin/<path>/bulk/status` and `admin/<path>/bulk`

Tours, destinations, categories, blog, testimonials, FAQs, services and pages all work this way. Only enquiries, accounts, media and a few catalog views (category tree, countries, related tours) are hand-written. Details of `build_views()`:
- It keeps a slug stable on rename unless a new slug is explicitly sent.
- It maps `ProtectedError` to a 409.
- It revalidates the web cache after writes.

**Cache revalidation, a cross-repo contract.** Each `Resource.tags` returns the Next.js cache tags an object affects (`tours`, `tour:<slug>`, `home`…). `apps/common/revalidate.py` POSTs them to `REVALIDATE_URL` (the web app's `/api/revalidate`) with `x-revalidate-secret`. It does this on transaction commit, in a background thread, and never fails the save. The tag names must match `src/lib/tags.ts` in cladasafari-web. With the API mounted at `/api` on the site's domain, `REVALIDATE_URL` must be the web app's `/hooks/revalidate`, because `/api/revalidate` would reach Django. Hand-written views that change public content must call `revalidate()` themselves.

**Auth.**
- Views subclass `PublicView` (no auth) or `AdminView` (`apps/accounts/auth.py`).
- `AdminView` authenticates the `csb_admin_token` httpOnly JWT cookie and re-reads the user and role from the DB on every request. It also enforces `required_permissions`, which is a string or a `{METHOD: perm}` dict.
- Use `require(request, perm)` for checks that depend on the payload. Changing `status` counts as publishing, so an edit that flips status needs both `.edit` and `.publish`.
- Permissions are `resource.verb` strings defined in `apps/accounts/permissions_catalog.py`. Roles are seeded as Administrator (locked), Editor, Author and Travel Consultant. A new resource needs its perms added there.
- The cookie is `SameSite=None; Secure` in production, so `VerifyOriginMiddleware` (`apps/common/middleware.py`) is the real CSRF defence: every non-GET request under `/api/` must carry an `Origin`/`Referer` listed in `WEB_ORIGIN`.

**Enquiries.**
- References are `ENQ-YYMM-NNNN`, allocated under a row lock (`EnquiryReferenceCounter`).
- Pipeline: new → assigned → in progress → quoted → booked / closed.
- Each enquiry has an append-only `EnquiryEvent` timeline. Logic lives in `apps/enquiries/services.py`.
- Public submissions are throttled (`THROTTLE_ENQUIRIES`, default 20/hour). Failed logins are rate-limited per IP.
- Throttle counters live in the Django cache, which is per-process locmem unless `CACHE_URL` (Redis) is set.

**Travel areas and navigation.**
- `TravelArea` (catalog) is a regional tree, groups with areas beneath, linked to tours many-to-many and independent of `TourCategory`. Each area also has a card tag, a teaser (`description`), an image and linked `places`.
- It's served as a tree at `/api/areas`, with distinct published-tour counts and `placeCount`, and filters tours with `?area=<slug>` (a group includes its areas).
- No areas are seeded (`AREAS` in `apps/seed/data/catalog.py` is empty: the live site has none). They are managed in Django admin; there's no dashboard CRUD for them.
- `SiteSettings.navigation` holds the menu arranged in the dashboard, validated by `NavItemSchema`/`NavLinkSchema` in `apps/content/views.py`. Links must be site paths or http(s)/mailto/tel. A top-level item can instead carry a `source` (category/area/destination slug, checked to exist on save), which the web app resolves at render time. The menu is replaced whole on PATCH, and an empty list means the web app builds the menu from categories.

**Categories and destinations.**
- Categories are a two-level tree, groups with leaf categories beneath; `apply_category` refuses a third level, and tours must sit in a leaf. The web app's menu, footer, filters and package form all assume this shape. The seeded tree is the Clada Safari Bliss menu (Local, Getaways, International, Safari Packages and their places), with the live site's slugs, which the web app's redirects from `/ba_locations/<slug>` rely on.
- `Country.iso_code` is a django-countries `CountryField`, so any ISO 3166-1 country is valid. The destination form sends the code; `resolve_destination_country()` creates the `Country` row on first use, with a region from `apps/catalog/regions.py` unless one is sent. `/api/admin/countries/options` lists every country with its region and existing destination page. Keep destinations on the `Country` FK rather than a bare `CountryField`: tours, filters and counts join through it.
- A destination is a country page, so a tour is "in" every destination whose country it visits. `?destination=<slug|uuid>`, the destination's `tourCount` and the tour's derived `destinations` list all follow that one rule. `Tour.destination` is only the primary one (listed first), and saving it adds its country to the tour's countries.

**Pages.** `Page` (content) holds About, Contact, policies and other standalone pages, served at `/api/pages` and `/api/pages/<slug>` and rendered by the web app at `/<slug>`.
- `body` is the blog Markdown subset. `sections` are typed blocks (`text`, `imageText`, `cards`, `faq`, `cta`) validated by `SECTION_SCHEMAS` in `apps/content/resources.py`; the web app's `PageSections` renders the same set.
- The `contact` template's `contact` dict holds extra emails, phones and offices. `contactDetails` in the response fills whatever it leaves empty from `SiteSettings.contact`/`socials`.
- `RESERVED_PAGE_SLUGS` lists the web app's own top-level routes; keep it in step when a route is added there. Tags are `pages` and `page:<slug>`.
- The seed creates pages once and never overwrites them. The policy pages are draft outlines, because legal text has to come from the business.

**Content provenance.** Everything seeded comes from cladasafaribliss.com (`apps/seed/data/`: `tours.py` is generated from its 49 package pages; the README lists what was carried over and the judgement calls). Where the live site has nothing, the field is empty: no itineraries, inclusions, group sizes, price basis, reviews or FAQs. On a tour, `price_from` 0 means "price on request", and `duration_days` 0 and `group_size_max` 0 mean "not stated"; the web app hides them. Seeded records carry `is_sample` and `source_note`. Don't present generated content as real (no invented ratings, licence numbers, itineraries or accreditations). `apps/content/defaults.py` holds the `SiteSettings` defaults, which the web app's `src/lib/settings.ts` `FALLBACK` mirrors.

**Media.** Uploads go to `MEDIA_ROOT` (`uploads/`) and are served by Django at both `/uploads/` and `/api/uploads/` (`config/urls.py`) unless `SERVE_MEDIA=false`. Their URLs are `PUBLIC_API_URL` + `/uploads/<file>`, so `PUBLIC_API_URL` is `https://cladasafaribliss.com/api` when the app is mounted under `/api`. `image_shape()` includes `width`/`height` when known, which the web app uses to avoid stretching small photographs. The seeded photographs themselves live in the web repo's `public/images/`. The API only stores their `ImageAsset` records (`apps/seed/data/images.py`).

**Settings.** Everything comes from env (`.env.example`). With `DJANGO_DEBUG` off, the server refuses to start if `DJANGO_SECRET_KEY`/`JWT_SECRET` are still the `dev-only` placeholders. `REVALIDATE_SECRET` must equal the web app's. In production, set `COOKIE_DOMAIN` to the shared parent domain, or have the web app proxy through `/backend`.
