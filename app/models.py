import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import relationship

from .database import Base


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"


class FoodOrderStatus(str, enum.Enum):
    PLACED = "placed"
    VERIFIED = "verified"
    PREPARING = "preparing"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    READY = "ready"
    COLLECTED = "collected"
    REJECTED = "rejected"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    FACULTY = "faculty"
    STUDENT = "student"
    OWNER = "owner"


class AttendanceSubmissionStatus(str, enum.Enum):
    VERIFIED = "verified"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class AttendanceRectificationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AttendanceRecoveryRiskLevel(str, enum.Enum):
    WATCH = "watch"
    HIGH = "high"
    CRITICAL = "critical"


class AttendanceRecoveryPlanStatus(str, enum.Enum):
    ACTIVE = "active"
    ESCALATED = "escalated"
    RECOVERED = "recovered"
    CANCELLED = "cancelled"


class AttendanceRecoveryActionType(str, enum.Enum):
    REMEDIAL_SLOT = "remedial_slot"
    FACULTY_NUDGE = "faculty_nudge"
    OFFICE_HOUR_INVITE = "office_hour_invite"
    CATCH_UP_TASK = "catch_up_task"
    PARENT_ALERT = "parent_alert"


class AttendanceRecoveryActionStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class RMSCaseStatus(str, enum.Enum):
    NEW = "new"
    TRIAGE = "triage"
    ASSIGNED = "assigned"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLOSED = "closed"


class RMSCasePriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RMSAttendanceCorrectionStatus(str, enum.Enum):
    PENDING_ADMIN_APPROVAL = "pending_admin_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class FraudRiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IdentityVerificationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    VERIFIED = "verified"
    FLAGGED = "flagged"
    REJECTED = "rejected"


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    registration_number = Column(String(40), unique=True, nullable=True, index=True)
    parent_email = Column(String(120), nullable=True)
    section = Column(String(80), nullable=True, index=True)
    section_updated_at = Column(DateTime, nullable=True)
    profile_photo_data_url = Column(Text, nullable=True)
    profile_photo_object_key = Column(String(240), nullable=True, index=True)
    profile_photo_updated_at = Column(DateTime, nullable=True)
    profile_photo_locked_until = Column(DateTime, nullable=True)
    profile_face_template_json = Column(Text().with_variant(LONGTEXT(), "mysql"), nullable=True)
    profile_face_template_updated_at = Column(DateTime, nullable=True)
    enrollment_video_template_json = Column(Text().with_variant(LONGTEXT(), "mysql"), nullable=True)
    enrollment_video_updated_at = Column(DateTime, nullable=True)
    enrollment_video_locked_until = Column(DateTime, nullable=True)
    department = Column(String(100), nullable=False)
    semester = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")


class Faculty(Base):
    __tablename__ = "faculty"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    faculty_identifier = Column(String(40), unique=True, nullable=True, index=True)
    section = Column(String(80), nullable=True)
    section_updated_at = Column(DateTime, nullable=True)
    profile_photo_data_url = Column(Text, nullable=True)
    profile_photo_object_key = Column(String(240), nullable=True, index=True)
    profile_photo_updated_at = Column(DateTime, nullable=True)
    profile_photo_locked_until = Column(DateTime, nullable=True)
    department = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    courses = relationship("Course", back_populates="faculty")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(String(150), nullable=False)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False)

    faculty = relationship("Faculty", back_populates="courses")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_student_course"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")


class Classroom(Base):
    __tablename__ = "classrooms"
    __table_args__ = (UniqueConstraint("block", "room_number", name="uq_block_room"),)

    id = Column(Integer, primary_key=True, index=True)
    block = Column(String(50), nullable=False)
    room_number = Column(String(20), nullable=False)
    capacity = Column(Integer, nullable=False)


class CourseClassroom(Base):
    __tablename__ = "course_classrooms"
    __table_args__ = (UniqueConstraint("course_id", name="uq_course_classroom"),)

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "attendance_date", name="uq_attendance_day"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    marked_by_faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False)
    attendance_date = Column(Date, nullable=False, index=True)
    status = Column(Enum(AttendanceStatus), nullable=False)
    source = Column(String(50), nullable=False, default="faculty-web", server_default="faculty-web")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    computed_from_event_id = Column(Integer, ForeignKey("attendance_events.id"), nullable=True, index=True)


