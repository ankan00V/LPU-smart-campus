from datetime import date, datetime, time
from enum import Enum
import re
from typing import Any, Optional

from pydantic import Field, model_validator

from .models import (
    AttendanceRecoveryActionStatus,
    AttendanceRecoveryActionType,
    AttendanceRecoveryPlanStatus,
    AttendanceRecoveryRiskLevel,
    AttendanceRectificationStatus,
    AttendanceStatus,
    AttendanceSubmissionStatus,
    FraudRiskLevel,
    FoodOrderStatus,
    IdentityVerificationStatus,
    RMSAttendanceCorrectionStatus,
    RMSCasePriority,
    RMSCaseStatus,
    UserRole,
)
from .validation import StrictSchemaModel

DEFAULT_REMEDIAL_ONLINE_LINK = "https://myclass.lpu.in/"
BaseModel = StrictSchemaModel


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


class IdentityRiskSignalOut(BaseModel):
    id: int
    signal_type: str
    severity: FraudRiskLevel
    score_delta: float
    is_blocking: bool
    reason: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class IdentityVerificationCaseOut(BaseModel):
    id: int
    workflow_key: str
    subject_role: str
    auth_user_id: Optional[int] = None
    student_id: Optional[int] = None
    faculty_id: Optional[int] = None
    applicant_email: Optional[str] = None
    external_subject_key: Optional[str] = None
    status: IdentityVerificationStatus
    risk_score: float
    risk_level: FraudRiskLevel
    requested_checks: list[str] = Field(default_factory=list)
    completed_checks: list[str] = Field(default_factory=list)
    latest_reason: Optional[str] = None
    graph_summary: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    signals: list[IdentityRiskSignalOut] = Field(default_factory=list)


class ApplicantRiskAssessmentRequest(BaseModel):
    applicant_email: str = Field(min_length=5, max_length=120)
    external_subject_key: Optional[str] = Field(default=None, max_length=160)
    claimed_role: str = Field(default="student", min_length=3, max_length=30)
    registration_number: Optional[str] = Field(default=None, min_length=3, max_length=40)
    parent_email: Optional[str] = Field(default=None, min_length=5, max_length=120)
    device_id: Optional[str] = Field(default=None, max_length=120)
    user_agent: Optional[str] = Field(default=None, max_length=300)
    ip_address: Optional[str] = Field(default=None, max_length=120)
    document_reference: Optional[str] = Field(default=None, max_length=160)
    document_match_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    face_match_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    liveness_passed: Optional[bool] = None
    suspicious_flags: list[str] = Field(default_factory=list, max_length=12)


class IdentityGraphNodeOut(BaseModel):
    id: str
    node_type: str
    label: str
    risk_level: FraudRiskLevel = FraudRiskLevel.LOW
    metadata: dict[str, Any] = Field(default_factory=dict)


class IdentityGraphEdgeOut(BaseModel):
    source: str
    target: str
    relation: str
    weight: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class IdentityGraphOut(BaseModel):
    subject_key: str
    summary: dict[str, Any] = Field(default_factory=dict)
    nodes: list[IdentityGraphNodeOut] = Field(default_factory=list)
    edges: list[IdentityGraphEdgeOut] = Field(default_factory=list)


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


class AttendanceAggregateRecomputeRequest(BaseModel):
    student_id: Optional[int] = None
    course_id: Optional[int] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    limit: int = Field(default=5000, ge=1, le=20000)


class AttendanceAggregateRecomputeResponse(BaseModel):
    recomputed: int
    scanned: int


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


class FoodDemoPaymentCompleteRequest(BaseModel):
    payment_reference: str = Field(min_length=5, max_length=120)


class FoodMetricsOut(BaseModel):
    active_orders: int
    completed_today: int
    cancelled_today: int
    rejection_today: int
    avg_preparing_minutes: float
    funnel: dict
    generated_at: datetime


class VendorSLAOut(BaseModel):
    monitored_orders: int
    on_time_orders: int
    on_time_percent: float
    avg_fulfillment_minutes: float
    breach_count: int


class VendorFulfillmentOut(BaseModel):
    total_orders: int
    status_breakdown: dict[str, int] = Field(default_factory=dict)
    avg_prep_minutes: float
    avg_delivery_minutes: float


