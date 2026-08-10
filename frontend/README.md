# Home Manager — Frontend

PWA client: TypeScript, React, Vite, Tailwind CSS, TanStack Query, React Router, vite-plugin-pwa.

## Development

```bash
npm install
npm run dev
```

The dev server proxies `/api` to `http://localhost:8000` (see `vite.config.ts`), so run the
backend separately (see the root `README.md`) for the app to have anything to talk to.

## Scripts

- `npm run dev` — Vite dev server with HMR
- `npm run build` — typecheck (`tsc -b`) + production build (also generates the service worker)
- `npm run lint` — oxlint
- `npm run test` — Vitest (unit + component tests)
- `npm run preview` — serve the production build locally

## Production

`Dockerfile` builds the app and serves it via `nginx-unprivileged`, proxying `/api/` to the
`backend` service and setting security headers (`nginx.conf`, `security-headers.conf`). This is
the `nginx` service in the root `docker-compose.yml`.