class AttendanceEvent(Base):
    __tablename__ = "attendance_events"
    __table_args__ = (
        UniqueConstraint("event_key", name="uq_attendance_event_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    event_key = Column(String(80), nullable=False, unique=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    status = Column(Enum(AttendanceStatus), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True, index=True)
    actor_faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True, index=True)
    actor_role = Column(String(20), nullable=True, index=True)
    source = Column(String(80), nullable=False, default="attendance-event", index=True)
    note = Column(String(600), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    message = Column(String(500), nullable=False)
    channel = Column(String(50), nullable=False, default="simulated")
    sent_to = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class NotificationDeliveryAttempt(Base):
    __tablename__ = "notification_delivery_attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    recovery_action_id = Column(
        Integer,
        ForeignKey("attendance_recovery_actions.id"),
        nullable=True,
        index=True,
    )
    notification_type = Column(String(80), nullable=False, index=True)
    recipient_email = Column(String(120), nullable=False, index=True)
    channel = Column(String(50), nullable=False, default="worker-email", index=True)
    status = Column(String(24), nullable=False, default="pending", index=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    error_message = Column(String(600), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class SchedulerLease(Base):
    __tablename__ = "scheduler_leases"

    job_name = Column(String(120), primary_key=True, index=True)
    owner_id = Column(String(120), nullable=False, index=True)
    lease_expires_at = Column(DateTime, nullable=True, index=True)
    next_due_at = Column(DateTime, nullable=True, index=True)
    heartbeat_at = Column(DateTime, nullable=True, index=True)
    last_started_at = Column(DateTime, nullable=True, index=True)
    last_completed_at = Column(DateTime, nullable=True, index=True)
    last_status = Column(String(24), nullable=False, default="pending", index=True)
    last_error = Column(String(600), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AttendanceRecoveryPlan(Base):
    __tablename__ = "attendance_recovery_plans"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True, index=True)
    risk_level = Column(Enum(AttendanceRecoveryRiskLevel), nullable=False, index=True)
    status = Column(
        Enum(AttendanceRecoveryPlanStatus),
        nullable=False,
        default=AttendanceRecoveryPlanStatus.ACTIVE,
        index=True,
    )
    attendance_percent = Column(Float, nullable=False, default=0.0)
    present_count = Column(Integer, nullable=False, default=0)
    absent_count = Column(Integer, nullable=False, default=0)
    delivered_count = Column(Integer, nullable=False, default=0)
    consecutive_absences = Column(Integer, nullable=False, default=0)
    missed_remedials = Column(Integer, nullable=False, default=0)
    recommended_makeup_class_id = Column(Integer, ForeignKey("makeup_classes.id"), nullable=True, index=True)
    parent_alert_allowed = Column(Boolean, nullable=False, default=False)
    recovery_due_at = Column(DateTime, nullable=True, index=True)
    summary = Column(String(700), nullable=False)
    last_absent_on = Column(Date, nullable=True, index=True)
    last_evaluated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AttendanceRecoveryAction(Base):
    __tablename__ = "attendance_recovery_actions"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("attendance_recovery_plans.id"), nullable=False, index=True)
    action_type = Column(Enum(AttendanceRecoveryActionType), nullable=False, index=True)
    status = Column(
        Enum(AttendanceRecoveryActionStatus),
        nullable=False,
        default=AttendanceRecoveryActionStatus.PENDING,
        index=True,
    )
    title = Column(String(160), nullable=False)
    description = Column(String(900), nullable=False)
    recipient_role = Column(String(30), nullable=False, index=True)
    recipient_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True, index=True)
    recipient_email = Column(String(120), nullable=True, index=True)
    target_makeup_class_id = Column(Integer, ForeignKey("makeup_classes.id"), nullable=True, index=True)
    scheduled_for = Column(DateTime, nullable=True, index=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    outcome_note = Column(String(600), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class FoodItem(Base):
    __tablename__ = "food_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class FoodShop(Base):
    __tablename__ = "food_shops"
    __table_args__ = (UniqueConstraint("name", "block", name="uq_food_shop_name_block"),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    block = Column(String(80), nullable=False, index=True)
    owner_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_popular = Column(Boolean, default=False, nullable=False)
    rating = Column(Float, default=4.0, nullable=False)
    average_prep_minutes = Column(Integer, default=18, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class FoodMenuItem(Base):
    __tablename__ = "food_menu_items"
    __table_args__ = (UniqueConstraint("shop_id", "name", name="uq_food_menu_item_shop_name"),)

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("food_shops.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(String(400), nullable=True)
    base_price = Column(Float, nullable=False)
    is_veg = Column(Boolean, default=True, nullable=False)
    spicy_level = Column(Integer, default=0, nullable=False)
    variants_json = Column(Text, nullable=True)
    addons_json = Column(Text, nullable=True)
    available_from = Column(Time, nullable=True)
    available_to = Column(Time, nullable=True)
    prep_time_override_minutes = Column(Integer, nullable=True)
    stock_quantity = Column(Integer, nullable=True)
    sold_out = Column(Boolean, default=False, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class BreakSlot(Base):
    __tablename__ = "break_slots"
    __table_args__ = (UniqueConstraint("label", name="uq_break_slot_label"),)

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(50), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    max_orders = Column(Integer, nullable=False)


class FoodOrder(Base):
    __tablename__ = "food_orders"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    shop_id = Column(Integer, ForeignKey("food_shops.id"), nullable=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("food_menu_items.id"), nullable=True, index=True)
    food_item_id = Column(Integer, ForeignKey("food_items.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("break_slots.id"), nullable=False)
    order_date = Column(Date, nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False, default=0.0)
    total_price = Column(Float, nullable=False, default=0.0)
    status = Column(Enum(FoodOrderStatus), nullable=False, default=FoodOrderStatus.PLACED)
    shop_name = Column(String(120), nullable=True)
    shop_block = Column(String(80), nullable=True)
    idempotency_key = Column(String(100), nullable=True, index=True)
    payment_status = Column(String(40), nullable=False, default="pending", index=True)
    payment_provider = Column(String(40), nullable=True)
    payment_reference = Column(String(120), nullable=True, index=True)
    status_note = Column(String(240), nullable=True)
    assigned_runner = Column(String(120), nullable=True)
    pickup_point = Column(String(120), nullable=True)
    delivery_eta_minutes = Column(Integer, nullable=True)
    estimated_ready_at = Column(DateTime, nullable=True)
    location_verified = Column(Boolean, nullable=False, default=False)
    location_latitude = Column(Float, nullable=True)
    location_longitude = Column(Float, nullable=True)
    location_accuracy_m = Column(Float, nullable=True)
    last_location_verified_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    preparing_at = Column(DateTime, nullable=True)
    out_for_delivery_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancel_reason = Column(String(240), nullable=True)
    rating_stars = Column(Integer, nullable=True)
    rating_comment = Column(String(400), nullable=True)
    rated_at = Column(DateTime, nullable=True)
    rating_locked_at = Column(DateTime, nullable=True)
    last_status_updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class FoodPayment(Base):
    __tablename__ = "food_payments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    provider = Column(String(40), nullable=False, default="sandbox")
    payment_reference = Column(String(120), nullable=False, unique=True, index=True)
    provider_order_id = Column(String(120), nullable=True, index=True)
    provider_payment_id = Column(String(120), nullable=True, index=True)
    provider_signature = Column(String(200), nullable=True)
    order_state = Column(String(40), nullable=False, default="created", index=True)
    payment_state = Column(String(40), nullable=False, default="created", index=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    failed_reason = Column(String(300), nullable=True)
    status = Column(String(40), nullable=False, default="created", index=True)
    order_ids_json = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    webhook_payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    verified_at = Column(DateTime, nullable=True)


class FoodOrderAudit(Base):
    __tablename__ = "food_order_audit"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("food_orders.id"), nullable=False, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    from_status = Column(String(40), nullable=True)
    to_status = Column(String(40), nullable=True)
    actor_role = Column(String(40), nullable=True)
    actor_id = Column(Integer, nullable=True)
    actor_email = Column(String(120), nullable=True)
    message = Column(String(600), nullable=True)
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MakeUpClass(Base):
    __tablename__ = "makeup_classes"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False)
    class_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    topic = Column(String(200), nullable=False)
    sections_json = Column(Text, nullable=False, default="[]")
    class_mode = Column(String(20), nullable=False, default="offline")
    room_number = Column(String(80), nullable=True)
    online_link = Column(String(400), nullable=True)
    remedial_code = Column(String(16), unique=True, nullable=False, index=True)
    code_generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    code_expires_at = Column(DateTime, nullable=False)
    attendance_open_minutes = Column(Integer, nullable=False, default=15)
    scheduled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RemedialAttendance(Base):
    __tablename__ = "remedial_attendance"
    __table_args__ = (UniqueConstraint("makeup_class_id", "student_id", name="uq_remedial_attendance"),)

    id = Column(Integer, primary_key=True, index=True)
    makeup_class_id = Column(Integer, ForeignKey("makeup_classes.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    source = Column(String(50), nullable=False, default="remedial-code")
    marked_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RemedialMessage(Base):
    __tablename__ = "remedial_messages"
    __table_args__ = (
        UniqueConstraint("makeup_class_id", "student_id", name="uq_remedial_message_class_student"),
    )

    id = Column(Integer, primary_key=True, index=True)
    makeup_class_id = Column(Integer, ForeignKey("makeup_classes.id"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    section = Column(String(80), nullable=False, index=True)
    remedial_code = Column(String(16), nullable=False, index=True)
    message = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)


class FacultyMessage(Base):
    __tablename__ = "faculty_messages"
    __table_args__ = (UniqueConstraint("faculty_id", "student_id", "created_at", name="uq_faculty_message"),)

    id = Column(Integer, primary_key=True, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    section = Column(String(80), nullable=False, index=True)
    message_type = Column(String(30), nullable=False, default="Announcement")
    message = Column(String(600), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)


class SupportQueryMessage(Base):
    __tablename__ = "support_query_messages"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False, index=True)
    section = Column(String(80), nullable=False, index=True)
    category = Column(String(30), nullable=False, default="Attendance")
    subject = Column(String(140), nullable=False)
    message = Column(String(1000), nullable=False)
    sender_role = Column(String(20), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True, index=True)


class SaarthiSession(Base):
    __tablename__ = "saarthi_sessions"
    __table_args__ = (
        UniqueConstraint("student_id", "week_start_date", name="uq_saarthi_student_week"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False, index=True)
    week_start_date = Column(Date, nullable=False, index=True)
    mandatory_date = Column(Date, nullable=False, index=True)
    attendance_credit_minutes = Column(Integer, nullable=False, default=0)
    attendance_marked_at = Column(DateTime, nullable=True, index=True)
    attendance_record_id = Column(Integer, ForeignKey("attendance_records.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    last_message_at = Column(DateTime, nullable=True, index=True)


class SaarthiMessage(Base):
    __tablename__ = "saarthi_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("saarthi_sessions.id"), nullable=False, index=True)
    sender_role = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class ClassSchedule(Base):
    __tablename__ = "class_schedules"
    __table_args__ = (
        UniqueConstraint("course_id", "weekday", "start_time", name="uq_course_weekday_start"),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False, index=True)
    weekday = Column(Integer, nullable=False, index=True)  # 0=Mon ... 6=Sun
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    classroom_label = Column(String(120), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TimetableOverride(Base):
    __tablename__ = "timetable_overrides"
    __table_args__ = (
        UniqueConstraint(
            "scope_key",
            "source_weekday",
            "source_start_time",
            name="uq_timetable_override_scope_source_slot",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String(20), nullable=False, index=True)
    scope_key = Column(String(120), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    section = Column(String(80), nullable=True, index=True)
    source_weekday = Column(Integer, nullable=False, index=True)
    source_start_time = Column(Time, nullable=False)
    schedule_id = Column(Integer, ForeignKey("class_schedules.id"), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    updated_by_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AttendanceSubmission(Base):
    __tablename__ = "attendance_submissions"
    __table_args__ = (
        UniqueConstraint("schedule_id", "student_id", "class_date", name="uq_submission_per_class"),
    )

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("class_schedules.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    class_date = Column(Date, nullable=False, index=True)
    selfie_photo_data_url = Column(Text, nullable=True)
    selfie_photo_object_key = Column(String(240), nullable=True, index=True)
    ai_match = Column(Boolean, nullable=False, default=False)
    ai_confidence = Column(Float, nullable=False, default=0.0)
    ai_model = Column(String(80), nullable=True)
    ai_reason = Column(String(600), nullable=True)
    status = Column(Enum(AttendanceSubmissionStatus), nullable=False, index=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_by_faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_note = Column(String(300), nullable=True)


class AttendanceRectificationRequest(Base):
    __tablename__ = "attendance_rectification_requests"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "schedule_id",
            "class_date",
            name="uq_attendance_rectification_per_class",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    schedule_id = Column(Integer, ForeignKey("class_schedules.id"), nullable=False, index=True)
    class_date = Column(Date, nullable=False, index=True)
    class_start_time = Column(Time, nullable=False)
    class_end_time = Column(Time, nullable=False)
    proof_note = Column(String(1200), nullable=False)
    proof_photo_data_url = Column(Text, nullable=True)
    proof_photo_object_key = Column(String(240), nullable=True, index=True)
    status = Column(Enum(AttendanceRectificationStatus), nullable=False, index=True)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    reviewed_at = Column(DateTime, nullable=True, index=True)
    reviewed_by_faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True)
    review_note = Column(String(600), nullable=True)


class ClassroomAnalysis(Base):
    __tablename__ = "classroom_analyses"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("class_schedules.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False, index=True)
    class_date = Column(Date, nullable=False, index=True)
    photo_data_url = Column(Text, nullable=True)
    photo_object_key = Column(String(240), nullable=True, index=True)
    estimated_headcount = Column(Integer, nullable=False)
    engagement_level = Column(String(80), nullable=False)
    ai_summary = Column(String(800), nullable=True)
    ai_model = Column(String(80), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class StudentGrade(Base):
    __tablename__ = "student_grades"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_student_grade_course"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True, index=True)
    grade_letter = Column(String(8), nullable=False, index=True)
    grade_points = Column(Float, nullable=True)
    marks_percent = Column(Float, nullable=True)
    remark = Column(String(400), nullable=True)
    graded_by_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True, index=True)
    graded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AuthUser(Base):
    __tablename__ = "auth_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(Enum(UserRole), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True, nullable=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), unique=True, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student")
    faculty = relationship("Faculty")


class AuthOTP(Base):
    __tablename__ = "auth_otps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=False, index=True)
    otp_hash = Column(String(256), nullable=False)
    otp_salt = Column(String(64), nullable=False)
    purpose = Column(String(40), nullable=False, default="login", index=True)
    attempts_count = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuthOTPDelivery(Base):
    __tablename__ = "auth_otp_delivery"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=False, index=True)
    destination = Column(String(120), nullable=False)
    otp_code = Column(String(10), nullable=False)
    channel = Column(String(40), nullable=False, default="simulated-email")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    sid = Column(String(120), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=False, index=True)
    device_id = Column(String(120), nullable=True, index=True)
    user_agent = Column(String(300), nullable=True)
    ip_address = Column(String(80), nullable=True)
    current_refresh_hash = Column(String(256), nullable=False)
    current_refresh_salt = Column(String(64), nullable=False)
    previous_refresh_hash = Column(String(256), nullable=True)
    previous_refresh_salt = Column(String(64), nullable=True)
    refresh_expires_at = Column(DateTime, nullable=False, index=True)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    rotated_at = Column(DateTime, nullable=True, index=True)
    revoked_at = Column(DateTime, nullable=True, index=True)
    revoked_reason = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AuthTokenRevocation(Base):
    __tablename__ = "auth_token_revocations"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(120), nullable=False, unique=True, index=True)
    sid = Column(String(120), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True, index=True)
    token_type = Column(String(20), nullable=False, default="access", index=True)
    reason = Column(String(200), nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class IdentityVerificationCase(Base):
    __tablename__ = "identity_verification_cases"

    id = Column(Integer, primary_key=True, index=True)
    workflow_key = Column(String(80), nullable=False, index=True)
    subject_role = Column(String(30), nullable=False, index=True)
    auth_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True, index=True)
    applicant_email = Column(String(120), nullable=True, index=True)
    external_subject_key = Column(String(120), nullable=True, index=True)
    status = Column(
        Enum(IdentityVerificationStatus),
        nullable=False,
        default=IdentityVerificationStatus.PENDING,
        index=True,
    )
    risk_score = Column(Float, nullable=False, default=0.0, index=True)
    risk_level = Column(
        Enum(FraudRiskLevel),
        nullable=False,
        default=FraudRiskLevel.LOW,
        index=True,
    )
    requested_checks_json = Column(Text, nullable=False, default="[]")
    completed_checks_json = Column(Text, nullable=False, default="[]")
    latest_reason = Column(String(500), nullable=True)
    graph_summary_json = Column(Text, nullable=False, default="{}")
    evidence_json = Column(Text, nullable=False, default="{}")
    reviewed_by_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True, index=True)
    reviewed_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    signals = relationship("IdentityRiskSignal", back_populates="case", cascade="all, delete-orphan")
    artifacts = relationship("IdentityVerificationArtifact", back_populates="case", cascade="all, delete-orphan")


class IdentityRiskSignal(Base):
    __tablename__ = "identity_risk_signals"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("identity_verification_cases.id"), nullable=False, index=True)
    signal_type = Column(String(80), nullable=False, index=True)
    severity = Column(Enum(FraudRiskLevel), nullable=False, default=FraudRiskLevel.LOW, index=True)
    score_delta = Column(Float, nullable=False, default=0.0)
    is_blocking = Column(Boolean, nullable=False, default=False, index=True)
    reason = Column(String(500), nullable=False)
    evidence_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    case = relationship("IdentityVerificationCase", back_populates="signals")


class IdentityVerificationArtifact(Base):
    __tablename__ = "identity_verification_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("identity_verification_cases.id"), nullable=False, index=True)
    artifact_type = Column(String(80), nullable=False, index=True)
    media_object_key = Column(String(240), nullable=False, index=True)
    content_type = Column(String(120), nullable=False)
    size_bytes = Column(Integer, nullable=False, default=0)
    checksum_sha256 = Column(String(64), nullable=False, index=True)
    verification_state = Column(String(40), nullable=False, default="submitted", index=True)
    document_match_score = Column(Float, nullable=True)
    face_match_confidence = Column(Float, nullable=True)
    liveness_passed = Column(Boolean, nullable=True)
    note = Column(String(500), nullable=True)
    extracted_identity_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    case = relationship("IdentityVerificationCase", back_populates="artifacts")


class MediaObject(Base):
    __tablename__ = "media_objects"

    id = Column(Integer, primary_key=True, index=True)
    object_key = Column(String(240), nullable=False, unique=True, index=True)
    bucket = Column(String(80), nullable=False, default="profile-media", index=True)
    owner_table = Column(String(80), nullable=False, index=True)
    owner_id = Column(Integer, nullable=True, index=True)
    media_kind = Column(String(80), nullable=False, index=True)
    content_type = Column(String(120), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    checksum_sha256 = Column(String(64), nullable=False, index=True)
    retention_until = Column(DateTime, nullable=True, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(Integer, primary_key=True, index=True)
    destination = Column(String(40), nullable=False, default="mongo", index=True)
    collection_name = Column(String(120), nullable=False, index=True)
    operation = Column(String(20), nullable=False, default="upsert")
    payload_json = Column(Text, nullable=False)
    upsert_filter_json = Column(Text, nullable=True)
    required = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    available_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True, index=True)
    last_error = Column(String(900), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class RMSCase(Base):
    __tablename__ = "rms_cases"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True, index=True)
    section = Column(String(80), nullable=False, index=True)
    category = Column(String(30), nullable=False, default="Other", index=True)
    subject = Column(String(140), nullable=False)
    status = Column(Enum(RMSCaseStatus), nullable=False, default=RMSCaseStatus.NEW, index=True)
    priority = Column(Enum(RMSCasePriority), nullable=False, default=RMSCasePriority.MEDIUM, index=True)
    assigned_to_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True, index=True)
    created_from_message_id = Column(Integer, ForeignKey("support_query_messages.id"), nullable=True, index=True)
    first_response_due_at = Column(DateTime, nullable=True, index=True)
    resolution_due_at = Column(DateTime, nullable=True, index=True)
    first_responded_at = Column(DateTime, nullable=True)
    last_message_at = Column(DateTime, nullable=True)
    is_escalated = Column(Boolean, nullable=False, default=False, index=True)
    escalated_at = Column(DateTime, nullable=True, index=True)
    escalation_reason = Column(String(400), nullable=True)
    closed_at = Column(DateTime, nullable=True, index=True)
    reopened_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class RMSCaseAuditLog(Base):
    __tablename__ = "rms_case_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("rms_cases.id"), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True, index=True)
    actor_role = Column(String(20), nullable=True, index=True)
    action = Column(String(80), nullable=False, index=True)
    from_status = Column(Enum(RMSCaseStatus), nullable=True)
    to_status = Column(Enum(RMSCaseStatus), nullable=True)
    note = Column(String(600), nullable=True)
    evidence_ref = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class RMSAttendanceCorrectionRequest(Base):
    __tablename__ = "rms_attendance_corrections"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    requested_status = Column(Enum(AttendanceStatus), nullable=False, index=True)
    previous_status = Column(Enum(AttendanceStatus), nullable=True)
    reason = Column(String(600), nullable=False)
    evidence_ref = Column(Text, nullable=False)
    requested_by_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=False, index=True)
    requested_by_role = Column(String(20), nullable=False, index=True)
    status = Column(
        Enum(RMSAttendanceCorrectionStatus),
        nullable=False,
        default=RMSAttendanceCorrectionStatus.PENDING_ADMIN_APPROVAL,
        index=True,
    )
    review_note = Column(String(600), nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True, index=True)
    reviewed_at = Column(DateTime, nullable=True, index=True)
    applied_record_id = Column(Integer, ForeignKey("attendance_records.id"), nullable=True, index=True)
    applied_at = Column(DateTime, nullable=True, index=True)
    is_high_impact = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class CopilotAuditLog(Base):
    __tablename__ = "copilot_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=False, index=True)
    actor_role = Column(String(20), nullable=False, index=True)
    session_id = Column(String(120), nullable=True, index=True)
    query_text = Column(String(1000), nullable=False)
    intent = Column(String(80), nullable=False, index=True)
    outcome = Column(String(20), nullable=False, index=True)
    scope = Column(String(160), nullable=True, index=True)
    target_student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    target_course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    target_section = Column(String(80), nullable=True, index=True)
    explanation_json = Column(Text, nullable=False, default="[]")
    evidence_json = Column(Text, nullable=False, default="[]")
    actions_json = Column(Text, nullable=False, default="[]")
    result_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AdminPolicySetting(Base):
    __tablename__ = "admin_policy_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(120), nullable=False, unique=True, index=True)
    value_json = Column(Text, nullable=False, default="{}")
    updated_by_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class RoleDelegationLog(Base):
    __tablename__ = "role_delegation_logs"

    id = Column(Integer, primary_key=True, index=True)
    target_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=False, index=True)
    from_role = Column(Enum(UserRole), nullable=True)
    to_role = Column(Enum(UserRole), nullable=False)
    delegated_by_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=False, index=True)
    reason = Column(String(400), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class BreakGlassAccessLog(Base):
    __tablename__ = "break_glass_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=False, index=True)
    actor_email = Column(String(120), nullable=False, index=True)
    scope = Column(String(200), nullable=False, default="global")
    reason = Column(String(500), nullable=False)
    ticket_ref = Column(String(80), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