class VendorBillingOut(BaseModel):
    gross_amount: float
    paid_amount: float
    pending_amount: float
    failed_amount: float
    reconciliation_gap_count: int


class VendorComplianceFlagOut(BaseModel):
    code: str
    severity: str
    message: str
    count: int = 0


class VendorDashboardOut(BaseModel):
    range_start: date
    range_end: date
    shops: int
    sla: VendorSLAOut
    fulfillment: VendorFulfillmentOut
    billing: VendorBillingOut
    compliance_flags: list[VendorComplianceFlagOut] = Field(default_factory=list)
    generated_at: datetime


class VendorReconciliationItemOut(BaseModel):
    order_id: int
    order_date: date
    shop_id: Optional[int] = None
    shop_name: Optional[str] = None
    total_price: float
    payment_reference: Optional[str] = None
    order_payment_status: str
    payment_record_status: Optional[str] = None
    issue_code: str
    issue_message: str
    last_status_updated_at: Optional[datetime] = None


class VendorReconciliationListOut(BaseModel):
    range_start: date
    range_end: date
    total_issues: int
    items: list[VendorReconciliationItemOut] = Field(default_factory=list)


class VendorReconciliationResolveRequest(BaseModel):
    order_ids: list[int] = Field(min_length=1, max_length=200)
    note: str = Field(min_length=5, max_length=300)


class VendorReconciliationResolveOut(BaseModel):
    resolved: int
    order_ids: list[int] = Field(default_factory=list)
    note: str
    resolved_at: datetime


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


class StudentDirectEmailRequest(BaseModel):
    student_id: Optional[int] = Field(default=None, ge=1)
    registration_number: Optional[str] = Field(default=None, min_length=3, max_length=40)
    email: Optional[str] = Field(default=None, min_length=5, max_length=160)
    subject: str = Field(min_length=3, max_length=140)
    message: str = Field(min_length=3, max_length=2000)

    @model_validator(mode="after")
    def normalize_direct_email_fields(self):
        if self.registration_number is not None:
            self.registration_number = re.sub(r"\s+", "", str(self.registration_number).strip().upper())
        if self.email is not None:
            self.email = str(self.email).strip().lower()
        self.subject = re.sub(r"\s+", " ", str(self.subject or "").strip())
        if not (self.student_id or self.registration_number or self.email):
            raise ValueError("Provide student_id, registration_number, or email.")
        if not self.subject:
            raise ValueError("Subject cannot be empty.")
        return self


class StudentDirectEmailOut(BaseModel):
    message: str
    student_id: int
    delivered_to: str
    subject: str
    channel: str
    notification_id: Optional[int] = None


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


class SupportQueryCategory(str, Enum):
    ATTENDANCE = "Attendance"
    ACADEMICS = "Academics"
    DISCREPANCY = "Discrepancy"
    OTHER = "Other"


class SupportQueryContactOut(BaseModel):
    id: int
    name: str
    section: Optional[str] = None
    descriptor: Optional[str] = None


class SupportQueryThreadOut(BaseModel):
    counterparty_id: int
    counterparty_name: str
    section: Optional[str] = None
    category: SupportQueryCategory
    subject: str
    last_message: str
    last_sender_role: str
    last_created_at: datetime
    unread_count: int = 0


class SupportQueryContextOut(BaseModel):
    role: str
    categories: list[SupportQueryCategory] = Field(default_factory=list)
    contacts: list[SupportQueryContactOut] = Field(default_factory=list)
    threads: list[SupportQueryThreadOut] = Field(default_factory=list)
    unread_total: int = 0


class SupportQuerySend(BaseModel):
    recipient_id: int = Field(ge=1)
    category: SupportQueryCategory = SupportQueryCategory.ATTENDANCE
    subject: Optional[str] = Field(default=None, max_length=140)
    message: str = Field(min_length=2, max_length=1000)


class SupportQueryMessageOut(BaseModel):
    id: int
    student_id: int
    faculty_id: int
    section: str
    category: SupportQueryCategory
    subject: str
    message: str
    sender_role: str
    created_at: datetime
    read_at: Optional[datetime] = None


class RMSQueryWorkflowAction(str, Enum):
    APPROVE = "approve"
    DISAPPROVE = "disapprove"
    SCHEDULE = "schedule"


