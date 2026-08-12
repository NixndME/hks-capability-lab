# HKS Capability Portal — Frontend

React + TypeScript + Vite + Tailwind CSS + lucide-react. Talks only to the
backend's REST API (`../backend/`) — never to Kubernetes directly.

## Develop

```bash
npm install
npm run dev      # Vite dev server on :5173, proxies /api,/health,/ready -> :8080 (see vite.config.ts)
```

Run the backend separately (`cd ../backend && .venv/bin/uvicorn app.main:app --port 8080`) alongside `npm run dev`.

## Build

```bash
npm run build     # tsc -b && vite build -> dist/
npm run lint       # tsc --noEmit only
```

In production, `../Containerfile` builds this and the FastAPI backend
serves `dist/` directly (see `../backend/app/main.py`'s SPA fallback route)
— one container, one port, no separate frontend deployment.

## Design tokens

Centralized in `tailwind.config.js` ("Corporate Trust": indigo primary,
violet secondary, Plus Jakarta Sans) — components should reference token
names (`text-primary`, `bg-surface`, `font-heading`, etc.), not hard-coded
hex values.
