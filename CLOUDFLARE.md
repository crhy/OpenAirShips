# Cloudflare Pages handoff

The production-ready static site lives in `web/`.

## Git integration

Create a Cloudflare Pages project connected to `crhy/OpenAirShips` with:

- Production branch: `main`
- Framework preset: None
- Build command: leave blank
- Build output directory: `web`

Cloudflare will publish a `*.pages.dev` preview before any DNS is moved. Once it is approved, add `openairships.com` and `www.openairships.com` as custom domains in Pages, then follow Cloudflare's displayed DNS changes.

## Local preview

Run `npm install`, then `npm run dev`. A plain static server pointed at `web/` also works.

## Before DNS cutover

- Confirm Discord, GitHub, donation and model links.
- Decide explicit licenses for code, hardware, documentation and media.
- Add current owners/contact destinations for each workstream.
- Review safety and historical claims with qualified sources.
- Replace any concept imagery whose reuse rights are unclear.
