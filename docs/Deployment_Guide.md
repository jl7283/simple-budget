# Deployment Guide

Cross-Platform Budgeting Application

## Prerequisites and Dependencies

- GitHub repository with deployable source code
- Backend hosting account (Render or equivalent)
- Frontend hosting account (Vercel or equivalent)
- Managed PostgreSQL database
- Environment secrets prepared for production
- Runtime dependencies installed from:
   - `backend/requirements.txt`
   - `mobile/package.json`

## Backend Deployment (Render)

1. Push code to GitHub.
2. Log into Render.
3. Create new Web Service.
4. Connect repository.
5. Set service root directory to `backend/`.
6. Set build command:

pip install -r requirements.txt

7. Set start command:

uvicorn app.main:app --host 0.0.0.0 --port 10000

8. Add environment variables:
   - DATABASE_URL
   - SECRET_KEY
   - ACCESS_TOKEN_EXPIRE_MINUTES
   - API_V1_PREFIX

9. Deploy.

---

## Frontend Deployment (Vercel)

1. Connect GitHub repository.
2. Set project root to `mobile/`.
3. Set build command:

npx expo export --platform web

4. Set output directory:

dist

5. Deploy.

Note:

- Frontend API requests use environment-driven configuration:
   - `EXPO_PUBLIC_API_BASE_URL` (for example, `https://api.example.com`)
   - Optional: `EXPO_PUBLIC_API_PREFIX` (defaults to `/api/v1`)
   - Optional: `EXPO_PUBLIC_API_STRICT` (`true` forces a startup error in production when API base URL is missing)

---

## Environment Variables

Backend:

- DATABASE_URL
- SECRET_KEY
- ACCESS_TOKEN_EXPIRE_MINUTES
- API_V1_PREFIX

Frontend:

- EXPO_PUBLIC_API_BASE_URL
- EXPO_PUBLIC_API_PREFIX (optional, default: /api/v1)
- EXPO_PUBLIC_API_STRICT (optional, default: false)

---

## Post-Deployment Testing

After deployment:

- Register user
- Log in
- Create budget
- Add expense
- Verify summary updates

---

## Deployment Rehearsal (Fresh Environment)

Use this checklist for release readiness validation.

1. From repository root, move to backend folder.
2. Export required environment variables:
   - POSTGRES_PASSWORD
   - SECRET_KEY
3. Tear down all existing containers, network, and volumes:

docker compose down -v --remove-orphans

4. Rebuild and start services:

docker compose up --build -d

5. Confirm container status:

docker compose ps

Expected state:

- db service is `healthy`
- app service is `started` and transitions to `healthy`

6. Validate health and readiness endpoints:

- GET /health returns 200 and status=healthy
- GET /ready returns 200 and status=ready with database=ok

7. Run smoke test:

python scripts/smoke_test.py

Expected result:

- All checks pass
- Exit code 0

---

## Rollback Validation Drill

Perform this drill to verify that a bad release can be recovered quickly.

1. Simulate a bad app configuration by setting an invalid env value (example: ACCESS_TOKEN_EXPIRE_MINUTES=not-a-number).
2. Recreate app service:

docker compose up -d --force-recreate app

3. Confirm service degradation:

- /health request fails (connection or non-200)

4. Restore known-good configuration values.
5. Recreate app service again:

docker compose up -d --force-recreate app

6. Confirm recovery:

- /health returns 200 with status=healthy
- db remains healthy

Rollback validation passes only if both degradation and recovery are observed.

---

## Release Signoff Notes Template

Record the following after rehearsal:

- Date and environment used
- Commands executed
- Health/readiness results
- Smoke test summary
- Rollback drill result
- Final go/no-go decision
- Signoff owner