class RMSQueryActionState(str, Enum):
    NONE = "none"
    APPROVED = "approved"
    DISAPPROVED = "disapproved"
    SCHEDULED = "scheduled"


class RMSQueryThreadOut(BaseModel):
    student_id: int
    student_name: str
    student_email: Optional[str] = None
    student_registration_number: Optional[str] = None
    faculty_id: int
    faculty_name: str
    section: str
    category: SupportQueryCategory
    subject: str
    last_message: str
    last_sender_role: str
    last_created_at: datetime
    unread_from_student: int = 0
    pending_action: bool = False
    action_state: RMSQueryActionState = RMSQueryActionState.NONE
    action_note: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    action_by_role: Optional[str] = None
    action_updated_at: Optional[datetime] = None


class RMSQueryCategoryBucketOut(BaseModel):
    category: SupportQueryCategory
    total_threads: int = 0
    pending_threads: int = 0
    threads: list[RMSQueryThreadOut] = Field(default_factory=list)


class RMSQueryDashboardOut(BaseModel):
    total_threads: int = 0
    total_pending: int = 0
    categories: list[RMSQueryCategoryBucketOut] = Field(default_factory=list)


class RMSStudentLookupOut(BaseModel):
    student_id: int
    name: str
    email: str
    registration_number: Optional[str] = None
    section: Optional[str] = None
    department: str
    semester: int
    parent_email: Optional[str] = None
    recent_query_count: int = 0
    pending_query_count: int = 0
    last_query_at: Optional[datetime] = None


class RMSStudentUpdateRequest(BaseModel):
    registration_number: Optional[str] = Field(default=None, min_length=3, max_length=40)
    section: Optional[str] = Field(default=None, min_length=1, max_length=80)


class RMSStudentUpdateOut(BaseModel):
    student: RMSStudentLookupOut
    changed_fields: list[str] = Field(default_factory=list)
    message: str


class RMSQueryActionRequest(BaseModel):
    student_id: int = Field(ge=1)
    faculty_id: int = Field(ge=1)
    category: SupportQueryCategory
    action: RMSQueryWorkflowAction
    note: Optional[str] = Field(default=None, max_length=400)
    scheduled_for: Optional[datetime] = None


class RMSQueryActionOut(BaseModel):
    thread: RMSQueryThreadOut
    message: str


class RMSAttendanceStatusUpdateRequest(BaseModel):
    registration_number: str = Field(min_length=3, max_length=40)
    course_code: Optional[str] = Field(default=None, min_length=2, max_length=20)
    schedule_id: Optional[int] = Field(default=None, ge=1)
    attendance_date: date
    status: AttendanceStatus
    note: Optional[str] = Field(default=None, max_length=400)

    @model_validator(mode="after")
    def ensure_course_or_schedule(self):
        if not self.course_code and not self.schedule_id:
            raise ValueError("course_code or schedule_id is required")
        return self


class RMSAttendanceSubjectSlotOut(BaseModel):
    schedule_id: int
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    classroom_label: Optional[str] = None
    current_status: Optional[AttendanceStatus] = None
    current_status_label: str = "Not marked"


class RMSAttendanceStudentSubjectOut(BaseModel):
    course_id: int
    course_code: str
    course_title: str
    faculty_id: int
    faculty_name: Optional[str] = None
    current_status: Optional[AttendanceStatus] = None
    current_status_label: str = "Not marked"
    slots: list[RMSAttendanceSubjectSlotOut] = Field(default_factory=list)


class RMSAttendanceStudentContextOut(BaseModel):
    student: RMSStudentLookupOut
    attendance_date: date
    subjects: list[RMSAttendanceStudentSubjectOut] = Field(default_factory=list)
    message: str


class RMSAttendanceStatusUpdateOut(BaseModel):
    record_id: int
    schedule_id: int
    class_start_time: time
    class_end_time: time
    classroom_label: Optional[str] = None
    student_id: int
    student_name: str
    registration_number: Optional[str] = None
    course_id: int
    course_code: str
    course_title: str
    faculty_id: int
    faculty_name: Optional[str] = None
    attendance_date: date
    previous_status: Optional[AttendanceStatus] = None
    updated_status: AttendanceStatus
    source: str
    note: Optional[str] = None
    updated_at: datetime
    message_sent: bool = False
    message: str


