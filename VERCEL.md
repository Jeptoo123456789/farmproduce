# Vercel deployment

This repository is configured as one Vercel project:

- Vite builds from `frontend/` and is served from `frontend/dist`.
- FastAPI is exposed through `api/index.py` at `/api/*`.
- The frontend calls the API through the same-domain `/api` path.

## Deploy

1. Import the repository into Vercel.
2. Leave the project root set to the repository root.
3. Add these environment variables for Production, Preview, and Development:

   - `DATABASE_URL`: a hosted PostgreSQL connection string.
   - `FARMMARKET_TOKEN_SECRET`: a long, random signing secret.

4. Deploy.

The database URL may use either `postgres://` or `postgresql://`; the backend
normalizes the former for Psycopg. The API creates its tables on startup.

SQLite remains available for local development, but Vercel's filesystem is
ephemeral. Do not use the local `farmproduce.db` as the production database.