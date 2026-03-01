from datetime import date, datetime, time
from enum import Enum
import re
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator

from .models import AttendanceStatus, AttendanceSubmissionStatus, FoodOrderStatus, UserRole

DEFAULT_REMEDIAL_ONLINE_LINK = "https://myclass.lpu.in/"


class StudentBase(BaseModel):
    name: str
    email: str
    registration_number: Optional[str] = None
    parent_email: Optional[str] = None
    section: Optional[str] = None
    department: str
    semester: int = Field(ge=1, le=12)


class StudentCreate(StudentBase):
    pass


class StudentOut(StudentBase):
    id: int

    class Config:
        from_attributes = True


class StudentProfilePhotoUpdate(BaseModel):
    photo_data_url: str = Field(min_length=20)


class StudentProfilePhotoOut(BaseModel):
    has_profile_photo: bool
    photo_data_url: Optional[str] = None
    can_update_now: bool = True
    locked_until: Optional[datetime] = None
    lock_days_remaining: int = 0
    registration_number: Optional[str] = None


class StudentProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    registration_number: Optional[str] = Field(default=None, min_length=3, max_length=40)
    photo_data_url: Optional[str] = Field(default=None, min_length=20)
    section: Optional[str] = Field(default=None, min_length=1, max_length=80)


class StudentProfileOut(BaseModel):
    student_id: int
    name: str
    email: str
    registration_number: Optional[str] = None
    section: Optional[str] = None
    section_updated_at: Optional[datetime] = None
    parent_email: Optional[str] = None
    department: str
    semester: int
    has_profile_photo: bool
    photo_data_url: Optional[str] = None
    can_update_photo_now: bool = True
    photo_locked_until: Optional[datetime] = None
    photo_lock_days_remaining: int = 0
    can_update_section_now: bool = True
    section_locked_until: Optional[datetime] = None
    section_lock_minutes_remaining: int = 0
    section_change_requires_faculty_approval: bool = False


class StudentEnrollmentVideoRequest(BaseModel):
    frames_data_urls: list[str] = Field(min_length=5, max_length=40)

    @model_validator(mode="after")
    def validate_frames(self):
        cleaned = [str(item or "").strip() for item in self.frames_data_urls]
        if any(len(item) < 20 for item in cleaned):
            raise ValueError("Each frame in frames_data_urls must be a valid image data URL")
        self.frames_data_urls = cleaned
        return self


class StudentEnrollmentStatusOut(BaseModel):
    has_enrollment_video: bool
    can_update_now: bool = True
    locked_until: Optional[datetime] = None
    lock_days_remaining: int = 0
    enrollment_updated_at: Optional[datetime] = None


class StudentEnrollmentVideoOut(StudentEnrollmentStatusOut):
    message: str
    valid_frames_used: int = 0
    total_frames_received: int = 0


class FacultyBase(BaseModel):
    name: str
    email: str
    department: str


class FacultyCreate(FacultyBase):
    pass


class FacultyOut(FacultyBase):
    id: int

    class Config:
        from_attributes = True


class FacultyProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    faculty_identifier: Optional[str] = Field(default=None, min_length=3, max_length=40)
    section: Optional[str] = Field(default=None, min_length=1, max_length=80)
    photo_data_url: Optional[str] = Field(default=None, min_length=20)


class FacultyProfileOut(BaseModel):
    faculty_id: int
    name: str
    email: str
    department: str
    faculty_identifier: Optional[str] = None
    section: Optional[str] = None
    section_updated_at: Optional[datetime] = None
    has_profile_photo: bool
    photo_data_url: Optional[str] = None
    can_update_photo_now: bool = True
    photo_locked_until: Optional[datetime] = None
    photo_lock_days_remaining: int = 0
    can_update_section_now: bool = True
    section_locked_until: Optional[datetime] = None
    section_lock_minutes_remaining: int = 0


class FacultyStudentSectionUpdateRequest(BaseModel):
    section: str = Field(min_length=1, max_length=80)


class CourseCreate(BaseModel):
    code: str
    title: str
    faculty_id: int


class CourseOut(BaseModel):
    id: int
    code: str
    title: str
    faculty_id: int

    class Config:
        from_attributes = True


class EnrollmentCreate(BaseModel):
    student_id: int
    course_id: int


class ClassroomCreate(BaseModel):
    block: str
    room_number: str
    capacity: int = Field(gt=0)


