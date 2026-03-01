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
    profile_photo_updated_at = Column(DateTime, nullable=True)
    profile_photo_locked_until = Column(DateTime, nullable=True)
    profile_face_template_json = Column(Text, nullable=True)
    profile_face_template_updated_at = Column(DateTime, nullable=True)
    enrollment_video_template_json = Column(Text, nullable=True)
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


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    message = Column(String(500), nullable=False)
    channel = Column(String(50), nullable=False, default="simulated")
    sent_to = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


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
    ai_match = Column(Boolean, nullable=False, default=False)
    ai_confidence = Column(Float, nullable=False, default=0.0)
    ai_model = Column(String(80), nullable=True)
    ai_reason = Column(String(600), nullable=True)
    status = Column(Enum(AttendanceSubmissionStatus), nullable=False, index=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_by_faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_note = Column(String(300), nullable=True)


class ClassroomAnalysis(Base):
    __tablename__ = "classroom_analyses"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("class_schedules.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False, index=True)
    class_date = Column(Date, nullable=False, index=True)
    photo_data_url = Column(Text, nullable=True)
    estimated_headcount = Column(Integer, nullable=False)
    engagement_level = Column(String(80), nullable=False)
    ai_summary = Column(String(800), nullable=True)
    ai_model = Column(String(80), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


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
