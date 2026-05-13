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
- `OTP_SMTP_HOST=smtp.gmail.com`
- `OTP_SMTP_PORT=587`
- `OTP_SMTP_USERNAME` (your Gmail address)
- `OTP_SMTP_PASSWORD` (Google app password, no spaces)
- `OTP_SMTP_STARTTLS=true`
- `OTP_SMTP_USE_SSL=false`
- Keep SendGrid variables present but commented out until you re-enable it

## Deploy Order

1. Connect the GitHub repo in Railway.
2. Add the variables above.
3. Make sure Neon, Atlas, and Upstash are reachable from Railway.
4. Deploy the service.
5. Open the Railway URL and confirm `/` returns the health payload.
6. Log in with OTP and verify Recovery Copilot emails deliver via SMTP.

## Notes

- Railway will build the provided `Dockerfile`.
- The container listens on port `8080` to match Railway public networking.
- The worker stays inside the same container, so there is only one paid service.

## Recovery Copilot Autopilot

- Automatic mode: enable `ATTENDANCE_RECOVERY_AUTOPILOT_ENABLED=true` and set:
  - `ATTENDANCE_RECOVERY_AUTOPILOT_INTERVAL_SECONDS` (default `900`)
  - `ATTENDANCE_RECOVERY_AUTOPILOT_BATCH_SIZE` (default `400`)
  - `ATTENDANCE_RECOVERY_RETRO_NOTIFY_COOLDOWN_MINUTES` (default `360`)
  - `ATTENDANCE_RECOVERY_AI_GUIDANCE_ENABLED=true`
  - `ATTENDANCE_RECOVERY_STUDENT_EMAIL_COOLDOWN_MINUTES` (default `1440`)
  - `ATTENDANCE_RECOVERY_FACULTY_EMAIL_COOLDOWN_MINUTES` (default `1440`)

- Bedrock personalization (optional):
  - Set `AWS_BEARER_TOKEN_BEDROCK` in Railway Variables (do not commit it).
  - For Campus Copilot: `COPILOT_LLM_PROVIDER=bedrock`, `COPILOT_BEDROCK_REGION`, `COPILOT_BEDROCK_MODEL_ID`
  - For Recovery Copilot emails: `RECOVERY_LLM_EMAIL_ENABLED=true`, `RECOVERY_LLM_PROVIDER=bedrock`, `RECOVERY_BEDROCK_REGION`, `RECOVERY_BEDROCK_MODEL_ID`
- One-click admin endpoint:
  - `POST /attendance/recovery/retro-notify`
  - Body example:
    - `{"limit": 400, "force_resend": false, "dry_run": false, "refresh_scope": true}`
- Cron-friendly trigger script:
  - `python3 scripts/recovery_retro_notify.py --base-url https://app.lpusmartcampus.site --admin-token <token> --limit 400`