class RMSCaseAction(str, Enum):
    TRIAGE = "triage"
    ASSIGN = "assign"
    APPROVE = "approve"
    REJECT = "reject"
    CLOSE = "close"
    REOPEN = "reopen"
    ESCALATE = "escalate"


class RMSCaseAuditOut(BaseModel):
    id: int
    case_id: int
    action: str
    actor_user_id: Optional[int] = None
    actor_role: Optional[str] = None
    from_status: Optional[RMSCaseStatus] = None
    to_status: Optional[RMSCaseStatus] = None
    note: Optional[str] = None
    evidence_ref: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RMSCaseOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    student_registration_number: Optional[str] = None
    faculty_id: Optional[int] = None
    faculty_name: Optional[str] = None
    section: str
    category: SupportQueryCategory
    subject: str
    status: RMSCaseStatus
    priority: RMSCasePriority
    assigned_to_user_id: Optional[int] = None
    first_response_due_at: Optional[datetime] = None
    resolution_due_at: Optional[datetime] = None
    first_responded_at: Optional[datetime] = None
    is_escalated: bool = False
    escalated_at: Optional[datetime] = None
    escalation_reason: Optional[str] = None
    reopened_count: int = 0
    last_message_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    sla_seconds_to_first_response: Optional[int] = None
    sla_seconds_to_resolution: Optional[int] = None
    updated_at: datetime
    created_at: datetime


class RMSCaseListOut(BaseModel):
    total: int = 0
    pending_queue: int = 0
    escalated: int = 0
    cases: list[RMSCaseOut] = Field(default_factory=list)


class RMSCaseTransitionRequest(BaseModel):
    action: RMSCaseAction
    note: Optional[str] = Field(default=None, max_length=600)
    evidence_ref: Optional[str] = Field(default=None, max_length=4000)
    assign_to_user_id: Optional[int] = Field(default=None, ge=1)


class RMSCaseBulkTransitionRequest(BaseModel):
    case_ids: list[int] = Field(min_length=1, max_length=500)
    action: RMSCaseAction
    note: Optional[str] = Field(default=None, max_length=600)
    assign_to_user_id: Optional[int] = Field(default=None, ge=1)


class RMSCaseBulkTransitionOut(BaseModel):
    requested: int
    updated: int
    skipped: int
    updated_case_ids: list[int] = Field(default_factory=list)


class RMSCaseTimelineOut(BaseModel):
    case: RMSCaseOut
    timeline: list[RMSCaseAuditOut] = Field(default_factory=list)


class RMSCaseReopenRequest(BaseModel):
    note: str = Field(min_length=8, max_length=600)
    evidence_ref: Optional[str] = Field(default=None, max_length=4000)


class RMSAttendanceCorrectionCreateRequest(BaseModel):
    registration_number: str = Field(min_length=3, max_length=40)
    course_code: str = Field(min_length=2, max_length=20)
    attendance_date: date
    requested_status: AttendanceStatus
    reason: str = Field(min_length=10, max_length=600)
    evidence_ref: str = Field(min_length=10, max_length=4000)


class RMSAttendanceCorrectionReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


class RMSAttendanceCorrectionReviewRequest(BaseModel):
    action: RMSAttendanceCorrectionReviewAction
    review_note: Optional[str] = Field(default=None, max_length=600)


class RMSAttendanceCorrectionOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    registration_number: Optional[str] = None
    course_id: int
    course_code: str
    course_title: str
    faculty_id: int
    faculty_name: Optional[str] = None
    attendance_date: date
    previous_status: Optional[AttendanceStatus] = None
    requested_status: AttendanceStatus
    reason: str
    evidence_ref: str
    requested_by_user_id: int
    requested_by_role: str
    status: RMSAttendanceCorrectionStatus
    is_high_impact: bool
    review_note: Optional[str] = None
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    applied_record_id: Optional[int] = None
    applied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class RMSAttendanceCorrectionListOut(BaseModel):
    total: int = 0
    pending: int = 0
    requests: list[RMSAttendanceCorrectionOut] = Field(default_factory=list)


