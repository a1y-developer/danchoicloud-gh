## danchoicloud_gh
@danchoicloud GitHub App

### Web UI
The Next.js web UI lives in `web/` and is used to log in with GitHub, install
the app, and configure notification channels.

```bash
cd web
npm install
cp .env.example .env.local
npm run dev
```

### API
The FastAPI backend serves GitHub webhooks and configuration APIs.

```bash
python -m uvicorn app.main:app --reload
```
