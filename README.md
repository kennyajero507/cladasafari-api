# Clada Safari Bliss: API

The Django 6 + Django REST Framework API behind the Clada Safari Bliss website and admin
dashboard. It serves content, bookings/enquiries, users and roles, and the media library.

The website and `/admin` dashboard are in a separate repo, **cladasafari-web** (Next.js).

Both repos started as copies of the Holidaybank Expeditions build, so the endpoints and response
shapes are the same. The catalogue, content, brand and menu are Clada Safari Bliss's own, taken
from cladasafaribliss.com.

---

## Run it locally

Requirements: Python 3.12+. SQLite is used by default; another database via `DATABASE_URL`.

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # set DJANGO_DEBUG=true, and ADMIN_PASSWORD (12+ chars)
python manage.py migrate
python manage.py seed             # catalogue, content and the admin account
python manage.py runserver 8001
```

Then start the web app (see its README). `REVALIDATE_SECRET` must match in both repos.

| | URL |
|---|---|
| API health | http://localhost:8001/api/health |
| Django admin (superusers) | http://localhost:8001/django-admin/ |
| Dashboard (web app) | http://localhost:3001/admin, signing in with `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env` |

### With Docker

`docker-compose.yml` runs PostgreSQL 16, this API under gunicorn and the built Next.js site. It
expects the web repo checked out next to this one as `../cladasafari-web`.

```bash
cp .env.docker.example .env.docker    # fill in the secrets
docker compose --env-file .env.docker up --build
docker compose --env-file .env.docker exec api python manage.py seed
```

### On cPanel / DirectAdmin (Python app, WSGI)

`passenger_wsgi.py` is the entry point for **Setup Python App** (Phusion Passenger on CloudLinux).

1. Upload the repo (without `.venv`, `db.sqlite3` and `uploads/`) to the app's folder.
2. In **Setup Python App**: Python 3.12 or newer, the folder as application root, startup file
   `passenger_wsgi.py`, entry point `application`. Choose where it answers:
   - **its own subdomain**, e.g. `api.cladasafaribliss.com` (application URL `/`), or
   - **`/api` on the site's domain**, `cladasafaribliss.com/api`. Passenger strips the mount point
     from the path; `passenger_wsgi.py` puts it back, so the same URLconf serves both.
3. Create `.env` in that folder (see `.env.example`):

   ```
   DJANGO_DEBUG=false
   DJANGO_SECRET_KEY=<random>
   JWT_SECRET=<random, 32+ characters>
   REVALIDATE_SECRET=<random, same value in the web app>
   DATABASE_URL=<the hosting account's database>
   DJANGO_ALLOWED_HOSTS=cladasafaribliss.com,www.cladasafaribliss.com,api.cladasafaribliss.com
   WEB_ORIGIN=https://cladasafaribliss.com,https://www.cladasafaribliss.com
   PUBLIC_API_URL=https://api.cladasafaribliss.com        # or https://cladasafaribliss.com/api
   COOKIE_DOMAIN=.cladasafaribliss.com                    # own-subdomain layout only
   ADMIN_EMAIL=<email>
   ADMIN_PASSWORD=<12+ characters>
   ```

   Under `/api` on the site's domain also set
   `REVALIDATE_URL=https://cladasafaribliss.com/hooks/revalidate` (see the web README).
4. In the app's virtual environment (the panel shows the `source .../activate` command):

   ```bash
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py seed
   ```

5. Restart the app from the panel (or `touch tmp/restart.txt`).

**Uploads.** Dashboard uploads are written to `uploads/` in the app folder and served by Django
at both `/uploads/<file>` and `/api/uploads/<file>` (`config/urls.py`). Their URLs are built from
`PUBLIC_API_URL`, so that value must be the address browsers reach this app on. Keep `uploads/`
out of any deploy step that replaces the folder.

**Database.** The code is tested on SQLite and PostgreSQL. cPanel accounts usually offer MySQL or
MariaDB: `DATABASE_URL=mysql://user:pass@localhost/dbname` with `pip install mysqlclient` should
work with Django 6 (MariaDB 10.6+, MySQL 8.0.11+), but it has not been run against either here.
Run the test suite against it before going live.

`docker-compose.yml`, the `Dockerfile` and `railway.json` are carried over from the Holidaybank
build and still work for a container host.

### Tests

```bash
python manage.py test tests      # 67 API tests, SQLite or PostgreSQL
```

CI (`.github/workflows/ci.yml`) runs them against PostgreSQL.

### Endpoints

Public endpoints (no auth): `/api/tours`, `/api/tours/<slug>`, `/api/tours/<slug>/related`,
`/api/destinations`, `/api/categories`, `/api/countries`, `/api/blog`, `/api/testimonials`,
`/api/faqs`, `/api/services`, `/api/settings`, `/api/media`, `POST /api/enquiries`,
`/api/enquiries/options`, `/api/health`.

Dashboard endpoints live under `/api/admin/*` and `/api/auth/*`. Each is gated by a permission from
`apps/accounts/permissions_catalog.py`.

---

## Content: what came from the live site

cladasafaribliss.com (WordPress) was treated as the authoritative source, read on 5 October 2026.
Nothing was written to fill a gap: where the live site has no content, the field is empty.

**Taken from the live site**

- Brand name, logo, the "Beyond Magical" line, colours (#6d5116 and #9bb10d) and fonts (Aref Ruqaa
  for headings, Jost for text).
- The menu, exactly: Local, Getaways, International and Safari Packages with their places, plus
  Air Ticketing, About Us and Contact Us. Categories keep the live site's slugs.
- All **49 packages**: title, overview, "from" price, duration, gallery, and the "Things To Do"
  list as highlights. "What to carry" and camp-inclusion lists stay in the overview text.