class GovernancePolicyUpsertRequest(BaseModel):
    value: dict[str, Any] = Field(default_factory=dict)


class GovernancePolicyOut(BaseModel):
    key: str
    value: dict[str, Any] = Field(default_factory=dict)
    updated_by_user_id: Optional[int] = None
    updated_at: datetime


class GovernanceRoleDelegationRequest(BaseModel):
    target_user_id: int = Field(ge=1)
    target_role: UserRole
    reason: Optional[str] = Field(default=None, max_length=400)


class GovernanceRoleDelegationOut(BaseModel):
    target_user_id: int
    from_role: Optional[UserRole] = None
    to_role: UserRole
    delegated_by_user_id: int
    reason: Optional[str] = None
    created_at: datetime


class GovernanceBreakGlassRequest(BaseModel):
    reason: str = Field(min_length=8, max_length=500)
    scope: str = Field(default="global", min_length=3, max_length=200)
    expires_in_minutes: Optional[int] = Field(default=60, ge=5, le=720)
    ticket_ref: Optional[str] = Field(default=None, max_length=80)


class GovernanceBreakGlassLogOut(BaseModel):
    id: int
    actor_user_id: int
    actor_email: str
    reason: str
    scope: str
    ticket_ref: Optional[str] = None
    expires_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime


class GovernanceBreakGlassListOut(BaseModel):
    total: int = 0
    logs: list[GovernanceBreakGlassLogOut] = Field(default_factory=list)


class AdminStudentSearchOut(BaseModel):
    student_id: int
    name: str
    email: str
    registration_number: Optional[str] = None
    section: Optional[str] = None
    department: str
    semester: int
    parent_email: Optional[str] = None


class AdminFacultySearchOut(BaseModel):
    faculty_id: int
    name: str
    email: str
    faculty_identifier: Optional[str] = None
    section: Optional[str] = None
    department: str


class AdminCourseSearchOut(BaseModel):
    course_id: int
    course_code: str
    course_title: str
    faculty_id: int
    faculty_name: Optional[str] = None


class AdminGlobalSearchOut(BaseModel):
    query: str
    students: list[AdminStudentSearchOut] = Field(default_factory=list)
    faculty: list[AdminFacultySearchOut] = Field(default_factory=list)
    courses: list[AdminCourseSearchOut] = Field(default_factory=list)
    total_matches: int = 0


class AdminStudentGradeUpsertRequest(BaseModel):
    registration_number: str = Field(min_length=3, max_length=40)
    course_code: str = Field(min_length=2, max_length=20)
    grade_letter: str = Field(min_length=1, max_length=8)
    marks_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    remark: Optional[str] = Field(default=None, max_length=400)


class AdminStudentGradeOut(BaseModel):
    grade_id: int
    student_id: int
    student_name: str
    registration_number: Optional[str] = None
    course_id: int
    course_code: str
    course_title: str
    faculty_id: Optional[int] = None
    faculty_name: Optional[str] = None
    grade_letter: str
    grade_points: Optional[float] = None
    marks_percent: Optional[float] = None
    remark: Optional[str] = None
    graded_by_user_id: Optional[int] = None
    graded_at: datetime
    updated_at: datetime


class AdminStudentGradeListOut(BaseModel):
    student: AdminStudentSearchOut
    grades: list[AdminStudentGradeOut] = Field(default_factory=list)


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
    profile_photo_data_url: Optional[str] = None
    registration_number: Optional[str] = Field(default=None, min_length=3, max_length=40)
    faculty_identifier: Optional[str] = Field(default=None, min_length=3, max_length=40)
    section: Optional[str] = Field(default=None, min_length=1, max_length=80)
    semester: Optional[int] = Field(default=None, ge=1, le=12)
    parent_email: Optional[str] = None
    invite_token: Optional[str] = Field(default=None, min_length=12, max_length=240)
    provisioning_token: Optional[str] = Field(default=None, min_length=12, max_length=240)

    @model_validator(mode="after")
    def normalize_signup_fields(self):
        self.email = str(self.email or "").strip().lower()
        self.name = re.sub(r"\s+", " ", str(self.name or "").strip()).upper()
        self.department = re.sub(r"\s+", " ", str(self.department or "").strip()).upper()
        if self.registration_number is not None:
            self.registration_number = re.sub(r"\s+", "", str(self.registration_number).strip().upper())
        if self.faculty_identifier is not None:
            self.faculty_identifier = re.sub(r"\s+", "", str(self.faculty_identifier).strip().upper())
        if self.section is not None:
            self.section = re.sub(r"\s+", "", str(self.section).strip().upper())
        if self.parent_email is not None:
            self.parent_email = str(self.parent_email).strip().lower() or None
        if self.invite_token is not None:
            self.invite_token = str(self.invite_token).strip() or None
        if self.provisioning_token is not None:
            self.provisioning_token = str(self.provisioning_token).strip() or None
        return self


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
    mfa_enabled: bool = False
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
    cooldown_seconds: int = 30
    validity_minutes: int = 10