class ClassroomOut(BaseModel):
    id: int
    block: str
    room_number: str
    capacity: int

    class Config:
        from_attributes = True


class CourseClassroomCreate(BaseModel):
    course_id: int
    classroom_id: int


class AttendanceOverride(BaseModel):
    student_id: int
    status: AttendanceStatus


class AttendanceBulkMarkRequest(BaseModel):
    course_id: int
    faculty_id: int
    attendance_date: date
    default_status: AttendanceStatus = AttendanceStatus.PRESENT
    source: str = "faculty-web"
    overrides: list[AttendanceOverride] = Field(default_factory=list)


class AttendanceBulkMarkResponse(BaseModel):
    total_marked: int
    absent_student_ids: list[int]
    notifications_sent: int


class AttendanceSummaryItem(BaseModel):
    student_id: int
    student_name: str
    present_count: int
    absent_count: int


class NotificationOut(BaseModel):
    id: int
    student_id: int
    message: str
    channel: str
    sent_to: str

    class Config:
        from_attributes = True


class FoodItemCreate(BaseModel):
    name: str
    price: float = Field(gt=0)


class FoodItemOut(BaseModel):
    id: int
    name: str
    price: float
    is_active: bool

    class Config:
        from_attributes = True


class FoodShopCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    block: str = Field(min_length=2, max_length=80)
    owner_user_id: Optional[int] = None
    is_active: bool = True
    is_popular: bool = False
    rating: float = Field(default=4.0, ge=0.0, le=5.0)
    average_prep_minutes: int = Field(default=18, ge=2, le=180)


class FoodShopUpdate(BaseModel):
    owner_user_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_popular: Optional[bool] = None
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    average_prep_minutes: Optional[int] = Field(default=None, ge=2, le=180)


class FoodShopOut(BaseModel):
    id: int
    name: str
    block: str
    owner_user_id: Optional[int] = None
    is_active: bool
    is_popular: bool
    rating: float
    average_prep_minutes: int

    class Config:
        from_attributes = True


class FoodMenuItemCreate(BaseModel):
    shop_id: int
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=400)
    base_price: float = Field(gt=0)
    is_veg: bool = True
    spicy_level: int = Field(default=0, ge=0, le=5)
    variants: list[dict] = Field(default_factory=list)
    addons: list[dict] = Field(default_factory=list)
    available_from: Optional[time] = None
    available_to: Optional[time] = None
    prep_time_override_minutes: Optional[int] = Field(default=None, ge=1, le=300)
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    sold_out: bool = False
    is_active: bool = True


class FoodMenuItemUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=400)
    base_price: Optional[float] = Field(default=None, gt=0)
    is_veg: Optional[bool] = None
    spicy_level: Optional[int] = Field(default=None, ge=0, le=5)
    variants: Optional[list[dict]] = None
    addons: Optional[list[dict]] = None
    available_from: Optional[time] = None
    available_to: Optional[time] = None
    prep_time_override_minutes: Optional[int] = Field(default=None, ge=1, le=300)
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    sold_out: Optional[bool] = None
    is_active: Optional[bool] = None


class FoodMenuItemOut(BaseModel):
    id: int
    shop_id: int
    name: str
    description: Optional[str] = None
    base_price: float
    is_veg: bool
    spicy_level: int
    variants: list[dict] = Field(default_factory=list)
    addons: list[dict] = Field(default_factory=list)
    available_from: Optional[time] = None
    available_to: Optional[time] = None
    prep_time_override_minutes: Optional[int] = None
    stock_quantity: Optional[int] = None
    sold_out: bool
    is_active: bool

    class Config:
        from_attributes = True


class FoodCartItemMutationRequest(BaseModel):
    shop_id: int = Field(gt=0)
    menu_item_id: int = Field(gt=0)
    food_item_id: Optional[int] = Field(default=None, gt=0)
    name: str = Field(min_length=1, max_length=180)
    price: float = Field(ge=0)
    quantity_delta: int = Field(default=1, ge=-20, le=20)
    item_note: Optional[str] = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def validate_quantity_delta(self):
        if self.quantity_delta == 0:
            raise ValueError("quantity_delta cannot be 0")
        return self


class FoodCartStateUpdateRequest(BaseModel):
    checkout_preview_open: Optional[bool] = None
    checkout_delivery_point: Optional[str] = Field(default=None, max_length=120)