- Hero copy and its three slider photographs; the About Us page (Company Profile, Mission, Vision,
  Values); the Air Ticketing page; contact details (Marist Lane, Karen; +254 727 999 944;
  info@cladasafaribliss.com; opening hours).

**Not on the live site, so not here**

- **Day-by-day itineraries, inclusions, exclusions and group sizes.** No package page has them.
  The fields exist and the public page shows each section once it has content.
- **What a price is per.** The live site says "From $410" and no more, so `priceBasis` is blank.
- **Reviews, FAQs, blog posts, destination pages.** None are seeded; their sections stay hidden.
- **Social links.** The live site shows icons that link nowhere.
- **Terms and privacy text.** The live Terms page is an unedited placeholder. Both pages are
  seeded as draft outlines for the business to write.

**Judgement calls to confirm with the business**

- **10 packages show "$0.00" on the live site.** They are seeded with price 0, which the web app
  prints as "Price on request". `5 Days Dubai Package` is the exception: its page shows $0.00 but
  its listing card shows $910, which is used.
- **Prices on a package's page and on its listing card sometimes differ.** The page's price is
  used. The three where it matters: Beautiful Mauritius (page KES 226,980, card $1,234), Dubai
  Second Timers Holidays (page $755, card $1,876) and 6 Days Luxury Wings Over Amboseli & Mara
  (page $4,061, card $4,573).
- `5 Days Kenya Midrange Safari Highlights` shows "KES 1,342" on its page. Its card shows $1,342
  and its budget and luxury siblings are $1,097 and $2,264, so it is seeded as USD.
- **7 packages have no stated length** (the four getaways, Mauritius, Cape Town, Dubai Second
  Timers). They are seeded with 0 days, which hides the duration.
- **4 packages are seeded as drafts**: three with no description or price on the live site (both
  8 Days Cheetah safaris, 8 Days Kenya Splendors) and one leftover duplicate ("… Copy").
- **5 packages sit on the live site under terms that are not in its menu.** The two Glimpse of
  Kenya safaris and Kenya Splendors are filed under Kenya(Non-residents); the two Cheetah safaris
  under East Africa Safaris.
- The Budget / Midrange / Luxury listings of the live site are not categories here; the tier is
  in each package's title.
- Titles in capitals were set in title case, and "Amboselli" corrected to "Amboseli".
- `6 Days Luxury Wings Over Amboseli & Mara` borrows the midrange version's photographs: its own
  five files return 404 on the live site.

**The live site appears to have been tampered with.** Its Terms & Conditions page carries
injected links to gambling sites, and its sitemap lists 226 spam post categories (casino and
betting names). None of that was imported. The WordPress install should be checked and cleaned,
or retired, whatever happens with this build.

Each record has a `source_note` saying where it came from. `python manage.py seed --reset` wipes
content and restores it from `apps/seed/data/`. Images are registered in the media library
(`ImageAsset`, seeded from `apps/seed/data/images.py`); the files are in the web repo's
`public/images/`.

---

## Architecture notes

**API shape.** Every response is `{success, data, meta?}` or `{success: false, error: {message,
code, details?}}`. Validation errors come back as a flat `{field: message}` map that the forms
highlight.

**Data model** (`apps/`)

| App | Models |
|---|---|
| `catalog` | `Country`, `TourCategory` (tree), `Destination`, `Place`, `Tour`, `TourImage` |
| `content` | `BlogPost`, `Tag`, `Testimonial`, `Faq`, `Service`, `SiteSettings` (singleton) |
| `media` | `ImageAsset`: every image with its credit and origin |
| `enquiries` | `Enquiry`, `EnquiryEvent` (timeline), `EnquiryReferenceCounter` |
| `accounts` | `AdminUser` (email login), `Role` (permission sets), `AuditLog` |

Countries, categories and tags are relational rather than Postgres arrays, so filtering behaves
identically on SQLite and PostgreSQL. The menu, footer and tour filters are built from
`/api/categories` and `/api/countries`, so new product lines need no deploy.

**Auth.** The dashboard signs in with a JWT in an httpOnly cookie (`csb_admin_token`), re-checked
against the database on every request. Cookie-authenticated writes must carry the web app's
`Origin` (see `common/middleware.py`). Failed logins are rate-limited per IP; public enquiries are
throttled at 20 an hour.

**Permissions.** Roles hold `resource.verb` permissions (`tours.publish`, `enquiries.assign`...).
They are seeded as Administrator (locked), Editor, Author and Travel Consultant, and editable under
Roles. Changing a record's status counts as publishing.

**Enquiries.** Each gets an `ENQ-YYMM-NNNN` reference, allocated under a row lock. They move through
new → assigned → in progress → quoted → booked / closed, with claim/assign, follow-up dates, and an
append-only timeline.

**Cache.** After an admin save the API POSTs the affected cache tags to Next.js
(`/api/revalidate`), so public pages update within moments. Otherwise they revalidate every five
minutes.

### Production checklist

- Set `DJANGO_DEBUG=false`, real `DJANGO_SECRET_KEY` / `JWT_SECRET` / `REVALIDATE_SECRET`,
  `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`, `WEB_ORIGIN`, `PUBLIC_API_URL`, and `COOKIE_DOMAIN`
  when the API has its own subdomain.
- Set `CACHE_URL` (Redis) when running more than one worker, so rate limits are shared.
- Confirm the prices and the other judgement calls listed above with the business.
- Add itineraries, inclusions and exclusions to the packages, and say what prices are per.
- Confirm the rights to the photographs carried over from the live site, or replace them.
- Write and publish the Privacy Policy and Terms & Conditions pages.
- Optional: set `NEXT_PUBLIC_TAWK_SRC` to the company's own Tawk.to widget for live chat.
