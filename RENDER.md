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