class FoodCartItemOut(BaseModel):
    cart_key: str
    shop_id: int
    menu_item_id: int
    food_item_id: Optional[int] = None
    name: str
    price: float
    quantity: int
    item_note: str = ""


class FoodCartOut(BaseModel):
    student_id: int
    shop_id: Optional[int] = None
    items: list[FoodCartItemOut] = Field(default_factory=list)
    total_items: int = 0
    total_quantity: int = 0
    total_price: float = 0
    checkout_preview_open: bool = False
    checkout_delivery_point: Optional[str] = None
    updated_at: Optional[datetime] = None


class BreakSlotCreate(BaseModel):
    label: str
    start_time: time
    end_time: time
    max_orders: int = Field(gt=0)


class BreakSlotOut(BaseModel):
    id: int
    label: str
    start_time: time
    end_time: time
    max_orders: int

    class Config:
        from_attributes = True


class FoodOrderCreate(BaseModel):
    student_id: int
    food_item_id: Optional[int] = None
    menu_item_id: Optional[int] = None
    shop_id: Optional[int] = None
    slot_id: int
    order_date: date
    quantity: int = Field(default=1, ge=1, le=20)
    idempotency_key: Optional[str] = Field(default=None, min_length=8, max_length=100)
    payment_reference: Optional[str] = Field(default=None, min_length=5, max_length=120)
    status_note: Optional[str] = Field(default=None, max_length=240)
    pickup_point: Optional[str] = Field(default=None, max_length=120)
    shop_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    shop_block: Optional[str] = Field(default=None, min_length=2, max_length=80)
    location_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    location_longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    location_accuracy_m: Optional[float] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_item_references(self):
        if self.food_item_id is None and self.menu_item_id is None:
            raise ValueError("Provide food_item_id or menu_item_id")
        return self


class FoodCheckoutItemCreate(BaseModel):
    menu_item_id: int = Field(gt=0)
    food_item_id: Optional[int] = Field(default=None, gt=0)
    quantity: int = Field(default=1, ge=1, le=20)
    status_note: Optional[str] = Field(default=None, max_length=240)


class FoodCheckoutCreate(BaseModel):
    student_id: int
    shop_id: Optional[int] = None
    slot_id: int
    order_date: date
    idempotency_key: Optional[str] = Field(default=None, min_length=8, max_length=100)
    pickup_point: Optional[str] = Field(default=None, max_length=120)
    shop_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    shop_block: Optional[str] = Field(default=None, min_length=2, max_length=80)
    location_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    location_longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    location_accuracy_m: Optional[float] = Field(default=None, ge=0)
    items: list[FoodCheckoutItemCreate] = Field(min_length=1, max_length=40)


class FoodOrderOut(BaseModel):
    id: int
    student_id: int
    shop_id: Optional[int] = None
    menu_item_id: Optional[int] = None
    food_item_id: int
    slot_id: int
    order_date: date
    quantity: int = 1
    unit_price: float = 0
    total_price: float = 0
    status: FoodOrderStatus
    shop_name: Optional[str] = None
    shop_block: Optional[str] = None
    idempotency_key: Optional[str] = None
    payment_status: str = "pending"
    payment_provider: Optional[str] = None
    payment_reference: Optional[str] = None
    status_note: Optional[str] = None
    assigned_runner: Optional[str] = None
    pickup_point: Optional[str] = None
    delivery_eta_minutes: Optional[int] = None
    estimated_ready_at: Optional[datetime] = None
    location_verified: bool = False
    location_latitude: Optional[float] = None
    location_longitude: Optional[float] = None
    location_accuracy_m: Optional[float] = None
    last_location_verified_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    preparing_at: Optional[datetime] = None
    out_for_delivery_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    rating_stars: Optional[int] = None
    rating_comment: Optional[str] = None
    rated_at: Optional[datetime] = None
    rating_locked_at: Optional[datetime] = None
    last_status_updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FoodOrderRatingUpdateRequest(BaseModel):
    stars: Optional[int] = Field(default=None, ge=0, le=5)
    comment: Optional[str] = Field(default=None, max_length=400)
    confirm_final: bool = False