class AlternateEmailUpdateRequest(BaseModel):
    alternate_email: Optional[str] = None


class VerifyOTPRequest(BaseModel):
    email: str
    otp_code: str = Field(min_length=4, max_length=10)
    mfa_code: Optional[str] = Field(default=None, min_length=6, max_length=20)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    refresh_token: Optional[str] = None
    refresh_expires_at: Optional[datetime] = None
    user: AuthUserOut


class PrivilegedRoleInviteCreateRequest(BaseModel):
    email: str
    role: UserRole
    expires_in_hours: int = Field(default=48, ge=1, le=168)


class PrivilegedRoleInviteOut(BaseModel):
    email: str
    role: UserRole
    invite_token: str
    expires_at: datetime


class MFAStatusResponse(BaseModel):
    required: bool
    enabled: bool
    enrolled_at: Optional[datetime] = None
    backup_codes_remaining: int = 0
    setup_pending: bool = False
    setup_expires_at: Optional[datetime] = None


class MFAEnrollResponse(BaseModel):
    message: str
    secret: str
    otpauth_uri: str
    qr_svg_data_uri: Optional[str] = None
    backup_codes: list[str]
    setup_expires_at: datetime


class MFAActivateRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=10)


class MFABackupCodeRotateResponse(BaseModel):
    message: str
    backup_codes: list[str]


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


class TimetableOverrideScope(str, Enum):
    STUDENT = "student"
    SECTION = "section"


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


class TimetableOverrideUpsertRequest(BaseModel):
    scope_type: TimetableOverrideScope
    student_id: Optional[int] = Field(default=None, ge=1)
    section: Optional[str] = Field(default=None, min_length=1, max_length=80)
    source_weekday: int = Field(ge=0, le=6)
    source_start_time: time
    course_id: int = Field(ge=1)
    faculty_id: int = Field(ge=1)
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    classroom_label: Optional[str] = Field(default=None, max_length=120)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_scope_and_time(self):
        if self.scope_type == TimetableOverrideScope.STUDENT and not self.student_id:
            raise ValueError("student_id is required for student timetable overrides")
        if self.scope_type == TimetableOverrideScope.SECTION and not self.section:
            raise ValueError("section is required for section timetable overrides")
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        return self


class TimetableOverrideOut(BaseModel):
    id: int
    scope_type: TimetableOverrideScope
    student_id: Optional[int] = None
    section: Optional[str] = None
    source_weekday: int
    source_start_time: time
    schedule_id: int
    course_id: int
    faculty_id: int
    weekday: int
    start_time: time
    end_time: time
    classroom_label: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


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
    schedule_id: Optional[int] = Field(default=None, ge=1)
    demo_mode: bool = False
    selfie_photo_data_url: Optional[str] = Field(default=None, min_length=20)
    selfie_frames_data_urls: Optional[list[str]] = Field(default=None, min_length=1, max_length=12)
    ai_match: Optional[bool] = None
    ai_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    ai_reason: Optional[str] = None
    ai_model: Optional[str] = "gemini-3-flash-preview"

    @model_validator(mode="after")
    def validate_selfie_payload(self):
        if not self.demo_mode and not self.schedule_id:
            raise ValueError("schedule_id is required unless demo_mode is true")
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
    demo_mode: bool = False
    persistence_skipped: bool = False
    verification_engine: str = "ai"
    verification_confidence: float = 0.0
    verification_reason: Optional[str] = None


