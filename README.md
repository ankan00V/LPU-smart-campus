# LPU Smart Campus Management System (MVP)

Python backend starter project for the **mandatory requirements** in `LPU_Project_2.pdf`.

Implemented as a FastAPI API with **MongoDB-required persistence** (production mode) and separate modules for:
- Smart Attendance Management
- Smart Food Stall Pre-Ordering
- Campus Resource & Parameter Estimation
- Make-Up Class & Remedial Code
- Role-based authentication (`faculty/student`) with OTP login
- Puter.js-powered AI assistant (client-side, no API key)
- MongoDB (Atlas) mirroring for operational/AI event data

## 1) Stack
- FastAPI
- SQLAlchemy
- SQLite
- Custom token auth + OTP verification flow
- PyMongo (MongoDB Atlas integration)
- OpenCV (server-side face verification fallback)

## 2) Run Locally
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 \
  --reload-dir app --reload-dir web \
  --reload-exclude '.venv/*' --reload-exclude '.venv_*/*'
```

Open:
- API docs: `http://127.0.0.1:8000/docs`
- Health endpoint: `http://127.0.0.1:8000/`
- Web UI: `http://127.0.0.1:8000/ui`

Environment config:
- Create `.env` (or copy from `.env.example`)
- Required for Mongo:
  - `MONGO_URI=...`
  - `MONGO_DB_NAME=lpu_smart`
  - `MONGO_PERSISTENCE_REQUIRED=true`
- Required for real OTP email delivery:
  - `OTP_DELIVERY_MODE=smtp` or `OTP_DELIVERY_MODE=graph`
  - For SMTP mode:
    - `OTP_SMTP_HOST`, `OTP_SMTP_PORT`
    - `OTP_SMTP_USERNAME`, `OTP_SMTP_PASSWORD`
    - `OTP_FROM_EMAIL`
    - Optional: `OTP_SMTP_STARTTLS`, `OTP_SMTP_USE_SSL`
  - For Graph mode (recommended when SMTP AUTH is blocked):
    - `OTP_GRAPH_TENANT_ID`, `OTP_GRAPH_CLIENT_ID`, `OTP_GRAPH_CLIENT_SECRET`
    - `OTP_GRAPH_SENDER_USER`
  - Optional: `OTP_SUBJECT_PREFIX`
  - Optional: `ALLOW_DEMO_SEED=true` only if you explicitly want demo seed API enabled
- Optional for face verification behavior:
  - `FACE_VERIFICATION_MODE=opencv_only` (default)
  - Supported values: `hybrid`, `opencv_only`, `ai_only`
  - Strict biometric tuning:
    - `FACE_MATCH_PASS_THRESHOLD` (default `0.82`)
    - `FACE_MATCH_MIN_SIMILARITY` (default `0.82`)
    - `FACE_MATCH_MIN_FRAMES` (default `5`)
    - `FACE_MATCH_MAX_FRAMES` (default `8`)
    - `FACE_ANTI_SPOOF_BLUR_THRESHOLD`, `FACE_ANTI_SPOOF_MIN_FACE_AREA_RATIO`
    - `FACE_ANTI_SPOOF_MIN_EYE_DISTANCE_RATIO`, `FACE_ANTI_SPOOF_MIN_LOWER_TEXTURE_RATIO`
    - `FACE_ANTI_SPOOF_MIN_CONTRAST`

## 3) Project Structure
```text
app/
  main.py
  database.py
  models.py
  schemas.py
  routers/
    people.py
    attendance.py
    food.py
    resources.py
    makeup.py
web/
  index.html
  styles.css
  app.js
```

## 4) Mandatory Modules Covered