class FoodOrderStatusUpdateRequest(BaseModel):
    status: FoodOrderStatus
    status_note: Optional[str] = Field(default=None, max_length=240)
    assigned_runner: Optional[str] = Field(default=None, max_length=120)
    pickup_point: Optional[str] = Field(default=None, max_length=120)
    delivery_eta_minutes: Optional[int] = Field(default=None, ge=1, le=300)


class FoodOrderAuditOut(BaseModel):
    id: int
    order_id: int
    event_type: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    actor_role: Optional[str] = None
    actor_id: Optional[int] = None
    actor_email: Optional[str] = None
    message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FoodPaymentIntentCreate(BaseModel):
    order_ids: list[int] = Field(min_length=1, max_length=40)
    provider: str = Field(default="sandbox", min_length=2, max_length=40)


class FoodPaymentIntentOut(BaseModel):
    payment_reference: str
    provider_order_id: Optional[str] = None
    provider: str
    status: str
    amount: float
    subtotal_amount: float = 0
    delivery_fee: float = 0
    platform_fee: float = 0
    currency: str = "INR"
    order_ids: list[int]


class FoodPaymentWebhookRequest(BaseModel):
    payment_reference: str = Field(min_length=5, max_length=120)
    status: str = Field(min_length=3, max_length=40)
    provider: str = Field(default="sandbox", min_length=2, max_length=40)
    payload: dict = Field(default_factory=dict)


class FoodPaymentRecoveryItemOut(BaseModel):
    payment_reference: str
    provider_order_id: Optional[str] = None
    status: str
    payment_state: str
    failed_reason: Optional[str] = None
    order_ids: list[int] = Field(default_factory=list)
    amount: float
    created_at: datetime
    updated_at: datetime


class FoodMetricsOut(BaseModel):
    active_orders: int
    completed_today: int
    cancelled_today: int
    rejection_today: int
    avg_preparing_minutes: float
    funnel: dict
    generated_at: datetime


class SlotDemand(BaseModel):
    slot_id: int
    slot_label: str
    orders: int
    capacity: int
    utilization_percent: float


class SlotDemandLivePulse(BaseModel):
    slot_id: int
    slot_label: str
    event_count: int
    created_count: int
    status_count: int
    payment_count: int


class SlotDemandLiveOut(BaseModel):
    order_date: date
    window_minutes: int
    synced_at: datetime
    active_orders: int
    orders_last_window: int
    status_updates_last_window: int
    payment_events_last_window: int
    hottest_slot_label: Optional[str] = None
    hottest_slot_orders: int = 0
    pulses: list[SlotDemandLivePulse] = Field(default_factory=list)


class PeakTimePrediction(BaseModel):
    slot_id: int
    slot_label: str
    average_orders: float
    predicted_rush_level: str


class FoodDeliveryLocationCheckRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: Optional[float] = Field(default=None, ge=0)


class FoodDeliveryLocationCheckOut(BaseModel):
    allowed: bool
    message: str
    distance_m: float
    radius_m: float
    max_accuracy_m: float
    center_latitude: float
    center_longitude: float


class MakeUpClassCreate(BaseModel):
    course_id: Optional[int] = Field(default=None, gt=0)
    course_code: Optional[str] = Field(default=None, min_length=2, max_length=20)
    course_title: Optional[str] = Field(default=None, min_length=2, max_length=150)
    faculty_id: int
    class_date: date
    start_time: time
    end_time: time
    topic: str
    sections: list[str] = Field(min_length=1)
    class_mode: str = Field(pattern="^(online|offline)$")
    room_number: Optional[str] = Field(default=None, min_length=1, max_length=80)
    online_link: Optional[str] = Field(default=None, min_length=5, max_length=400)
    demo_bypass_lead_time: bool = False

    @model_validator(mode="after")
    def validate_mode_fields(self):
        code = re.sub(r"\s+", "", str(self.course_code or "").strip().upper())
        title = re.sub(r"\s+", " ", str(self.course_title or "").strip())
        if code and not re.fullmatch(r"[A-Z0-9][A-Z0-9\-_/]{1,19}", code):
            raise ValueError(
                "course_code can include only letters, numbers, hyphen, underscore, and slash (2-20 chars)"
            )
        if self.course_id is None and (not code or not title):
            raise ValueError("Select an existing course or enter both course code and course title")
        self.course_code = code or None
        self.course_title = title or None

        mode = (self.class_mode or "").strip().lower()
        self.class_mode = mode
        if mode == "online":
            normalized_link = str(self.online_link or "").strip()
            self.online_link = normalized_link or DEFAULT_REMEDIAL_ONLINE_LINK
            self.room_number = None
        elif mode == "offline":
            if not self.room_number:
                raise ValueError("room_number is required for offline remedial classes")
            self.online_link = None
        return self


