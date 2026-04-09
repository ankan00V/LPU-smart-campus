# Railway Hobby Deployment

This project can run on Railway Hobby as a single service.

## What Runs Where

- `uvicorn` serves the FastAPI app and the frontend from the same origin.
- `celery` runs in the same Docker container under `supervisord`.
- Postgres, MongoDB, and Redis stay external on managed services.

## Required Railway Variables

Set these on the Railway service:

- `APP_ENV=production`
- `APP_DEPLOY_TARGET=railway`
- `APP_RUNTIME_STRICT=true`
- `APP_MANAGED_SERVICES_REQUIRED=true`
- `APP_SECRETS_PROVIDER=env`
- `APP_ALLOW_ENV_SECRETS_IN_PRODUCTION=true`
- `APP_AUTH_SECRET`
- `SCIM_BEARER_TOKEN`
- `APP_LOOKUP_HASH_SECRET`
- `APP_FIELD_ENCRYPTION_REQUIRED=true`
- `APP_FIELD_ENCRYPTION_KEYS_JSON`
- `APP_FIELD_ENCRYPTION_ACTIVE_KEY_ID`
- `APP_COOKIE_SECURE=true`
- `SQLALCHEMY_DATABASE_URL`
- `POSTGRES_ADMIN_DATABASE_URL`
- `DATABASE_SSL_MODE=require`
- `DATABASE_PREFER_IPV4=true`
- `MONGO_URI`
- `MONGO_PERSISTENCE_REQUIRED=true`
- `REDIS_URL`
- `REDIS_REQUIRED=true`
- `REDIS_SSL_REQUIRED=true`
- `WORKER_REQUIRED=true`
- `WORKER_INLINE_FALLBACK_ENABLED=false`
- `WORKER_WAIT_FOR_OTP_RESULT=true`
- `OTP_DELIVERY_DIRECT_SYNC=true`
- `OTP_DELIVERY_MODE=smtp`

## Deploy Order

1. Connect the GitHub repo in Railway.
2. Add the variables above.
3. Make sure Neon, Atlas, and Upstash are reachable from Railway.
4. Deploy the service.
5. Open the Railway URL and confirm `/` returns the health payload.
6. Log in with OTP and verify one worker-backed action.

## Notes

- Railway will build the provided `Dockerfile`.
- The container listens on Railway's injected `PORT` automatically.
- The worker stays inside the same container, so there is only one paid service.