### Module 1: Smart Attendance Management
Endpoints:
- `POST /attendance/mark-bulk` (faculty one-click attendance)
- `GET /attendance/absentees`
- `GET /attendance/summary`
- `GET /attendance/notifications`
- `POST /attendance/schedules`
- `GET /attendance/schedules`
- `GET /attendance/student/timetable`
- `POST /attendance/student/default-timetable`
- `GET /attendance/student/profile-photo`
- `PUT /attendance/student/profile-photo`
- `GET /attendance/student/attendance-aggregate`
- `GET /attendance/student/attendance-history`
- `POST /attendance/realtime/mark`
- `GET /attendance/faculty/dashboard`
- `POST /attendance/faculty/review`
- `POST /attendance/faculty/classroom-analysis`
- `GET /attendance/faculty/classroom-analysis`

Included behavior:
- Instant attendance update
- Automatic absentee detection
- Simulated notifications to students and parents
- Optional source field (`faculty-web`, `cctv-upload`, etc.)
- Realtime facial attendance with strict OpenCV embedding verification (AI optional assist only)
- Multi-frame verification (default: 5 consecutive valid frames)
- Anti-spoof checks: blur, coverage/occlusion, landmark presence, face area quality
- Time-gated attendance window (first 10 minutes from class start)
- Faculty pending queue with batch approve/reject workflow
- Classroom AI analytics (headcount + engagement)
- Student profile photo lock policy: once updated, next change allowed after 14 days

### Module 2: Smart Food Stall Pre-Ordering
Endpoints:
- `POST /food/bootstrap/catalog`
- `POST /food/bootstrap/ensure`
- `POST /food/items`
- `POST /food/slots`
- `POST /food/orders`
- `POST /food/location/verify`
- `GET /food/demand`
- `GET /food/peak-times`

Included behavior:
- Pre-order by slot
- Auto-bootstrap of LPU stall catalog + full menu set + pickup slots (`10:00` to `21:00`)
- Auto-heal bootstrap (`/food/bootstrap/ensure`) to repair partial/empty shop-slot setup at runtime
- Slot capacity checks with atomic locking (crowd control)
- Demand tracking and peak-time prediction (basic analytics)
- Single-shop cart rule, idempotent checkout keys, order audit trail, and webhook-ready payment intents
- Server-side LPU geofence verification (checkout blocked outside configured radius)

### Module 3: Campus Resource & Parameter Estimation
Endpoints:
- `GET /resources/overview`
- `GET /resources/capacity-utilization`
- `GET /resources/workload-distribution`
- `GET /resources/mongo/status`

Included behavior:
- Stores blocks/classrooms/courses/faculty/students
- Computes capacity utilization
- Computes faculty workload distribution

### Module 4: Make-Up Class & Remedial Code
Endpoints:
- `POST /makeup/classes`
- `GET /makeup/classes`
- `POST /makeup/attendance/mark`
- `GET /makeup/classes/{class_id}/attendance`

Included behavior:
- Faculty creates make-up class
- System generates remedial code
- Students mark attendance with code
- Separate remedial attendance records

## 5) Puter.js AI Integration (No API Key)
This project can use Puter.js wherever AI help is needed in frontend workflows.

- Script source: `https://js.puter.com/v2/`
- AI calls are done in browser from `web/app.js`
- Model default: `gemini-3-flash-preview`

Current AI-assisted tasks in UI:
- Parent absence notice drafting
- Food rush action-plan generation
- Remedial class plan generation
- Student face matching flow (stored profile photo vs live selfie)
- Faculty classroom crowd/engagement analysis

Note:
- Puter requires internet access in browser to load SDK and run model calls.
- AI integration is optional/assistive; attendance flow still works with backend OpenCV verification.

## 6) Premium Web UI Experience
The `/ui` dashboard now includes:
- Glassmorphism cards with backdrop blur and layered depth
- Parallax scene background with animated nebula/orb elements
- 3D tilt interactions on panels and KPI cards
- Camera capture modal for live selfie/classroom image acquisition
- Role-specific dashboards:
  - Student: weekly timetable grid with active glow pulse + realtime mark flow
  - Faculty/Admin: attendance control center, batch review, classroom analysis history