class StudentAttendanceHistoryItemOut(BaseModel):
    schedule_id: Optional[int] = None
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


class SaarthiMessageOut(BaseModel):
    id: int
    sender_role: str
    message: str
    created_at: datetime


class SaarthiStatusOut(BaseModel):
    course_code: str
    course_title: str
    faculty_name: str
    week_start_date: date
    mandatory_date: date
    session_completed_for_week: bool
    attendance_credit_minutes_for_week: int
    attendance_awarded_on: Optional[datetime] = None
    current_week_message_count: int = 0
    last_attendance_status: Optional[AttendanceStatus] = None
    last_attendance_date: Optional[date] = None
    status_message: str
    messages: list[SaarthiMessageOut] = Field(default_factory=list)


class SaarthiChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class SaarthiChatResponse(BaseModel):
    reply: str
    attendance_awarded_now: bool = False
    session: SaarthiStatusOut


class AttendanceRecoverySuggestedClassOut(BaseModel):
    makeup_class_id: int
    class_date: date
    start_time: time
    end_time: time
    topic: str
    class_mode: str
    room_number: Optional[str] = None
    online_link: Optional[str] = None


class AttendanceRecoveryActionOut(BaseModel):
    id: int
    action_type: AttendanceRecoveryActionType
    status: AttendanceRecoveryActionStatus
    title: str
    description: str
    recipient_role: str
    recipient_user_id: Optional[int] = None
    recipient_email: Optional[str] = None
    target_makeup_class_id: Optional[int] = None
    scheduled_for: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    outcome_note: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AttendanceRecoveryPlanOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    registration_number: Optional[str] = None
    section: Optional[str] = None
    course_id: int
    course_code: str
    course_title: str
    faculty_id: Optional[int] = None
    faculty_name: Optional[str] = None
    risk_level: AttendanceRecoveryRiskLevel
    status: AttendanceRecoveryPlanStatus
    attendance_percent: float
    present_count: int
    absent_count: int
    delivered_count: int
    consecutive_absences: int
    missed_remedials: int
    parent_alert_allowed: bool = False
    recovery_due_at: Optional[datetime] = None
    summary: str
    last_absent_on: Optional[date] = None
    last_evaluated_at: datetime
    recommended_makeup_class: Optional[AttendanceRecoverySuggestedClassOut] = None
    actions: list[AttendanceRecoveryActionOut] = Field(default_factory=list)


class AttendanceRecoveryPlanListOut(BaseModel):
    plans: list[AttendanceRecoveryPlanOut] = Field(default_factory=list)
    last_updated_at: datetime


class AttendanceRecoveryActionUpdateRequest(BaseModel):
    note: Optional[str] = Field(default=None, min_length=2, max_length=600)


class AttendanceRecoveryActionUpdateOut(BaseModel):
    action_id: int
    status: AttendanceRecoveryActionStatus
    completed_at: Optional[datetime] = None
    outcome_note: Optional[str] = None


class AttendanceRecoveryRecomputeRequest(BaseModel):
    student_id: Optional[int] = Field(default=None, ge=1)
    course_id: Optional[int] = Field(default=None, ge=1)
    limit: int = Field(default=200, ge=1, le=5000)


class AttendanceRecoveryRecomputeOut(BaseModel):
    evaluated: int
    plans_touched: int


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


class AttendanceRectificationRequestCreate(BaseModel):
    course_id: int
    class_date: date
    start_time: Optional[time] = None
    proof_note: str = Field(min_length=10, max_length=1200)
    proof_photo_data_url: Optional[str] = Field(default=None, min_length=20)


class StudentAttendanceRectificationOut(BaseModel):
    id: int
    course_id: int
    course_code: str
    course_title: str
    faculty_name: str
    schedule_id: int
    class_date: date
    class_start_time: time
    class_end_time: time
    proof_note: str
    proof_photo_data_url: Optional[str] = None
    status: AttendanceRectificationStatus
    requested_at: datetime
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None


class StudentAttendanceRectificationListOut(BaseModel):
    requests: list[StudentAttendanceRectificationOut]


class FacultyAttendanceRectificationOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    course_id: int
    course_code: str
    course_title: str
    class_date: date
    class_start_time: time
    class_end_time: time
    proof_note: str
    proof_photo_data_url: Optional[str] = None
    status: AttendanceRectificationStatus
    requested_at: datetime
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None