class MakeUpClassOut(BaseModel):
    id: int
    course_id: int
    faculty_id: int
    class_date: date
    start_time: time
    end_time: time
    topic: str
    sections: list[str] = Field(default_factory=list)
    class_mode: str
    room_number: Optional[str] = None
    online_link: Optional[str] = None
    remedial_code: str
    code_generated_at: datetime
    code_expires_at: datetime
    attendance_open_minutes: int = 15
    scheduled_at: datetime
    is_active: bool
    can_reject: bool = False

    class Config:
        from_attributes = True


class RemedialAttendanceMark(BaseModel):
    remedial_code: str
    student_id: int
    selfie_photo_data_url: Optional[str] = Field(default=None, min_length=20)
    selfie_frames_data_urls: Optional[list[str]] = Field(default=None, min_length=1, max_length=12)
    ai_match: Optional[bool] = None
    ai_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    ai_model: Optional[str] = Field(default=None, max_length=120)
    ai_reason: Optional[str] = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def sanitize_selfie_payload(self):
        if self.selfie_frames_data_urls:
            cleaned = [str(item or "").strip() for item in self.selfie_frames_data_urls]
            if not all(frame.startswith("data:image") for frame in cleaned):
                raise ValueError("Each frame in selfie_frames_data_urls must be a valid image data URL")
            self.selfie_frames_data_urls = cleaned
            if not self.selfie_photo_data_url:
                self.selfie_photo_data_url = cleaned[0]
        if self.selfie_photo_data_url:
            self.selfie_photo_data_url = str(self.selfie_photo_data_url).strip()
        return self


class RemedialCodeGenerateOut(BaseModel):
    class_id: int
    remedial_code: str
    code_generated_at: datetime
    code_expires_at: datetime


class RemedialSendMessageRequest(BaseModel):
    custom_message: Optional[str] = Field(default=None, max_length=300)


class RemedialSendMessageOut(BaseModel):
    class_id: int
    remedial_code: str
    sections: list[str] = Field(default_factory=list)
    recipients: int
    message: str


class RemedialCodeValidateRequest(BaseModel):
    remedial_code: str


class RemedialCodeValidateOut(BaseModel):
    valid: bool
    message: str
    class_id: Optional[int] = None
    course_id: Optional[int] = None
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    class_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    class_mode: Optional[str] = None
    room_number: Optional[str] = None
    online_link: Optional[str] = None
    attendance_window_open: bool = False
    attendance_window_minutes: int = 15


class RemedialMessageOut(BaseModel):
    id: int
    class_id: int
    course_id: int
    course_code: str
    course_title: str
    faculty_name: Optional[str] = None
    section: str
    message: str
    remedial_code: str
    message_type: str = "Remedial"
    class_date: date
    start_time: time
    end_time: time
    class_mode: str
    room_number: Optional[str] = None
    online_link: Optional[str] = None
    created_at: datetime


class RemedialAttendanceHistoryItemOut(BaseModel):
    class_id: int
    course_id: int
    course_code: str
    course_title: str
    class_date: date
    start_time: time
    end_time: time
    class_mode: str
    room_number: Optional[str] = None
    online_link: Optional[str] = None
    status: str
    marked_at: Optional[datetime] = None
    source: Optional[str] = None


class FacultyMessageSend(BaseModel):
    sections: list[str] = Field(min_length=1)
    message_type: str = Field(default="Announcement", min_length=3, max_length=30)
    message: str = Field(min_length=3, max_length=600)


class StudentMessageOut(BaseModel):
    id: int
    faculty_id: int
    faculty_name: Optional[str] = None
    section: str
    message_type: str
    message: str
    created_at: datetime
    class_id: Optional[int] = None
    course_id: Optional[int] = None
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    remedial_code: Optional[str] = None
    class_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    class_mode: Optional[str] = None
    room_number: Optional[str] = None
    online_link: Optional[str] = None


class CapacityUtilizationItem(BaseModel):
    course_id: int
    course_code: str
    classroom: str
    enrolled_students: int
    capacity: int
    utilization_percent: float


