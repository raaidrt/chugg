# Chugg

A client-only chess opening trainer. See the exact variation, play one side from memory, and let Chugg play the other. Built with React, TypeScript, Vite, chess.js, IndexedDB, and a service worker.

**[Open Chugg](https://raaidrt.com/chugg/)** — hosted on GitHub Pages, inheriting the account's existing `raaidrt.com` domain. HTTPS is enforced. Use **Install Chugg** in the app for Safari and Android instructions.

## Run locally

Use Node 22.12+ and npm.

```sh
npm ci
npm run dev
```

```sh
npm test
npm run build
npm run preview
```

The development server does not install an offline service worker. Test installation/offline behavior using a production build and `npm run preview`, or the deployed HTTPS site.

## What is included

- 45 exact named opening lines across 13 families, with curated names/move orders from the Lichess CC0 dataset.
- Popularity-weighted family-then-variation sampling, softened by exponent 0.7 and 5% exploration; recent lines are excluded when alternatives exist.
- Real reference counts from TWIC tournament issues 1600–1603. These are tournament-sample frequencies among supported exact move orders, **not** online rapid population estimates.
- One-tap practice with White or Black chosen randomly for each new drill, a name-first opening reveal, legal-move validation, automatic opponent replies, hints, move history, replay, and library browsing. Replay keeps the same side.
- Device-only per-side progress, validated JSON export/import, optional persistent-storage request, and Safari/Android installation guidance.
- Locally bundled Maestro pieces and app icons. No runtime third-party API, account, database server, or analytics.

## How it is distributed

`npm run build` produces `dist/`: static HTML, JS, CSS, the catalog bundled into JS, images, a manifest, and a service worker. The worker precaches the app and opening assets. Once the service worker has cached the app and opening assets, users can practice without a network. Installation alone does not confirm that caching has finished.

An update waits for the user to select **Update Chugg** outside a drill. Opening IDs remain stable across catalog builds; progress lives separately in IndexedDB and is not replaced with app assets. A stable production origin is important because device storage is scoped to the origin.

Progress does not automatically sync across devices. Clearing site data or browser eviction can remove it; export a backup. Import merges snapshots conservatively without double-counting repeated imports. See [storage details](docs/STORAGE.md).

## Deploy with GitHub Actions / GitHub Pages

This repository includes a test/build workflow and a manually triggered Pages deployment workflow.

1. Push the repository to GitHub.
2. Under **Settings → Pages → Build and deployment**, choose **GitHub Actions**.
3. Under **Actions → Deploy to GitHub Pages**, select **Run workflow** on the branch to deploy.
4. The deployment action reports the HTTPS URL. This repository inherits the account's custom domain and is published at `https://raaidrt.com/chugg/`.

The workflow obtains the Pages base path and sets `BASE_PATH` during the build. This also updates the manifest scope, service worker, and asset URLs. Test this layout locally with:

```sh
BASE_PATH=/chugg/ npm run build
BASE_PATH=/chugg/ npm run preview
# Open http://localhost:4173/chugg/
```

Deployments are manual so a normal code push never unexpectedly updates the installed app. The check workflow runs on pushes and pull requests.

## Alternative: Cloudflare Pages

Connect this repository to Cloudflare Pages. Use `npm run build` as the build command, `dist` as the output directory, and Node 22.12+ for the build environment. Leave `BASE_PATH` unset when serving from the domain root. No Pages Functions or Worker is needed. `public/_headers` sets cache behavior for Cloudflare; GitHub Pages ignores this file.

## Catalog updates

See [catalog source, limitations, and regeneration](docs/CATALOG.md). `npm run catalog:build` regenerates the bundled catalog from pinned opening inputs and checked-in aggregate counts. Preparation runs on your laptop/CI; the phone only receives the resulting catalog. The catalog is a list of fixed training sequences, not an engine or an exhaustive tree of all theoretical continuations.

## Assets and licensing

Maestro is by **sadsnake1**, distributed via Lichess under **CC BY-NC-SA 4.0**. The pieces are included unmodified. This license restricts commercial use of those assets; obtain permission or choose another set before commercial distribution. See [third-party notices](THIRD_PARTY_NOTICES.md) and the in-app Credits page.

Regenerate the install icons with `npm run icons:build`. The Chugg icon is an original SVG mark; it does not reuse Lichess branding.
