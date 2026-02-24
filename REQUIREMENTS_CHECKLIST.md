# Mandatory Requirements Checklist (from LPU_Project_2.pdf)

## Scope extracted from PDF
Mandatory modules identified:
1. Smart Attendance Management System
2. Smart Food Stall Pre-Ordering System
3. Campus Resource & Parameter Estimation
4. Make-Up Class & Remedial Code Module

## Implementation Mapping

### 1) Smart Attendance Management
Required:
- Faculty one-click attendance
- Optional CCTV/image source
- Instant update
- Automatic absentee detection
- Notifications to students/parents (simulated)
- Realtime facial attendance (student live selfie vs stored face)
- Time-gated attendance (open for first 10 minutes)
- Faculty pending-review approval flow

Implemented:
- `POST /attendance/mark-bulk`
- `GET /attendance/absentees`
- `GET /attendance/summary`
- `GET /attendance/notifications`
- `GET /attendance/student/timetable`
- `PUT /attendance/student/profile-photo`
- `POST /attendance/realtime/mark`
- `GET /attendance/faculty/dashboard`
- `POST /attendance/faculty/review`
- `POST /attendance/faculty/classroom-analysis`

Status: **In Progress (backend + role UI implemented, advanced hardening pending)**

### 2) Smart Food Stall Pre-Ordering
Required:
- Pre-order via web/app
- Slot selection
- Reduce congestion
- Track demand and peak times

Implemented:
- `POST /food/orders`
- `GET /food/demand`
- `GET /food/peak-times`
- Slot capacity checks in order creation

Status: **Started (MVP complete for backend API)**

### 3) Campus Resources & Estimation
Required:
- Store/process blocks, classrooms, courses, faculty, students
- Compute capacity utilization
- Compute workload distribution

Implemented:
- Core setup endpoints under `/core/*`
- `GET /resources/overview`
- `GET /resources/capacity-utilization`
- `GET /resources/workload-distribution`

Status: **Started (MVP complete for backend API)**

### 4) Make-Up & Remedial Code
Required:
- Faculty schedules make-up classes
- System generates remedial code
- Student attendance via code
- Separate attendance records

Implemented:
- `POST /makeup/classes`
- `POST /makeup/attendance/mark`
- `GET /makeup/classes/{class_id}/attendance`

Status: **Started (MVP complete for backend API)**

## Not Yet Started
- Real notification channels (email/SMS)
- Automated tests and CI pipeline
- Production image storage and privacy policy layer

## Security Layer Status
- Role-based auth implemented (`admin`, `faculty`, `student`)
- OTP login flow implemented with two-step verification
- Frontend enforces authenticated dashboard access and role-aware UI controls
- SQLite schema safety migration added for new profile photo column on legacy DBs

## Optional AI Integration Status
- Puter.js client-side integration added in `web/app.js`
- Used for drafting notices, planning suggestions, facial attendance checks, and classroom analysis without API keys
- This supports AI-assisted workflows while keeping mandatory modules functional without AI

## MongoDB Integration Status
- PyMongo integrated with Atlas connection via `.env` (`MONGO_URI`, `MONGO_DB_NAME`)
- Mongo is now used as primary storage for auth/login identity and attendance snapshots
- Core operational writes are mirrored to Mongo collections for analytics/history
- Health/inspection endpoint added: `GET /resources/mongo/status`
- SQLite data remains available for compatibility modules and seed synchronization