- Animated visualizations:
  - Attendance donut (present vs absent)
  - Canteen demand spectrum bars
  - Capacity utilization progress bars
- Responsive behavior for desktop, tablet, and mobile

## 7) Authentication and OTP
Implemented endpoints:
- `POST /auth/register` (self-register as faculty or student)
- `POST /auth/login/request-otp` (email + password -> OTP)
- `POST /auth/login/verify-otp` (email + OTP -> access token)
- `POST /auth/logout` (clear secure server auth cookie)
- `GET /auth/me` (current authenticated user)
- `PUT /auth/me/alternate-email` (set/remove alternate Gmail for OTP fallback)

Role model:
- `faculty`: teaching/module operations
- `student`: student-safe operations (own scoped actions)

Email constraints:
- Faculty and student account emails must end with `@gmail.com`

Frontend login flow (`/ui`):
1. Register account once using role + email + password + profile details
2. Enter email + password and click **Request OTP**
3. Enter OTP and click **Verify OTP & Login**
4. Dashboard unlocks based on role

Notes:
- Auth users + OTP records are persisted in MongoDB (`auth_users`, `auth_otps`, `auth_otp_delivery`).
- Login also sets an HTTP-only session cookie (`lpu_access_token`) so auth state is not stored in browser localStorage.
- Users do not need to register again after first successful registration.
- End users never provide mailbox passwords. OTP emails are sent by one server-side sender channel (SMTP or Graph).
- Alternate OTP flow:
  - User must first complete one successful OTP login on primary email.
  - Then user can add alternate Gmail in profile.
  - Later on login screen, user may choose “Send OTP to alternate Gmail”.

## 8) Core Setup Endpoints
Use these to create data:
- `POST /core/students`
- `POST /core/faculty`
- `POST /core/courses`
- `POST /core/enroll`
- `POST /core/classrooms`
- `POST /core/course-classroom`

List endpoints:
- `GET /core/students`
- `GET /core/faculty`
- `GET /core/courses`
- `GET /core/classrooms`

## 9) Demo Seed (Disabled By Default)
`POST /demo/seed` is disabled by default in real-time mode.
To enable explicitly for testing only, set `ALLOW_DEMO_SEED=true` in `.env`.

## 10) MongoDB Primary Storage
The backend now uses MongoDB Atlas as the primary store for:
- authentication users + OTP login flow
- session identity lookups (`get_current_user`)
- attendance submission snapshots, review actions, classroom analysis snapshots

Additionally, the backend mirrors key records/events to MongoDB collections, including:
- auth events (`event_stream`)
- attendance submissions/reviews/bulk marks
- classroom analysis records
- food master/order events
- make-up class/remedial attendance events

Mongo health can be checked via:
- `GET /resources/mongo/status`
- `GET /` (includes `mongo` status block)

## 11) Payment Hardening Test Utilities
Unit test coverage for signed webhook + replay protection:
```bash
.venv/bin/python -m unittest tests.test_food_payment_hardening
```

Quick e2e smoke script (checkout -> failure -> recovery -> rating):
```bash
.venv/bin/python scripts/food_payment_e2e.py --base-url http://127.0.0.1:8000 --token "<student_access_token>"
```

Optional flags:
- `--operator-token "<faculty_or_admin_token>"` to auto-transition an order to `delivered` before rating.
- `--webhook-token "<FOOD_PAYMENT_WEBHOOK_TOKEN>"` if webhook token is enabled.
- `--signed-webhook-secret "<RAZORPAY_WEBHOOK_SECRET>"` to run signed Razorpay webhook replay checks.

## 12) Next Build Steps
- Add forgot-password/reset-password flow
- Add real notification channels (email/SMS)
- Add image storage hardening (object storage instead of raw data URLs)
- Add automated tests and CI pipeline