class FacultyWorkloadItem(BaseModel):
    faculty_id: int
    faculty_name: str
    assigned_courses: int
    total_enrolled_students: int


class AdminTopIssueItem(BaseModel):
    issue_type: str
    severity: str
    message: str
    context: dict = Field(default_factory=dict)


class AdminSummaryOut(BaseModel):
    blocks: int
    classrooms: int
    courses: int
    faculty: int
    students: int
    active_today: int
    present_today: int
    absent_today: int
    attendance_rate_today: float
    at_risk_students: int
    capacity_utilization_percent: float
    workload_distribution_percent: float
    conflict_count: int
    data_quality_score: float
    top_issues: list[AdminTopIssueItem] = Field(default_factory=list)
    mongo_status: dict = Field(default_factory=dict)
    last_updated_at: datetime
    stale_after_seconds: int = 60


class AdminCapacityItem(BaseModel):
    classroom_id: int
    block: str
    classroom: str
    classroom_label: str
    primary_course_code: str
    scheduled_slots: int
    occupied_students: int
    attendance_marked_students: int
    total_available_seats: int
    capacity: int
    utilization_percent: float
    mode: str
    last_updated_at: datetime


class AdminWorkloadItem(BaseModel):
    faculty_id: int
    faculty_name: str
    department: str
    assigned_courses: int
    assigned_hours: float
    target_hours: float
    workload_percent: float
    total_enrolled_students: int
    status: str
    last_updated_at: datetime


class AdminAlertItem(BaseModel):
    id: str
    issue_type: str
    severity: str
    message: str
    context: dict = Field(default_factory=dict)
    last_updated_at: datetime


class AdminLiveOut(BaseModel):
    summary: AdminSummaryOut
    capacity: list[AdminCapacityItem]
    workload: list[AdminWorkloadItem]
    alerts: list[AdminAlertItem]
    last_updated_at: datetime
    stale_after_seconds: int = 60


class AdminInsightsOut(BaseModel):
    profile: dict[str, Any] = Field(default_factory=dict)
    highlights: list[str] = Field(default_factory=list)
    last_updated_at: datetime


class AdminBootstrapRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


class AuthRegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    name: str = Field(min_length=2, max_length=100)
    department: str = Field(min_length=2, max_length=100)
    section: Optional[str] = Field(default=None, min_length=1, max_length=80)
    semester: Optional[int] = Field(default=None, ge=1, le=12)
    parent_email: Optional[str] = None


class AuthUserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    student_id: Optional[int] = None
    faculty_id: Optional[int] = None
    is_active: bool = True


class AuthUserOut(BaseModel):
    id: int
    name: Optional[str] = None
    email: str
    role: UserRole
    student_id: Optional[int]
    faculty_id: Optional[int]
    alternate_email: Optional[str] = None
    primary_login_verified: bool = False
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class LoginOTPRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    send_to_alternate: bool = False


class OTPRequestResponse(BaseModel):
    message: str
    expires_at: datetime
    delivered_to: Optional[str] = None
    otp_debug_code: Optional[str] = None
    cooldown_seconds: int = 30
    validity_minutes: int = 10


class AlternateEmailUpdateRequest(BaseModel):
    alternate_email: Optional[str] = None


class VerifyOTPRequest(BaseModel):
    email: str
    otp_code: str = Field(min_length=4, max_length=10)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    user: AuthUserOut


class PasswordResetOTPRequest(BaseModel):
    email: str
    registration_number: str = Field(min_length=3, max_length=40)


class PasswordResetVerifyOTPRequest(BaseModel):
    email: str
    otp_code: str = Field(min_length=4, max_length=10)


class PasswordResetVerifyResponse(BaseModel):
    message: str
    reset_token: str
    expires_at: datetime


class PasswordResetConfirmRequest(BaseModel):
    email: str
    reset_token: str = Field(min_length=20, max_length=300)
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


class ClassScheduleCreate(BaseModel):
    course_id: int
    faculty_id: int
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    classroom_label: Optional[str] = None
    is_active: bool = True