class FacultyAttendanceRectificationListOut(BaseModel):
    schedule_id: int
    class_date: date
    requests: list[FacultyAttendanceRectificationOut]


class FacultyRectificationReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


class FacultyRectificationReviewRequest(BaseModel):
    request_id: int
    action: FacultyRectificationReviewAction
    note: Optional[str] = Field(default=None, max_length=600)


class FacultyRectificationReviewResponse(BaseModel):
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


class CopilotIntent(str, Enum):
    ATTENDANCE_BLOCKER = "attendance_blocker"
    ELIGIBILITY_RISK = "eligibility_risk"
    CREATE_REMEDIAL_PLAN = "create_remedial_plan"
    STUDENT_FLAG_REASON = "student_flag_reason"
    MODULE_ASSIST = "module_assist"
    UNSUPPORTED = "unsupported"


class CopilotOutcome(str, Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    DENIED = "denied"
    FAILED = "failed"


class CopilotQueryRequest(BaseModel):
    query_text: str = Field(min_length=4, max_length=1000)
    schedule_id: Optional[int] = Field(default=None, ge=1)
    student_id: Optional[int] = Field(default=None, ge=1)
    registration_number: Optional[str] = Field(default=None, min_length=3, max_length=40)
    course_id: Optional[int] = Field(default=None, ge=1)
    course_code: Optional[str] = Field(default=None, min_length=2, max_length=20)
    section: Optional[str] = Field(default=None, min_length=1, max_length=80)
    class_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    class_mode: Optional[str] = Field(default=None, pattern="^(online|offline)$")
    room_number: Optional[str] = Field(default=None, min_length=1, max_length=80)
    active_module: Optional[str] = Field(
        default=None,
        pattern="^(attendance|food|saarthi|remedial|rms|administrative)$",
    )
    client_context: dict[str, Any] = Field(default_factory=dict)
    send_message: bool = True

    @model_validator(mode="after")
    def normalize_copilot_fields(self):
        self.query_text = re.sub(r"\s+", " ", str(self.query_text or "").strip())
        if self.registration_number is not None:
            self.registration_number = re.sub(r"\s+", "", str(self.registration_number).strip().upper())
        if self.course_code is not None:
            self.course_code = re.sub(r"\s+", "", str(self.course_code).strip().upper())
        if self.section is not None:
            self.section = re.sub(r"\s+", "", str(self.section).strip().upper())
        if self.class_mode is not None:
            self.class_mode = str(self.class_mode).strip().lower()
        if self.room_number is not None:
            self.room_number = re.sub(r"\s+", " ", str(self.room_number).strip())
        if self.active_module is not None:
            normalized_module = re.sub(r"\s+", "", str(self.active_module).strip().lower())
            self.active_module = normalized_module or None
        if not isinstance(self.client_context, dict):
            self.client_context = {}
        return self


class CopilotEvidenceItem(BaseModel):
    label: str
    value: str
    status: str = Field(default="info", pattern="^(pass|fail|warning|info)$")


class CopilotActionItem(BaseModel):
    action: str
    status: str = Field(default="preview", pattern="^(completed|preview|blocked|denied|failed)$")
    detail: Optional[str] = None


class CopilotQueryResponse(BaseModel):
    intent: CopilotIntent
    outcome: CopilotOutcome
    title: str
    explanation: list[str] = Field(default_factory=list)
    evidence: list[CopilotEvidenceItem] = Field(default_factory=list)
    actions: list[CopilotActionItem] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    entities: dict[str, Any] = Field(default_factory=dict)
    audit_id: Optional[int] = None


class CopilotAuditLogOut(BaseModel):
    id: int
    actor_user_id: int
    actor_role: str
    actor_email: Optional[str] = None
    query_text: str
    intent: CopilotIntent
    outcome: CopilotOutcome
    scope: Optional[str] = None
    target_student_id: Optional[int] = None
    target_course_id: Optional[int] = None
    target_section: Optional[str] = None
    explanation: list[str] = Field(default_factory=list)
    evidence: list[CopilotEvidenceItem] = Field(default_factory=list)
    actions: list[CopilotActionItem] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
