# Render deployment

This repository contains a Render Blueprint with two services:

- `farmproduce-api`: FastAPI web service.
- `farmproduce-frontend`: Vite static site.

## Deploy

1. Push the repository to GitHub.
2. In Render, choose **New > Blueprint** and select the repository.
3. Set `DATABASE_URL` on `farmproduce-api` to a hosted PostgreSQL connection string.
4. Set `VITE_API_BASE_URL` on `farmproduce-frontend` to the API URL, such as `https://farmproduce-api.onrender.com`.
5. After the frontend deploys, set `FRONTEND_URL` on `farmproduce-api` to the frontend URL.
6. Redeploy the API after setting `FRONTEND_URL`.

Render generates `FARMMARKET_TOKEN_SECRET` automatically. SQLite is only a local
fallback; production data must use PostgreSQL because Render service filesystems
are not durable databases.

## Frontend command settings

The frontend is a Render Static Site, so it does not need a start command. If the
service was created manually, remove `mpm start` and recreate it from this
Blueprint, or set these values in the Render dashboard:

- Root Directory: `frontend`
- Build Command: `npm ci && npm run build`
- Publish Directory: `dist`
- Start Command: leave empty

`mpm` is not an executable; `mpm start` will always exit with status 127.