class ClassScheduleOut(BaseModel):
    id: int
    course_id: int
    faculty_id: int
    weekday: int
    start_time: time
    end_time: time
    classroom_label: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class TimetableClassOut(BaseModel):
    schedule_id: int
    course_id: int
    course_code: str
    course_title: str
    weekday: int
    start_time: time
    end_time: time
    classroom_label: Optional[str]
    class_date: date
    is_open_now: bool
    is_active_now: bool
    is_ended_now: bool
    attendance_status: Optional[str] = None
    class_kind: str = "regular"
    attendance_window_minutes: int = 10
    remedial_class_id: Optional[int] = None
    remedial_code_required: bool = False


class WeeklyTimetableOut(BaseModel):
    week_start: date
    min_navigable_date: Optional[date] = None
    classes: list[TimetableClassOut]


class DefaultTimetableLoadResponse(BaseModel):
    message: str
    created_faculty: int
    created_courses: int
    created_classrooms: int
    created_schedules: int
    created_enrollments: int
    total_classes: int


class RealtimeAttendanceMarkRequest(BaseModel):
    schedule_id: int
    selfie_photo_data_url: Optional[str] = Field(default=None, min_length=20)
    selfie_frames_data_urls: Optional[list[str]] = Field(default=None, min_length=1, max_length=12)
    ai_match: Optional[bool] = None
    ai_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    ai_reason: Optional[str] = None
    ai_model: Optional[str] = "gemini-3-flash-preview"

    @model_validator(mode="after")
    def validate_selfie_payload(self):
        if not self.selfie_photo_data_url and not self.selfie_frames_data_urls:
            raise ValueError("Provide selfie_photo_data_url or selfie_frames_data_urls")
        if self.selfie_frames_data_urls:
            cleaned = [str(item or "").strip() for item in self.selfie_frames_data_urls]
            if any(len(item) < 20 for item in cleaned):
                raise ValueError("Each frame in selfie_frames_data_urls must be a valid image data URL")
            self.selfie_frames_data_urls = cleaned
            if not self.selfie_photo_data_url:
                self.selfie_photo_data_url = cleaned[0]
        return self


class RealtimeAttendanceMarkResponse(BaseModel):
    submission_id: int
    status: AttendanceSubmissionStatus
    requires_faculty_review: bool
    message: str
    verification_engine: str = "ai"
    verification_confidence: float = 0.0
    verification_reason: Optional[str] = None


class StudentAttendanceHistoryItemOut(BaseModel):
    class_date: date
    start_time: time
    end_time: time
    course_code: str
    course_title: str
    faculty_name: str
    status: AttendanceStatus
    source: str


class StudentAttendanceHistoryOut(BaseModel):
    records: list[StudentAttendanceHistoryItemOut]


class StudentCourseAttendanceAggregateOut(BaseModel):
    course_id: int
    course_code: str
    course_title: str
    faculty_name: str
    attended_classes: int
    delivered_classes: int
    attendance_percent: float
    last_attended_on: Optional[date] = None


class StudentAttendanceAggregateOut(BaseModel):
    aggregate_percent: float
    attended_total: int
    delivered_total: int
    courses: list[StudentCourseAttendanceAggregateOut]


class AttendanceSubmissionOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    status: AttendanceSubmissionStatus
    ai_confidence: float
    ai_reason: Optional[str]
    submitted_at: datetime


class FacultyAttendanceDashboardOut(BaseModel):
    schedule_id: int
    class_date: date
    total_students: int
    present: int
    pending_review: int
    absent: int
    submissions: list[AttendanceSubmissionOut]


class FacultyReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


class FacultyBatchReviewRequest(BaseModel):
    schedule_id: int
    class_date: date
    submission_ids: list[int] = Field(min_length=1)
    action: FacultyReviewAction
    note: Optional[str] = None


class FacultyBatchReviewResponse(BaseModel):
    updated: int
    approved: int
    rejected: int


class ClassroomAnalysisCreate(BaseModel):
    schedule_id: int
    class_date: date
    photo_data_url: str = Field(min_length=20)
    estimated_headcount: int = Field(ge=0)
    engagement_level: str
    ai_summary: Optional[str] = None
    ai_model: str = "gemini-3-flash-preview"


class ClassroomAnalysisOut(BaseModel):
    id: int
    schedule_id: int
    class_date: date
    estimated_headcount: int
    engagement_level: str
    ai_summary: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class RazorpayConfigOut(BaseModel):
    key_id: str


class RazorpayVerifyRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


class RazorpayFailureRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: Optional[str] = None
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    error_source: Optional[str] = None
    error_step: Optional[str] = None
    error_reason: Optional[str] = None
