const DAY_LABELS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const AI_MODEL = 'gemini-3-flash-preview';
const PUTER_SDK_URL = 'https://js.puter.com/v2/';
const RAZORPAY_SDK_URL = 'https://checkout.razorpay.com/v1/checkout.js';
const RAZORPAY_SDK_ORIGIN = 'https://checkout.razorpay.com';
const RAZORPAY_SDK_LOAD_TIMEOUT_MS = 12000;
const ENABLE_DECORATIVE_MOTION = false;
const USE_CLIENT_AI_FACE_ASSIST = false;
const ATTENDANCE_VERIFY_REQUEST_TIMEOUT_MS = 12000;
const LIVE_VERIFICATION_MAX_ATTEMPTS = 8;
const LIVE_VERIFICATION_BURST_FRAMES = 8;
const LIVE_VERIFICATION_BURST_INTERVAL_MS = 140;
const PASSWORD_POLICY_TEXT = 'Minimum 8 characters with letters, numbers, and a special character.';
const FOOD_LOCATION_MAX_STALE_MS = 120000;
const FOOD_DELIVERY_FEE_INR = 30;
const FOOD_PLATFORM_FEE_INR = 5;
const FOOD_DEMO_STORAGE_KEY = 'foodhall_demo_enabled';
const CLIENT_DEMO_FEATURES_ENABLED = (() => {
  try {
    const host = String(window.location.hostname || '').toLowerCase();
    return host === 'localhost'
      || host === '127.0.0.1'
      || host === '::1'
      || host.endsWith('.test')
      || host.endsWith('.loc');
  } catch (_) {
    return false;
  }
})();
const FOOD_SERVICE_START_MINUTES = 10 * 60;
const FOOD_SERVICE_END_MINUTES = 21 * 60;
const FOOD_SERVICE_HOURS_LABEL = '10:00 AM - 9:00 PM';
const FOOD_DEMAND_LIVE_REFRESH_MS = 3000;
const STUDENT_LIVE_REFRESH_MS = 60000;
const REMEDIAL_LIVE_REFRESH_MS = 30000;
const SUPPORT_DESK_LIVE_REFRESH_MS = 30000;
const REALTIME_TOPICS = 'attendance,messages,rms,food,remedial,admin,identity,identity_shield';
const ROUTE_SPLIT_ASSET_VERSION = '20260308b';
const REMEDIAL_REJECT_WINDOW_MS = 30 * 60 * 1000;
const REMEDIAL_DEFAULT_ONLINE_LINK = 'https://myclass.lpu.in/';
const STUDENT_TIMETABLE_START_DATE = '2026-03-02';
const SESSION_IDLE_LOGOUT_MS = 15 * 60 * 1000;
const SESSION_MAX_LOGOUT_MS = 30 * 60 * 1000;
const LIVE_DATE_FORMATTER = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  year: 'numeric',
  month: 'short',
  day: '2-digit',
});
const LIVE_TIME_FORMATTER = new Intl.DateTimeFormat(undefined, {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: true,
});
const LIVE_TIMEZONE_SHORT_FORMATTER = new Intl.DateTimeFormat(undefined, {
  timeZoneName: 'short',
});
const LIVE_TIMEZONE_LONG_FORMATTER = new Intl.DateTimeFormat(undefined, {
  timeZoneName: 'long',
});
const LIVE_DATE_TOOLTIP_FORMATTER = new Intl.DateTimeFormat(undefined, {
  weekday: 'long',
  year: 'numeric',
  month: 'long',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: true,
});
const LIVE_OPERATIONAL_REFRESH_MS = 10 * 1000;
const FOOD_ORDER_STATUS_LABELS = {
  placed: 'Order being verified by',
  verified: 'Order verified',
  preparing: 'Cooking your meals',
  out_for_delivery: 'Out for delivery',
  delivered: 'Delivered',
  rejected: 'Rejected by shop',
  refund_pending: 'Refund in progress',
  refunded: 'Refund completed',
  ready: 'Ready for pickup',
  collected: 'Picked up',
  cancelled: 'Order cancelled',
};
const FOOD_CART_TIMELINE_STATUSES = new Set(['placed', 'preparing', 'ready', 'out_for_delivery']);
const FOOD_WARN_ORDER_STATUSES = new Set(['cancelled', 'rejected', 'refund_pending', 'refunded']);
const FOOD_GOOD_ORDER_STATUSES = new Set(['delivered', 'collected']);
const FOOD_PAYMENT_FAILURE_STATES = new Set(['failed', 'failure', 'cancelled', 'refunded']);
const FOOD_FAILED_TONE_STATUSES = new Set(['cancelled', 'rejected', 'refund_pending', 'refunded']);
const FOOD_VERIFIED_TONE_STATUSES = new Set(['verified']);
const FOOD_DELIVERED_TONE_STATUSES = new Set(['delivered']);
const FOOD_MANUAL_DELIVERY_CONFIRM_STATUSES = new Set(['verified']);
const FOOD_FINAL_ORDER_STATUSES = new Set(['delivered', 'cancelled', 'rejected', 'refunded', 'collected']);
const FOOD_ORDER_PROGRESS_POINTS = {
  placed: 12,
  verified: 30,
  preparing: 52,
  ready: 68,
  out_for_delivery: 84,
  collected: 100,
  delivered: 100,
  cancelled: 100,
  rejected: 100,
  refund_pending: 100,
  refunded: 100,
};
const FOOD_DEMAND_PIE_COLORS = [
  '#2FA8FF',
  '#4CC9A0',
  '#F5B14F',
  '#6E8BFF',
  '#FF8E6A',
  '#37C3D6',
  '#D18BFF',
  '#7BB66D',
  '#E79D5C',
  '#4E93CF',
  '#B0A54A',
  '#5AB7F2',
];
const MODULE_LABELS = {
  attendance: 'Attendance',
  saarthi: 'Saarthi',
  food: 'Food Hall',
  administrative: 'Administrative',
  rms: 'RMS',
  remedial: 'Remedial',
};
let FOOD_POPULAR_SPOT_IDS = ['oven-express', 'kitchen-ette-block41', 'nk-food-court-bh2-6'];
let FOOD_SHOP_GROUPS = [
  { key: 'popular', title: 'Popular Spots', subtitle: 'Most loved by students right now' },
  { key: 'unimall17', title: 'UniMall - Block 17', subtitle: 'Branded chains' },
  { key: 'bh1', title: 'BH-1 Food Kiosk Area', subtitle: 'Quick meals and snacks' },
  { key: 'bh2to6', title: 'BH-2 to BH-6 Kiosk Cluster', subtitle: 'High variety cluster' },
  { key: 'block41', title: 'Block-41 Food Court Zone', subtitle: 'Tea + snack hub' },
  { key: 'block34', title: 'Block-34 Kiosk Area', subtitle: 'Hidden popular picks' },
];
let FOOD_SLOT_FALLBACK = [];
let FOOD_AI_QUICK_CRAVINGS = [
  'Spicy snacks under INR 150',
  'Healthy juice and light meal',
  'Coffee + dessert combo',
  'North Indian full meal',
  'Fast pizza pickup',
];
let FOOD_DELIVERY_POINTS = [];
let FOOD_SHOP_DIRECTORY = [];
let FOOD_COVER_FALLBACK_URL = '/web/assets/food-covers/fallback.svg';

let puterSdkPromise = null;
let razorpaySdkPromise = null;
let verlynHelpModulePromise = null;
let foodCatalogModulePromise = null;
let foodCatalogReady = false;
let liveDateTimeTimer = null;
let liveDateTimeLabelCache = '';
let liveDateUtilityLastRunMs = 0;
let studentRealtimeTimer = null;
let studentTimetableStatusTimer = null;
let moduleRealtimeTimer = null;
let moduleRealtimeBusy = false;
let otpCooldownTimer = null;
let forgotOtpCooldownTimer = null;
let foodPopupTimer = null;
let foodToastTimer = null;
let foodOrdersPulseTimer = null;
let foodDemandLiveTimer = null;
let foodDemandLiveBusy = false;
let remedialLiveTimer = null;
let remedialLiveBusy = false;
let supportDeskLiveTimer = null;
let supportDeskLiveBusy = false;
let realtimeBusController = null;
let realtimeBusLoadingPromise = null;
let routeModuleRuntime = null;
const routeModuleInstances = new Map();
const routeModuleActiveKeys = new Set();
let routeModuleSyncToken = 0;
let sessionIdleTimer = null;
let sessionMaxTimer = null;
let sessionActivityBound = false;
let lastSessionActivityPingMs = 0;
const runtimeUiStore = {
  profilePromptSeenByUser: new Set(),
  mfaGuideSeenByUser: new Set(),
  themeByUser: new Map(),
};

const state = {
  absentees: [],
  demand: [],
  capacity: [],
  attendanceSummary: [],
  peakTimes: [],
  overview: { blocks: 0, classrooms: 0, courses: 0, faculty: 0, students: 0 },
  studentMessages: [],
  coursesById: {},
  food: {
    items: [],
    slots: [],
    slotHintsById: {},
    slotHintsDate: '',
    orders: [],
    orderHistory: [],
    ordersTab: 'current',
    paymentRecovery: [],
    expandedOrderGroups: new Set(),
    liveFeedByOrderId: new Map(),
    liveFeedInitialized: false,
    freshnessDigest: '',
    lastOrdersSyncAtMs: 0,
    lastOrdersChangeAtMs: 0,
    syncPulseUntilMs: 0,
    ratingBusyOrderIds: new Set(),
    deliveryConfirmBusyOrderIds: new Set(),
    recoveryBusyRefs: new Set(),
    demandDigest: '',
    lastDemandSyncAtMs: 0,
    demandSyncPulseUntilMs: 0,
    demandSelectedSlotId: 0,
    demandLive: {
      windowMinutes: 2,
      activeOrders: 0,
      ordersLastWindow: 0,
      statusUpdatesLastWindow: 0,
      paymentEventsLastWindow: 0,
      hottestSlotLabel: '',
      hottestSlotOrders: 0,
      pulsesBySlotId: {},
      pulses: [],
      syncedAtMs: 0,
      digest: '',
      pulseUntilMs: 0,
    },
    orderDate: '',
    shops: [],
    menuByShop: {},
    selectedShopId: '',
    demoEnabled: false,
    cart: {
        shopId: '',
        items: [],
    },
    cartUpdatedAt: '',
    cartModalTab: 'cart',
    checkoutPreviewOpen: false,
    checkoutDeliveryPoint: '',
    realtimeAvailabilitySignature: '',
    realtimeServiceOpen: null,
    location: {
        requestedOnce: false,
        autoPromptAttempted: false,
        checking: false,
        allowed: false,
        verified: false,
        monitoring: false,
        watchId: null,
        monitorBusy: false,
        latitude: null,
        longitude: null,
        accuracyM: null,
        lastVerifiedAtMs: 0,
        message: '',
    },
  },
  resources: {
    workload: [],
    mongoStatus: null,
  },
  admin: {
    telemetryHistory: [],
    summary: null,
    alerts: [],
    insights: null,
    identityCases: [],
    recoveryPlans: [],
    recoveryIncludeResolved: false,
    recoveryLastUpdatedAt: null,
    lastUpdatedAt: null,
    staleAfterSeconds: 60,
    copilotAuditLoadedAtMs: 0,
    copilotAuditBusy: false,
    copilotAuditQueued: false,
  },
  remedial: {
    eligibleCourses: [],
    classes: [],
    selectedClassId: null,
    selectedClassAttendance: [],
    selectedClassAttendanceSections: [],
    selectedClassAttendanceAllStudents: [],
    selectedAttendanceModalSection: '',
    selectedAttendanceModalCourseKey: '',
    messages: [],
    attendanceLedger: [],
    attendanceLedgerByCourse: {},
    validatedClass: null,
    markedClassId: null,
    markedOnlineLink: '',
    demoBypassLeadTime: false,
  },
  supportDesk: {
    categories: ['Attendance', 'Academics', 'Discrepancy', 'Other'],
    contacts: [],
    threads: [],
    messages: [],
    selectedCounterpartyId: null,
    selectedCategory: 'Attendance',
    selectedCounterpartyName: '',
    selectedCounterpartySection: '',
    unreadTotal: 0,
  },
  rms: {
    dashboard: null,
    selectedCategory: 'all',
    selectedStatus: 'all',
    selectedStudent: null,
    selectedThread: null,
    threadAction: 'approve',
    attendanceContext: null,
    attendanceSelectedCourseCode: '',
    attendanceSelectedScheduleId: null,
    attendanceUpdate: null,
  },
  student: {
    weekStart: '',
    minTimetableDate: STUDENT_TIMETABLE_START_DATE,
    viewDate: '',
    timetable: [],
    kpiTimetable: [],
    timetableCache: {},
    timetableNetworkRequests: new Map(),
    timetablePrefetching: new Set(),
    timetableRequestToken: 0,
    timetableRepairInFlight: false,
    kpiRefreshInFlight: false,
    selectedScheduleId: null,
    name: '',
    registrationNumber: '',
    section: '',
    sectionUpdatedAt: null,
    profilePhotoDataUrl: '',
    profilePhotoLockedUntil: null,
    profilePhotoCanUpdateNow: true,
    profilePhotoLockDaysRemaining: 0,
    sectionCanUpdateNow: true,
    sectionLockedUntil: null,
    sectionLockMinutesRemaining: 0,
    sectionChangeRequiresFacultyApproval: false,
    profileLoaded: false,
    enrollmentLoaded: false,
    hasEnrollmentVideo: false,
    enrollmentCanUpdateNow: true,
    enrollmentLockedUntil: null,
    enrollmentLockDaysRemaining: 0,
    enrollmentUpdatedAt: null,
    enrollmentRequired: false,
    enrollmentFrames: [],
    enrollmentCaptureRunning: false,
    enrollmentStream: null,
    pendingProfilePhotoDataUrl: '',
    profileSetupRequired: false,
    autoRefreshBusy: false,
    demoAttendanceEnabled: false,
    selfieDataUrl: '',
    attendanceAggregate: null,
    recoveryPlans: [],
    attendanceHistory: [],
    attendanceHistoryByCourse: {},
    saarthiStatus: null,
    saarthiMessages: [],
    saarthiSending: false,
    saarthiResetting: false,
    saarthiUiMessage: 'Saarthi session will appear here.',
    saarthiUiState: 'neutral',
    attendanceDetailsCourseKey: '',
    attendanceRectificationRequests: [],
    attendanceRectificationByKey: {},
    attendanceRectificationTarget: null,
    attendanceRectificationProofDataUrl: '',
    kpiScheduleId: null,
  },
  faculty: {
    schedules: [],
    selectedScheduleId: null,
    classDate: '',
    dashboard: null,
    recoveryPlans: [],
    selectedSubmissionIds: new Set(),
    rectificationRequests: [],
    analysisHistory: [],
    classroomPhotoDataUrl: '',
  },
  facultyProfile: {
    name: '',
    facultyIdentifier: '',
    section: '',
    sectionUpdatedAt: null,
    profilePhotoDataUrl: '',
    profilePhotoLockedUntil: null,
    profilePhotoCanUpdateNow: true,
    profilePhotoLockDaysRemaining: 0,
    sectionCanUpdateNow: true,
    sectionLockedUntil: null,
    sectionLockMinutesRemaining: 0,
    profileLoaded: false,
    pendingProfilePhotoDataUrl: '',
    profileSetupRequired: false,
  },
  camera: {
    stream: null,
    captureHandler: null,
    burstFrames: 1,
    liveVerificationActive: false,
    liveSessionToken: 0,
  },
  ui: {
    theme: 'light',
    activeModule: 'attendance',
    adminSubmodules: {
      attendance: 'attendance-ops',
      rms: 'rms-overview',
    },
    chotuOpen: false,
    supportDeskOpen: false,
    verlynOpen: false,
  },
};

const authState = {
  token: '',
  user: null,
  pendingEmail: '',
  mode: 'login',
  otpCooldownUntilMs: 0,
  otpRequestInFlight: false,
  otpVerifyInFlight: false,
  registerInFlight: false,
  signupAdminPhotoDataUrl: '',
  forgotOtpCooldownUntilMs: 0,
  forgotOtpRequestInFlight: false,
  forgotResetToken: '',
  forgotResetTokenExpiresAt: '',
  mfaSetupRequired: false,
  mfaEnrollInFlight: false,
  mfaActivateInFlight: false,
  mfaSetup: null,
  sessionStartedAtMs: 0,
  lastActivityAtMs: 0,
};

const els = {
  workDate: document.getElementById('work-date'),
  courseId: document.getElementById('course-id'),
  absenteesWrap: document.getElementById('absentees-wrap'),
  demandChart: document.getElementById('demand-chart'),
  adminTelemetryChart: document.getElementById('admin-telemetry-chart'),
  adminTelemetryAttendanceNow: document.getElementById('admin-telemetry-attendance-now'),
  adminTelemetryAttendanceDelta: document.getElementById('admin-telemetry-attendance-delta'),
  adminTelemetryCapacityNow: document.getElementById('admin-telemetry-capacity-now'),
  adminTelemetryCapacityDelta: document.getElementById('admin-telemetry-capacity-delta'),
  adminTelemetryDemandNow: document.getElementById('admin-telemetry-demand-now'),
  adminTelemetryDemandDelta: document.getElementById('admin-telemetry-demand-delta'),
  adminTelemetryStabilityNow: document.getElementById('admin-telemetry-stability-now'),
  adminTelemetryStabilityNote: document.getElementById('admin-telemetry-stability-note'),
  capacityChart: document.getElementById('capacity-chart'),
  workloadChart: document.getElementById('workload-chart'),
  mongoSyncStatus: document.getElementById('mongo-sync-status'),
  aiOutput: document.getElementById('ai-output'),
  statusLog: document.getElementById('status-log'),
  metricBlocks: document.getElementById('metric-blocks'),
  metricClassrooms: document.getElementById('metric-classrooms'),
  metricCourses: document.getElementById('metric-courses'),
  metricFaculty: document.getElementById('metric-faculty'),
  metricStudents: document.getElementById('metric-students'),
  liveDateTime: document.getElementById('live-datetime'),
  attendanceDonut: document.getElementById('attendance-donut'),
  attendanceRate: document.getElementById('attendance-rate'),
  adminHealthAttendanceValue: document.getElementById('admin-health-attendance-value'),
  adminHealthAttendanceFill: document.getElementById('admin-health-attendance-fill'),
  adminHealthCapacityValue: document.getElementById('admin-health-capacity-value'),
  adminHealthCapacityFill: document.getElementById('admin-health-capacity-fill'),
  adminHealthDemandValue: document.getElementById('admin-health-demand-value'),
  adminHealthDemandFill: document.getElementById('admin-health-demand-fill'),
  adminHealthWorkloadValue: document.getElementById('admin-health-workload-value'),
  adminHealthWorkloadFill: document.getElementById('admin-health-workload-fill'),
  presentCount: document.getElementById('present-count'),
  absentCount: document.getElementById('absent-count'),
  enrolledCount: document.getElementById('enrolled-count'),
  attendancePresentPercent: document.getElementById('attendance-present-percent'),
  attendancePresentFill: document.getElementById('attendance-present-fill'),
  attendanceAbsentPercent: document.getElementById('attendance-absent-percent'),
  attendanceAbsentFill: document.getElementById('attendance-absent-fill'),
  attendanceHealthScore: document.getElementById('attendance-health-score'),
  attendanceHealthFill: document.getElementById('attendance-health-fill'),
  attendanceHealthNote: document.getElementById('attendance-health-note'),

  authOverlay: document.getElementById('auth-overlay'),
  authModeLoginBtn: document.getElementById('auth-mode-login-btn'),
  authModeSignupBtn: document.getElementById('auth-mode-signup-btn'),
  authRoleWrap: document.getElementById('auth-role-wrap'),
  authRoleSelect: document.getElementById('auth-role-select'),
  authLoginSection: document.getElementById('auth-login-section'),
  authEmail: document.getElementById('auth-email'),
  authPassword: document.getElementById('auth-password'),
  authSignupEmail: document.getElementById('auth-signup-email'),
  authSignupPassword: document.getElementById('auth-signup-password'),
  authSignupPasswordStrength: document.getElementById('auth-signup-password-strength'),
  authLoginControls: document.getElementById('auth-login-controls'),
  authSignupFields: document.getElementById('auth-signup-fields'),
  authSignupActions: document.getElementById('auth-signup-actions'),
  authOtpWrap: document.getElementById('auth-otp-wrap'),
  authMfaWrap: document.getElementById('auth-mfa-wrap'),
  authMfaCode: document.getElementById('auth-mfa-code'),
  authMfaHelp: document.getElementById('auth-mfa-help'),
  authName: document.getElementById('auth-name'),
  authDepartment: document.getElementById('auth-department'),
  authSignupRegistrationWrap: document.getElementById('auth-signup-registration-wrap'),
  authSignupRegistration: document.getElementById('auth-signup-registration'),
  authSignupFacultyIdWrap: document.getElementById('auth-signup-faculty-id-wrap'),
  authSignupFacultyId: document.getElementById('auth-signup-faculty-id'),
  authSignupAdminPhotoWrap: document.getElementById('auth-signup-admin-photo-wrap'),
  authSignupAdminPhoto: document.getElementById('auth-signup-admin-photo'),
  authSignupAdminPhotoPreview: document.getElementById('auth-signup-admin-photo-preview'),
  authSectionWrap: document.getElementById('auth-section-wrap'),
  authSignupSection: document.getElementById('auth-signup-section'),
  authSemesterWrap: document.getElementById('auth-semester-wrap'),
  authSemester: document.getElementById('auth-semester'),
  authParentEmailWrap: document.getElementById('auth-parent-email-wrap'),
  authParentEmail: document.getElementById('auth-parent-email'),
  authOtp: document.getElementById('auth-otp'),
  authMessage: document.getElementById('auth-message'),
  authPasswordStrength: document.getElementById('auth-password-strength'),
  requestOtpBtn: document.getElementById('request-otp-btn'),
  verifyOtpBtn: document.getElementById('verify-otp-btn'),
  registerBtn: document.getElementById('register-btn'),
  forgotPasswordToggleBtn: document.getElementById('forgot-password-toggle-btn'),
  forgotPasswordPanel: document.getElementById('forgot-password-panel'),
  forgotEmail: document.getElementById('forgot-email'),
  forgotRegistrationNumber: document.getElementById('forgot-registration-number'),
  forgotRequestOtpBtn: document.getElementById('forgot-request-otp-btn'),
  forgotVerifyOtpBtn: document.getElementById('forgot-verify-otp-btn'),
  forgotOtp: document.getElementById('forgot-otp'),
  forgotNewPassword: document.getElementById('forgot-new-password'),
  forgotPasswordStrength: document.getElementById('forgot-password-strength'),
  forgotConfirmPassword: document.getElementById('forgot-confirm-password'),
  forgotResetBtn: document.getElementById('forgot-reset-btn'),
  forgotCancelBtn: document.getElementById('forgot-cancel-btn'),
  forgotModalCloseBtn: document.getElementById('forgot-modal-close-btn'),
  forgotMessage: document.getElementById('forgot-message'),
  mfaSetupModal: document.getElementById('mfa-setup-modal'),
  mfaEnrollBtn: document.getElementById('mfa-enroll-btn'),
  mfaSecret: document.getElementById('mfa-secret'),
  mfaCopySecretBtn: document.getElementById('mfa-copy-secret-btn'),
  mfaOtpauthUri: document.getElementById('mfa-otpauth-uri'),
  mfaCopyUriBtn: document.getElementById('mfa-copy-uri-btn'),
  mfaQrImage: document.getElementById('mfa-qr-image'),
  mfaQrEmpty: document.getElementById('mfa-qr-empty'),
  mfaQrConfirm: document.getElementById('mfa-qr-confirm'),
  mfaSetupExpires: document.getElementById('mfa-setup-expires'),
  mfaBackupCodes: document.getElementById('mfa-backup-codes'),
  mfaTotpCode: document.getElementById('mfa-totp-code'),
  mfaActivateBtn: document.getElementById('mfa-activate-btn'),
  mfaLogoutBtn: document.getElementById('mfa-logout-btn'),
  mfaHelpOpenBtn: document.getElementById('mfa-help-open-btn'),
  mfaHelpModal: document.getElementById('mfa-help-modal'),
  mfaHelpCloseBtn: document.getElementById('mfa-help-close-btn'),
  mfaHelpGotItBtn: document.getElementById('mfa-help-got-it-btn'),
  mfaSetupStatus: document.getElementById('mfa-setup-status'),
  otpPopup: document.getElementById('otp-popup'),
  otpPopupLoader: document.getElementById('otp-popup-loader'),
  otpPopupTitle: document.getElementById('otp-popup-title'),
  otpPopupText: document.getElementById('otp-popup-text'),
  otpPopupCloseBtn: document.getElementById('otp-popup-close-btn'),
  foodToast: document.getElementById('food-toast'),
  foodToastCard: document.getElementById('food-toast-card'),
  foodToastTitle: document.getElementById('food-toast-title'),
  foodToastText: document.getElementById('food-toast-text'),
  foodToastCloseBtn: document.getElementById('food-toast-close-btn'),
  accountMenuBtn: document.getElementById('account-menu-btn'),
  accountMenuDropdown: document.getElementById('account-menu-dropdown'),
  accountMenuAvatar: document.getElementById('account-menu-avatar'),
  accountMenuInitial: document.getElementById('account-menu-initial'),
  accountDropdownPhoto: document.getElementById('account-dropdown-photo'),
  accountDropdownEmail: document.getElementById('account-dropdown-email'),
  accountDropdownReg: document.getElementById('account-dropdown-reg'),
  viewProfileBtn: document.getElementById('view-profile-btn'),
  accountMfaSetupBtn: document.getElementById('account-mfa-setup-btn'),
  logoutBtn: document.getElementById('logout-btn'),
  navDashboardBtn: document.getElementById('nav-dashboard-btn'),
  navCoursesBtn: document.getElementById('nav-courses-btn'),
  navAttendanceBtn: document.getElementById('nav-attendance-btn'),
  topNavAttendanceBtn: document.getElementById('top-nav-attendance'),
  topNavSaarthiBtn: document.getElementById('top-nav-saarthi'),
  topNavFoodBtn: document.getElementById('top-nav-food'),
  topNavAdministrativeBtn: document.getElementById('top-nav-administrative'),
  topNavRmsBtn: document.getElementById('top-nav-rms'),
  topNavRemedialBtn: document.getElementById('top-nav-remedial'),
  modulePanels: document.querySelectorAll('.module-panel[data-module]'),
  accountSection: document.getElementById('account-section'),
  profilePrimaryEmail: document.getElementById('profile-primary-email'),
  profileFullName: document.getElementById('profile-full-name'),
  profileIdLabel: document.getElementById('profile-id-label'),
  profileAlternateEmail: document.getElementById('profile-alternate-email'),
  saveAlternateEmailBtn: document.getElementById('save-alternate-email-btn'),
  accountLogoutBtn: document.getElementById('account-logout-btn'),
  alternateEmailStatus: document.getElementById('alternate-email-status'),

  executiveSection: document.getElementById('executive-section'),
  rmsSection: document.getElementById('rms-section'),
  studentSection: document.getElementById('student-section'),
  saarthiSection: document.getElementById('saarthi-section'),
  facultySection: document.getElementById('faculty-section'),
  adminAttendanceActionsCard: document.getElementById('admin-attendance-actions-card'),
  adminRecoveryIncludeResolved: document.getElementById('admin-recovery-include-resolved'),
  adminRecoveryRefreshBtn: document.getElementById('admin-recovery-refresh-btn'),
  adminRecoveryRecomputeAllBtn: document.getElementById('admin-recovery-recompute-all-btn'),
  adminRecoveryStatus: document.getElementById('admin-recovery-status'),
  adminRecoverySummary: document.getElementById('admin-recovery-summary'),
  adminRecoveryList: document.getElementById('admin-recovery-list'),
  adminLiveChip: document.getElementById('admin-live-chip'),
  adminDataFreshnessNote: document.getElementById('admin-data-freshness-note'),
  adminIssuesWrap: document.getElementById('admin-issues-wrap'),
  adminProfileWrap: document.getElementById('admin-profile-wrap'),
  adminBenchmarkWrap: document.getElementById('admin-benchmark-wrap'),
  absenteeCard: document.getElementById('absentee-card'),
  capacityCard: document.getElementById('capacity-card'),
  aiAbsentBtn: document.getElementById('ai-absent-btn'),
  aiRushBtn: document.getElementById('ai-rush-btn'),
  aiRemedialBtn: document.getElementById('ai-remedial-btn'),
  foodSection: document.getElementById('food-section'),
  foodOrderDate: document.getElementById('food-order-date'),
  foodItemSelect: document.getElementById('food-item-select'),
  foodSlotSelect: document.getElementById('food-slot-select'),
  foodOpenCartBtn: document.getElementById('food-open-cart-btn'),
  foodDemoToggleBtn: document.getElementById('food-demo-toggle-btn'),
  foodDemoStatus: document.getElementById('food-demo-status'),
  foodEnableLocationBtn: document.getElementById('food-enable-location-btn'),
  foodLocationStatus: document.getElementById('food-location-status'),
  foodStatusMsg: document.getElementById('food-status-msg'),
  foodDemandChartModule: document.getElementById('food-demand-chart-module'),
  foodDemandFreshness: document.getElementById('food-demand-freshness'),
  foodDemandLiveCompact: document.getElementById('food-demand-live-compact'),
  foodDemandLiveCompactSummary: document.getElementById('food-demand-live-compact-summary'),
  foodDemandLiveHotBtn: document.getElementById('food-demand-live-hot-btn'),
  foodDemandSlotDetail: document.getElementById('food-demand-slot-detail'),
  foodPeakList: document.getElementById('food-peak-list'),
  foodOrdersPanel: document.getElementById('food-orders-panel'),
  foodOrdersPanelFreshness: document.getElementById('food-orders-panel-freshness'),
  foodOrdersList: document.getElementById('food-orders-list'),
  foodOrdersListFreshness: document.getElementById('food-orders-list-freshness'),
  foodOrdersTabCurrent: document.getElementById('food-orders-tab-current'),
  foodOrdersTabPrevious: document.getElementById('food-orders-tab-previous'),
  foodPaymentRecoveryList: document.getElementById('food-payment-recovery-list'),
  foodPaymentRecoveryFreshness: document.getElementById('food-payment-recovery-freshness'),
  foodShopGrid: document.getElementById('food-shop-grid'),
  foodCartSummary: document.getElementById('food-cart-summary'),
  foodCartList: document.getElementById('food-cart-list'),
  foodCheckoutPreview: document.getElementById('food-checkout-preview'),
  foodReviewSummaryStrip: document.getElementById('food-review-summary-strip'),
  foodCheckoutItems: document.getElementById('food-checkout-items'),
  foodCheckoutFeeBreakdown: document.getElementById('food-checkout-fee-breakdown'),
  foodCheckoutSummary: document.getElementById('food-checkout-summary'),
  foodDeliveryBlockSelect: document.getElementById('food-delivery-block-select'),
  foodOrderStatusTimeline: document.getElementById('food-order-status-timeline'),
  foodAiCravingInput: document.getElementById('food-ai-craving-input'),
  foodAiSuggestBtn: document.getElementById('food-ai-suggest-btn'),
  foodAiQuickChips: document.getElementById('food-ai-quick-chips'),
  foodAiOutput: document.getElementById('food-ai-output'),
  chotuWidget: document.getElementById('chotu-widget'),
  chotuHint: document.getElementById('chotu-hint'),
  chotuToggleBtn: document.getElementById('chotu-toggle-btn'),
  chotuPanel: document.getElementById('chotu-panel'),
  chotuMinimizeBtn: document.getElementById('chotu-minimize-btn'),
  supportDeskWidget: document.getElementById('support-desk-widget'),
  supportDeskToggleBtn: document.getElementById('support-desk-toggle-btn'),
  supportDeskUnreadBadge: document.getElementById('support-desk-unread-badge'),
  supportDeskPanel: document.getElementById('support-desk-panel'),
  supportDeskMinimizeBtn: document.getElementById('support-desk-minimize-btn'),
  supportDeskStatus: document.getElementById('support-desk-status'),
  supportDeskRecipientLabel: document.getElementById('support-desk-recipient-label'),
  supportDeskRecipientSelect: document.getElementById('support-desk-recipient-select'),
  supportDeskCategorySelect: document.getElementById('support-desk-category-select'),
  supportDeskThreadMeta: document.getElementById('support-desk-thread-meta'),
  supportDeskMessages: document.getElementById('support-desk-messages'),
  supportDeskComposeInput: document.getElementById('support-desk-compose-input'),
  supportDeskSendBtn: document.getElementById('support-desk-send-btn'),
  verlynSidebarWidget: document.getElementById('verlyn-sidebar-widget'),
  verlynToggleBtn: document.getElementById('verlyn-toggle-btn'),
  verlynPanel: document.getElementById('verlyn-panel'),
  verlynMinimizeBtn: document.getElementById('verlyn-minimize-btn'),
  verlynStatus: document.getElementById('verlyn-status'),
  verlynScopeChip: document.getElementById('verlyn-scope-chip'),
  verlynRoleChip: document.getElementById('verlyn-role-chip'),
  verlynToggleMeta: document.getElementById('verlyn-toggle-meta'),
  verlynQuickActions: document.getElementById('verlyn-quick-actions'),
  verlynOutput: document.getElementById('verlyn-output'),
  verlynInput: document.getElementById('verlyn-input'),
  verlynAskBtn: document.getElementById('verlyn-ask-btn'),
  foodAdminPanel: document.getElementById('food-admin-panel'),
  foodAdminPanelTitle: document.getElementById('food-admin-panel-title'),
  foodAdminPanelSubtitle: document.getElementById('food-admin-panel-subtitle'),
  foodGlobalItemControls: document.getElementById('food-global-item-controls'),
  foodGlobalSlotControls: document.getElementById('food-global-slot-controls'),
  foodOrderStatusControls: document.getElementById('food-order-status-controls'),
  foodNewItemName: document.getElementById('food-new-item-name'),
  foodNewItemPrice: document.getElementById('food-new-item-price'),
  foodCreateItemBtn: document.getElementById('food-create-item-btn'),
  foodNewSlotLabel: document.getElementById('food-new-slot-label'),
  foodNewSlotStart: document.getElementById('food-new-slot-start'),
  foodNewSlotEnd: document.getElementById('food-new-slot-end'),
  foodNewSlotCapacity: document.getElementById('food-new-slot-capacity'),
  foodCreateSlotBtn: document.getElementById('food-create-slot-btn'),
  foodAdminOrderSelect: document.getElementById('food-admin-order-select'),
  foodAdminStatusSelect: document.getElementById('food-admin-status-select'),
  foodAdminUpdateStatusBtn: document.getElementById('food-admin-update-status-btn'),
  foodAdminStatusMsg: document.getElementById('food-admin-status-msg'),
  foodShopModal: document.getElementById('food-shop-modal'),
  foodShopModalTitle: document.getElementById('food-shop-modal-title'),
  foodShopModalSubtitle: document.getElementById('food-shop-modal-subtitle'),
  foodShopMenuList: document.getElementById('food-shop-menu-list'),
  foodShopModalCloseBtn: document.getElementById('food-shop-modal-close-btn'),
  foodCartModal: document.getElementById('food-cart-modal'),
  foodCartTabCartBtn: document.getElementById('food-cart-tab-cart-btn'),
  foodCartTabReviewBtn: document.getElementById('food-cart-tab-review-btn'),
  foodCartTabCartPane: document.getElementById('food-cart-tab-cart'),
  foodCartTabReviewPane: document.getElementById('food-cart-tab-review'),
  foodCartStepCart: document.getElementById('food-cart-step-cart'),
  foodCartStepReview: document.getElementById('food-cart-step-review'),
  foodCartStepPay: document.getElementById('food-cart-step-pay'),
  foodCartModalCloseBtn: document.getElementById('food-cart-modal-close-btn'),
  foodCartCheckoutBtn: document.getElementById('food-cart-checkout-btn'),
  foodCartPayBtn: document.getElementById('food-cart-pay-btn'),
  foodCartBackBtn: document.getElementById('food-cart-back-btn'),
  foodCartClearBtn: document.getElementById('food-cart-clear-btn'),

  remedialSection: document.getElementById('remedial-section'),
  remedialFacultyPanel: document.getElementById('remedial-faculty-panel'),
  remedialStudentPanel: document.getElementById('remedial-student-panel'),
  remedialCourseSelect: document.getElementById('remedial-course-select'),
  remedialCourseCodeInput: document.getElementById('remedial-course-code-input'),
  remedialCourseTitleInput: document.getElementById('remedial-course-title-input'),
  remedialSectionsInput: document.getElementById('remedial-sections-input'),
  remedialDate: document.getElementById('remedial-date'),
  remedialStartTime: document.getElementById('remedial-start-time'),
  remedialEndTime: document.getElementById('remedial-end-time'),
  remedialModeSelect: document.getElementById('remedial-mode-select'),
  remedialRoomWrap: document.getElementById('remedial-room-wrap'),
  remedialRoomInput: document.getElementById('remedial-room-input'),
  remedialOnlineWrap: document.getElementById('remedial-online-wrap'),
  remedialOnlineLinkInput: document.getElementById('remedial-online-link-input'),
  remedialDemoInstantBtn: document.getElementById('remedial-demo-instant-btn'),
  remedialTopic: document.getElementById('remedial-topic'),
  remedialCustomMessageInput: document.getElementById('remedial-custom-message-input'),
  remedialCreateBtn: document.getElementById('remedial-create-btn'),
  remedialFacultyStatus: document.getElementById('remedial-faculty-status'),
  remedialClassesList: document.getElementById('remedial-classes-list'),
  remedialPreviousClassesList: document.getElementById('remedial-previous-classes-list'),
  remedialClassSelect: document.getElementById('remedial-class-select'),
  remedialRefreshAttendanceBtn: document.getElementById('remedial-refresh-attendance-btn'),
  remedialAttendanceList: document.getElementById('remedial-attendance-list'),
  remedialRefreshMessagesBtn: document.getElementById('remedial-refresh-messages-btn'),
  remedialMessagesList: document.getElementById('remedial-messages-list'),
  facultyMessageSections: document.getElementById('faculty-message-sections'),
  facultyMessageType: document.getElementById('faculty-message-type'),
  facultyMessageText: document.getElementById('faculty-message-text'),
  facultyMessageSendBtn: document.getElementById('faculty-message-send-btn'),
  facultyMessageStatus: document.getElementById('faculty-message-status'),
  directEmailStudentId: document.getElementById('direct-email-student-id'),
  directEmailRegistration: document.getElementById('direct-email-registration'),
  directEmailStudentEmail: document.getElementById('direct-email-student-email'),
  directEmailSubject: document.getElementById('direct-email-subject'),
  directEmailMessage: document.getElementById('direct-email-message'),
  directEmailSendBtn: document.getElementById('direct-email-send-btn'),
  directEmailStatus: document.getElementById('direct-email-status'),
  remedialCodeInput: document.getElementById('remedial-code-input'),
  remedialValidateBtn: document.getElementById('remedial-validate-btn'),
  remedialCodeDetails: document.getElementById('remedial-code-details'),
  remedialStudentAggregatePercent: document.getElementById('remedial-student-aggregate-percent'),
  remedialStudentAttendedDelivered: document.getElementById('remedial-student-attended-delivered'),
  remedialStudentLedgerList: document.getElementById('remedial-student-ledger-list'),
  remedialMarkBtn: document.getElementById('remedial-mark-btn'),
  remedialStudentStatus: document.getElementById('remedial-student-status'),
  remedialAttendanceModal: document.getElementById('remedial-attendance-modal'),
  remedialAttendanceModalTitle: document.getElementById('remedial-attendance-modal-title'),
  remedialAttendanceModalMeta: document.getElementById('remedial-attendance-modal-meta'),
  remedialAttendanceModalList: document.getElementById('remedial-attendance-modal-list'),
  remedialAttendanceModalCloseBtn: document.getElementById('remedial-attendance-modal-close-btn'),

  weekStartDate: document.getElementById('week-start-date'),
  prevWeekBtn: document.getElementById('prev-week-btn'),
  goCurrentWeekBtn: document.getElementById('go-current-week-btn'),
  nextWeekBtn: document.getElementById('next-week-btn'),
  loadTimetableBtn: document.getElementById('load-timetable-btn'),
  timetableViewInfo: document.getElementById('timetable-view-info'),
  timetableGrid: document.getElementById('timetable-grid'),
  themeToggleBtn: document.getElementById('theme-toggle-btn'),
  selectedClassLabel: document.getElementById('selected-class-label'),
  studentAttendanceDemoBtn: document.getElementById('student-attendance-demo-btn'),
  attendanceKpiSubtitle: document.getElementById('attendance-kpi-subtitle'),
  takeSelfieBtn: document.getElementById('take-selfie-btn'),
  studentAttendanceResult: document.getElementById('student-attendance-result'),
  profilePhotoInput: document.getElementById('profile-photo-input'),
  saveProfilePhotoBtn: document.getElementById('save-profile-photo-btn'),
  profilePhotoPreview: document.getElementById('profile-photo-preview'),
  profileStatus: document.getElementById('profile-status'),
  profileModal: document.getElementById('profile-modal'),
  profileModalTitle: document.getElementById('profile-modal-title'),
  profileModalSubtitle: document.getElementById('profile-modal-subtitle'),
  profileTabDetailsBtn: document.getElementById('profile-tab-details-btn'),
  profileTabEnrollmentBtn: document.getElementById('profile-tab-enrollment-btn'),
  profileTabDetails: document.getElementById('profile-tab-details'),
  profileTabEnrollment: document.getElementById('profile-tab-enrollment'),
  profileCloseBtn: document.getElementById('profile-close-btn'),
  profileRegistrationNumber: document.getElementById('profile-registration-number'),
  profileRegistrationNote: document.getElementById('profile-registration-note'),
  profileSectionWrap: document.getElementById('profile-section-wrap'),
  profileSectionInput: document.getElementById('profile-section-input'),
  profileSectionNote: document.getElementById('profile-section-note'),
  profilePhotoWrap: document.getElementById('profile-photo-wrap'),
  enrollmentPhotoPreview: document.getElementById('enrollment-photo-preview'),
  openProfilePhotoUpdateBtn: document.getElementById('open-profile-photo-update-btn'),
  enrollmentSummaryStatus: document.getElementById('enrollment-summary-status'),
  enrollmentSummaryUpdated: document.getElementById('enrollment-summary-updated'),
  enrollmentSummaryLock: document.getElementById('enrollment-summary-lock'),
  openEnrollmentModalBtn: document.getElementById('open-enrollment-modal-btn'),
  enrollmentModal: document.getElementById('enrollment-modal'),
  enrollmentModalTitle: document.getElementById('enrollment-modal-title'),
  enrollmentModalSubtitle: document.getElementById('enrollment-modal-subtitle'),
  enrollmentVideo: document.getElementById('enrollment-video'),
  enrollmentVideoDemo: document.getElementById('enrollment-video-demo'),
  enrollmentCanvas: document.getElementById('enrollment-canvas'),
  enrollmentInstruction: document.getElementById('enrollment-instruction'),
  enrollmentProgress: document.getElementById('enrollment-progress'),
  enrollmentStatus: document.getElementById('enrollment-status'),
  enrollmentStartBtn: document.getElementById('enrollment-start-btn'),
  enrollmentSaveBtn: document.getElementById('enrollment-save-btn'),
  enrollmentCloseBtn: document.getElementById('enrollment-close-btn'),
  enrollmentLogoutBtn: document.getElementById('enrollment-logout-btn'),
  selfiePreview: document.getElementById('selfie-preview'),
  studentMessagesList: document.getElementById('student-messages-list'),
  studentMessagesOpenRemedialBtn: document.getElementById('student-messages-open-remedial-btn'),
  studentSaarthiCard: document.getElementById('student-saarthi-card'),
  saarthiStatus: document.getElementById('saarthi-status'),
  saarthiMandatoryDate: document.getElementById('saarthi-mandatory-date'),
  saarthiWeeklyCredit: document.getElementById('saarthi-weekly-credit'),
  saarthiHistory: document.getElementById('saarthi-history'),
  saarthiComposeInput: document.getElementById('saarthi-compose-input'),
  saarthiNewChatBtn: document.getElementById('saarthi-new-chat-btn'),
  saarthiSendBtn: document.getElementById('saarthi-send-btn'),
  studentAggregatePercent: document.getElementById('student-aggregate-percent'),
  studentAttendedDelivered: document.getElementById('student-attended-delivered'),
  studentRecoveryPlans: document.getElementById('student-recovery-plans'),
  studentAggregateCourses: document.getElementById('student-aggregate-courses'),
  attendanceDetailsModal: document.getElementById('attendance-details-modal'),
  attendanceDetailsTitle: document.getElementById('attendance-details-title'),
  attendanceDetailsMeta: document.getElementById('attendance-details-meta'),
  dashboardTitle: document.getElementById('dashboard-title'),
  dashboardSubtitle: document.getElementById('dashboard-subtitle'),
  attendanceDetailsList: document.getElementById('attendance-details-list'),
  attendanceDetailsCloseBtn: document.getElementById('attendance-details-close-btn'),
  attendanceRectificationModal: document.getElementById('attendance-rectification-modal'),
  attendanceRectificationTitle: document.getElementById('attendance-rectification-title'),
  attendanceRectificationMeta: document.getElementById('attendance-rectification-meta'),
  attendanceRectificationContext: document.getElementById('attendance-rectification-context'),
  attendanceRectificationProofNote: document.getElementById('attendance-rectification-proof-note'),
  attendanceRectificationProofPhotoInput: document.getElementById('attendance-rectification-proof-photo'),
  attendanceRectificationProofPreview: document.getElementById('attendance-rectification-proof-preview'),
  attendanceRectificationStatus: document.getElementById('attendance-rectification-status'),
  attendanceRectificationSubmitBtn: document.getElementById('attendance-rectification-submit-btn'),
  attendanceRectificationCancelBtn: document.getElementById('attendance-rectification-cancel-btn'),

  facultyScheduleSelect: document.getElementById('faculty-schedule-select'),
  facultyClassDate: document.getElementById('faculty-class-date'),
  facultyRefreshBtn: document.getElementById('faculty-refresh-btn'),
  facultyTotal: document.getElementById('faculty-total'),
  facultyPresent: document.getElementById('faculty-present'),
  facultyPending: document.getElementById('faculty-pending'),
  facultyAbsent: document.getElementById('faculty-absent'),
  reviewSelectAll: document.getElementById('review-select-all'),
  facultyReviewNote: document.getElementById('faculty-review-note'),
  facultyApproveBtn: document.getElementById('faculty-approve-btn'),
  facultyRejectBtn: document.getElementById('faculty-reject-btn'),
  facultySubmissionsBody: document.getElementById('faculty-submissions-body'),
  facultyRecoveryList: document.getElementById('faculty-recovery-list'),
  facultyRectificationBody: document.getElementById('faculty-rectification-body'),
  adminCreateScheduleCourseId: document.getElementById('admin-create-schedule-course-id'),
  adminCreateScheduleFacultyId: document.getElementById('admin-create-schedule-faculty-id'),
  adminCreateScheduleWeekday: document.getElementById('admin-create-schedule-weekday'),
  adminCreateScheduleStartTime: document.getElementById('admin-create-schedule-start-time'),
  adminCreateScheduleEndTime: document.getElementById('admin-create-schedule-end-time'),
  adminCreateScheduleRoomLabel: document.getElementById('admin-create-schedule-room-label'),
  adminCreateScheduleBtn: document.getElementById('admin-create-schedule-btn'),
  adminCreateScheduleStatus: document.getElementById('admin-create-schedule-status'),
  adminTimetableOverrideScope: document.getElementById('admin-timetable-override-scope'),
  adminTimetableOverrideStudentId: document.getElementById('admin-timetable-override-student-id'),
  adminTimetableOverrideSection: document.getElementById('admin-timetable-override-section'),
  adminTimetableOverrideSourceWeekday: document.getElementById('admin-timetable-override-source-weekday'),
  adminTimetableOverrideSourceStartTime: document.getElementById('admin-timetable-override-source-start-time'),
  adminTimetableOverrideCourseId: document.getElementById('admin-timetable-override-course-id'),
  adminTimetableOverrideFacultyId: document.getElementById('admin-timetable-override-faculty-id'),
  adminTimetableOverrideWeekday: document.getElementById('admin-timetable-override-weekday'),
  adminTimetableOverrideStartTime: document.getElementById('admin-timetable-override-start-time'),
  adminTimetableOverrideEndTime: document.getElementById('admin-timetable-override-end-time'),
  adminTimetableOverrideRoomLabel: document.getElementById('admin-timetable-override-room-label'),
  adminTimetableOverrideBtn: document.getElementById('admin-timetable-override-btn'),
  adminTimetableOverrideStatus: document.getElementById('admin-timetable-override-status'),
  adminUpdateStudentId: document.getElementById('admin-update-student-id'),
  adminUpdateStudentSection: document.getElementById('admin-update-student-section'),
  adminUpdateStudentSectionBtn: document.getElementById('admin-update-student-section-btn'),
  adminUpdateStudentSectionStatus: document.getElementById('admin-update-student-section-status'),
  adminSearchStudentRegistration: document.getElementById('admin-search-student-registration'),
  adminSearchStudentBtn: document.getElementById('admin-search-student-btn'),
  adminSearchFacultyIdentifier: document.getElementById('admin-search-faculty-identifier'),
  adminSearchFacultyBtn: document.getElementById('admin-search-faculty-btn'),
  adminGlobalSearchQuery: document.getElementById('admin-global-search-query'),
  adminGlobalSearchBtn: document.getElementById('admin-global-search-btn'),
  adminSearchStatus: document.getElementById('admin-search-status'),
  adminSearchResults: document.getElementById('admin-search-results'),
  adminGradeStudentRegistration: document.getElementById('admin-grade-student-registration'),
  adminGradeCourseCode: document.getElementById('admin-grade-course-code'),
  adminGradeLetter: document.getElementById('admin-grade-letter'),
  adminGradeMarks: document.getElementById('admin-grade-marks'),
  adminGradeRemark: document.getElementById('admin-grade-remark'),
  adminGradeSubmitBtn: document.getElementById('admin-grade-submit-btn'),
  adminGradeStatus: document.getElementById('admin-grade-status'),
  adminGradeHistoryWrap: document.getElementById('admin-grade-history-wrap'),
  adminIdentityStudentId: document.getElementById('admin-identity-student-id'),
  adminIdentityScreenBtn: document.getElementById('admin-identity-screen-btn'),
  adminIdentityRefreshBtn: document.getElementById('admin-identity-refresh-btn'),
  adminIdentityStatus: document.getElementById('admin-identity-status'),
  adminIdentityCasesWrap: document.getElementById('admin-identity-cases-wrap'),
  adminCopilotAuditSearch: document.getElementById('admin-copilot-audit-search'),
  adminCopilotAuditIntent: document.getElementById('admin-copilot-audit-intent'),
  adminCopilotAuditOutcome: document.getElementById('admin-copilot-audit-outcome'),
  adminCopilotAuditRole: document.getElementById('admin-copilot-audit-role'),
  adminCopilotAuditActorUserId: document.getElementById('admin-copilot-audit-actor-user-id'),
  adminCopilotAuditLimit: document.getElementById('admin-copilot-audit-limit'),
  adminCopilotAuditSearchBtn: document.getElementById('admin-copilot-audit-search-btn'),
  adminCopilotAuditClearBtn: document.getElementById('admin-copilot-audit-clear-btn'),
  adminCopilotAuditStatus: document.getElementById('admin-copilot-audit-status'),
  adminCopilotAuditWrap: document.getElementById('admin-copilot-audit-wrap'),
  adminAttendanceSubmoduleSelect: document.getElementById('admin-attendance-submodule-select'),
  adminRmsSubmoduleSelect: document.getElementById('admin-rms-submodule-select'),
  rmsQueryCategory: document.getElementById('rms-query-category'),
  rmsQueryStatus: document.getElementById('rms-query-status'),
  rmsRefreshBtn: document.getElementById('rms-refresh-btn'),
  rmsStatusMsg: document.getElementById('rms-status-msg'),
  rmsTotalThreads: document.getElementById('rms-total-threads'),
  rmsTotalPending: document.getElementById('rms-total-pending'),
  rmsActiveCategories: document.getElementById('rms-active-categories'),
  rmsQueryList: document.getElementById('rms-query-list'),
  rmsSelectedThread: document.getElementById('rms-selected-thread'),
  rmsThreadAction: document.getElementById('rms-thread-action'),
  rmsThreadScheduleWrap: document.getElementById('rms-thread-schedule-wrap'),
  rmsThreadScheduledFor: document.getElementById('rms-thread-scheduled-for'),
  rmsThreadNote: document.getElementById('rms-thread-note'),
  rmsApplyThreadActionBtn: document.getElementById('rms-apply-thread-action-btn'),
  rmsThreadActionMsg: document.getElementById('rms-thread-action-msg'),
  rmsSearchRegistration: document.getElementById('rms-search-registration'),
  rmsStudentSearchBtn: document.getElementById('rms-student-search-btn'),
  rmsStudentSummary: document.getElementById('rms-student-summary'),
  rmsUpdateRegistration: document.getElementById('rms-update-registration'),
  rmsUpdateSection: document.getElementById('rms-update-section'),
  rmsApplyUpdateBtn: document.getElementById('rms-apply-update-btn'),
  rmsStudentUpdateMsg: document.getElementById('rms-student-update-msg'),
  rmsAdminDedicatedNote: document.getElementById('rms-admin-dedicated-note'),
  rmsAttendanceRegistration: document.getElementById('rms-attendance-registration'),
  rmsAttendanceSearchBtn: document.getElementById('rms-attendance-search-btn'),
  rmsAttendanceStudentSummary: document.getElementById('rms-attendance-student-summary'),
  rmsAttendanceSubjectSelect: document.getElementById('rms-attendance-subject-select'),
  rmsAttendanceSlotSelect: document.getElementById('rms-attendance-slot-select'),
  rmsAttendanceDate: document.getElementById('rms-attendance-date'),
  rmsAttendanceCurrentStatus: document.getElementById('rms-attendance-current-status'),
  rmsAttendanceStatus: document.getElementById('rms-attendance-status'),
  rmsAttendanceNote: document.getElementById('rms-attendance-note'),
  rmsAttendanceApplyBtn: document.getElementById('rms-attendance-apply-btn'),
  rmsAttendanceStatusMsg: document.getElementById('rms-attendance-status-msg'),
  rmsAttendanceResult: document.getElementById('rms-attendance-result'),
  classroomPhotoInput: document.getElementById('classroom-photo-input'),
  captureClassroomBtn: document.getElementById('capture-classroom-btn'),
  analyzeClassroomBtn: document.getElementById('analyze-classroom-btn'),
  classroomPhotoPreview: document.getElementById('classroom-photo-preview'),
  classroomAnalysisOutput: document.getElementById('classroom-analysis-output'),
  classroomAnalysisHistory: document.getElementById('classroom-analysis-history'),

  cameraModal: document.getElementById('camera-modal'),
  cameraTitle: document.getElementById('camera-title'),
  cameraReferenceWrap: document.getElementById('camera-reference-wrap'),
  cameraReferencePhoto: document.getElementById('camera-reference-photo'),
  cameraVideo: document.getElementById('camera-video'),
  cameraCanvas: document.getElementById('camera-canvas'),
  cameraMessage: document.getElementById('camera-message'),
  cameraCaptureBtn: document.getElementById('camera-capture-btn'),
  cameraCloseBtn: document.getElementById('camera-close-btn'),
};

const NUMERIC_METRICS = [
  ['metricBlocks', 'blocks'],
  ['metricClassrooms', 'classrooms'],
  ['metricCourses', 'courses'],
  ['metricFaculty', 'faculty'],
  ['metricStudents', 'students'],
];

function log(message) {
  if (!els.statusLog) {
    return;
  }
  const skeleton = els.statusLog.querySelector('.status-log-skeleton');
  if (skeleton) {
    skeleton.remove();
  }
  const line = document.createElement('div');
  line.className = 'log-line';
  line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  els.statusLog.prepend(line);
}

function normalizeUiState(state = 'neutral') {
  const candidate = String(state || '').trim().toLowerCase();
  if (candidate === 'loading' || candidate === 'empty' || candidate === 'error' || candidate === 'success') {
    return candidate;
  }
  return 'neutral';
}

function setUiStateMessage(element, message, { state = 'neutral' } = {}) {
  if (!element) {
    return;
  }
  const normalizedState = normalizeUiState(state);
  element.textContent = String(message || '');
  element.dataset.uiState = normalizedState;
  element.classList.add('ui-state');
  element.classList.toggle('error-text', normalizedState === 'error');
}

function setAuthMessage(message, isError = false, state = 'neutral') {
  setUiStateMessage(els.authMessage, message, {
    state: isError ? 'error' : state,
  });
}

function setForgotMessage(message, isError = false, state = 'neutral') {
  if (!els.forgotMessage) {
    return;
  }
  setUiStateMessage(els.forgotMessage, message || '', {
    state: isError ? 'error' : state,
  });
}

function isPrivilegedMfaRole(role) {
  const value = String(role || '').trim().toLowerCase();
  return value === 'admin' || value === 'faculty' || value === 'owner';
}

function isMfaEnrollmentRequiredMessage(message = '') {
  const text = String(message || '').trim().toLowerCase();
  return text.includes('mfa enrollment is required')
    || (text.includes('/auth/mfa/enroll') && text.includes('/auth/mfa/activate'));
}

function isMfaCodeRequiredMessage(message = '') {
  const text = String(message || '').trim().toLowerCase();
  return text.includes('mfa code is required')
    || text.includes('valid totp')
    || text.includes('backup code');
}

function setAuthMfaInputVisible(visible, helpMessage = '') {
  const show = Boolean(visible);
  setHidden(els.authMfaWrap, !show);
  if (els.authMfaHelp) {
    setHidden(els.authMfaHelp, !show);
    if (show && helpMessage) {
      els.authMfaHelp.textContent = String(helpMessage);
    } else if (!show) {
      els.authMfaHelp.textContent = 'Enter authenticator app code (or backup code) for privileged accounts with MFA enabled.';
    }
  }
  if (!show && els.authMfaCode) {
    els.authMfaCode.value = '';
  }
}

function setMfaSetupMessage(message, isError = false, state = 'neutral') {
  if (!els.mfaSetupStatus) {
    return;
  }
  setUiStateMessage(els.mfaSetupStatus, message || '', {
    state: isError ? 'error' : state,
  });
}

function setMfaActionBusyState() {
  const enrollBusy = Boolean(authState.mfaEnrollInFlight);
  const activateBusy = Boolean(authState.mfaActivateInFlight);
  if (els.mfaEnrollBtn) {
    els.mfaEnrollBtn.disabled = enrollBusy || activateBusy;
    els.mfaEnrollBtn.textContent = enrollBusy ? 'Generating Setup...' : 'Start MFA Enrollment';
  }
  if (els.mfaActivateBtn) {
    const normalizedTotpCode = String(els.mfaTotpCode?.value || '').replace(/\D+/g, '');
    const hasTotpCode = normalizedTotpCode.length === 6;
    els.mfaActivateBtn.disabled = enrollBusy || activateBusy || !hasTotpCode;
    els.mfaActivateBtn.textContent = activateBusy ? 'Activating...' : 'Activate MFA';
  }
}

function resetMfaCopyButtonLabels() {
  if (els.mfaCopySecretBtn) {
    els.mfaCopySecretBtn.textContent = 'Copy';
  }
  if (els.mfaCopyUriBtn) {
    els.mfaCopyUriBtn.textContent = 'Copy';
  }
}

function syncMfaCopyButtonsState() {
  if (els.mfaCopySecretBtn) {
    els.mfaCopySecretBtn.disabled = !Boolean((els.mfaSecret?.value || '').trim());
  }
  if (els.mfaCopyUriBtn) {
    els.mfaCopyUriBtn.disabled = !Boolean((els.mfaOtpauthUri?.value || '').trim());
  }
}

async function copyTextToClipboard(value) {
  const text = String(value || '').trim();
  if (!text) {
    return false;
  }
  if (navigator?.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_error) {
      // Fallback to document.execCommand when Clipboard API is blocked.
    }
  }
  const ghost = document.createElement('textarea');
  ghost.value = text;
  ghost.setAttribute('readonly', 'readonly');
  ghost.style.position = 'fixed';
  ghost.style.left = '-9999px';
  ghost.style.opacity = '0';
  document.body.appendChild(ghost);
  ghost.select();
  ghost.setSelectionRange(0, ghost.value.length);
  let copied = false;
  try {
    copied = document.execCommand('copy');
  } catch (_error) {
    copied = false;
  }
  ghost.remove();
  return copied;
}

function showMfaCopyButtonFeedback(button, label = 'Copied') {
  if (!button) {
    return;
  }
  button.textContent = label;
  window.clearTimeout(showMfaCopyButtonFeedback._timerById?.get(button));
  if (!showMfaCopyButtonFeedback._timerById) {
    showMfaCopyButtonFeedback._timerById = new Map();
  }
  const timer = window.setTimeout(() => {
    button.textContent = 'Copy';
    showMfaCopyButtonFeedback._timerById.delete(button);
  }, 1400);
  showMfaCopyButtonFeedback._timerById.set(button, timer);
}

function renderMfaSetupData(payload = null) {
  const data = payload && typeof payload === 'object' ? payload : null;
  authState.mfaSetup = data;
  if (els.mfaQrImage && els.mfaQrEmpty) {
    const qrPayload = data?.qr_svg_data_uri ? String(data.qr_svg_data_uri) : '';
    if (qrPayload) {
      els.mfaQrImage.src = qrPayload;
      els.mfaQrImage.classList.remove('hidden');
      els.mfaQrEmpty.textContent = 'Scan using Google Authenticator / Microsoft Authenticator / Authy.';
    } else {
      els.mfaQrImage.removeAttribute('src');
      els.mfaQrImage.classList.add('hidden');
      els.mfaQrEmpty.textContent = 'QR is unavailable in this runtime. Use manual setup key below.';
    }
  }
  if (els.mfaSecret) {
    els.mfaSecret.value = data?.secret ? String(data.secret) : '';
  }
  if (els.mfaOtpauthUri) {
    els.mfaOtpauthUri.value = data?.otpauth_uri ? String(data.otpauth_uri) : '';
  }
  if (els.mfaSetupExpires) {
    if (data?.setup_expires_at) {
      const expiresAt = new Date(String(data.setup_expires_at));
      const label = Number.isNaN(expiresAt.getTime())
        ? String(data.setup_expires_at)
        : expiresAt.toLocaleString();
      els.mfaSetupExpires.textContent = `Setup expires at: ${label}`;
    } else {
      els.mfaSetupExpires.textContent = 'Setup session details will appear after enrollment.';
    }
  }
  if (els.mfaBackupCodes) {
    els.mfaBackupCodes.innerHTML = '';
    const codes = Array.isArray(data?.backup_codes) ? data.backup_codes : [];
    if (!codes.length) {
      const empty = document.createElement('li');
      empty.className = 'mfa-backup-code mfa-backup-code-empty';
      empty.textContent = 'No backup codes yet. Generate by starting enrollment.';
      els.mfaBackupCodes.appendChild(empty);
    } else {
      for (const code of codes) {
        const item = document.createElement('li');
        item.className = 'mfa-backup-code';
        item.textContent = String(code || '');
        els.mfaBackupCodes.appendChild(item);
      }
    }
  }
  resetMfaCopyButtonLabels();
  syncMfaCopyButtonsState();
}

function setMfaSetupModal(open) {
  if (!els.mfaSetupModal) {
    return;
  }
  setHidden(els.mfaSetupModal, !open);
  if (!open) {
    setMfaHelpModal(false);
  }
}

function setMfaHelpModal(open) {
  if (!els.mfaHelpModal) {
    return;
  }
  const shouldOpen = Boolean(open);
  setHidden(els.mfaHelpModal, !shouldOpen);
  if (!shouldOpen && els.mfaSetupModal && !els.mfaSetupModal.classList.contains('hidden')) {
    syncModalFocusTrap(els.mfaSetupModal);
  }
}

function resetMfaSetupUiState() {
  authState.mfaEnrollInFlight = false;
  authState.mfaActivateInFlight = false;
  authState.mfaSetup = null;
  renderMfaSetupData(null);
  if (els.mfaQrConfirm) {
    els.mfaQrConfirm.checked = false;
  }
  if (els.mfaTotpCode) {
    els.mfaTotpCode.value = '';
  }
  setMfaSetupMessage('');
  setMfaActionBusyState();
}

function maybeShowMfaGuidePrompt() {
  const email = String(authState.user?.email || '').trim().toLowerCase();
  if (!email) {
    return;
  }
  if (hasSeenMfaGuidePrompt(email)) {
    return;
  }
  markMfaGuidePromptSeen(email);
  setMfaHelpModal(true);
}

function openMfaSetupModalForStatus(status = null, triggerMessage = 'MFA enrollment is required for this account.') {
  openAuthOverlay(triggerMessage);
  authState.mfaSetupRequired = true;
  setAuthMfaInputVisible(false);
  setAuthMessage('MFA enrollment is required for admin/faculty accounts. Complete setup below to continue.', true);
  resetMfaSetupUiState();
  if (status?.setup_pending && status?.setup_expires_at && els.mfaSetupExpires) {
    const expiresAt = new Date(String(status.setup_expires_at));
    const label = Number.isNaN(expiresAt.getTime())
      ? String(status.setup_expires_at)
      : expiresAt.toLocaleString();
    els.mfaSetupExpires.textContent = `A pending setup already exists. You can restart enrollment. Pending setup expires at: ${label}`;
  }
  setMfaSetupMessage('Start MFA enrollment, add secret to your authenticator app, then activate using TOTP.', false, 'neutral');
  setMfaSetupModal(true);
  maybeShowMfaGuidePrompt();
}

async function openMfaSetupFromAccountMenu() {
  if (!authState.user || !authState.token) {
    openAuthOverlay('Sign in first to complete MFA setup.');
    return;
  }
  if (!isPrivilegedMfaRole(authState.user.role)) {
    log('MFA setup is only available for privileged roles.');
    return;
  }
  const status = await api('/auth/mfa/status');
  const required = Boolean(status?.required);
  const enabled = Boolean(status?.enabled || authState.user?.mfa_enabled);
  if (!required) {
    log('MFA enrollment is not required for this account.');
    return;
  }
  if (enabled) {
    log('MFA is already enabled for this account.');
    return;
  }
  openMfaSetupModalForStatus(status, 'MFA enrollment is required for this account.');
}

async function maybePromptPrivilegedMfaSetup(triggerMessage = '') {
  if (!authState.user || !authState.token || !isPrivilegedMfaRole(authState.user.role)) {
    authState.mfaSetupRequired = false;
    return false;
  }
  if (authState.mfaSetupRequired && els.mfaSetupModal && !els.mfaSetupModal.classList.contains('hidden')) {
    return true;
  }
  let status = null;
  try {
    status = await api('/auth/mfa/status');
  } catch (error) {
    log(error?.message || 'Unable to load MFA status.');
    return false;
  }
  const required = Boolean(status?.required);
  const enabled = Boolean(status?.enabled || authState.user?.mfa_enabled);
  if (!required || enabled) {
    authState.mfaSetupRequired = false;
    return false;
  }

  openMfaSetupModalForStatus(status, triggerMessage || 'MFA enrollment is required for this account.');
  return true;
}

async function enrollMfaSetup() {
  if (authState.mfaEnrollInFlight || authState.mfaActivateInFlight) {
    return;
  }
  const hasExistingSetup = Boolean((authState.mfaSetup?.secret || '').trim());
  if (hasExistingSetup) {
    const shouldRegenerate = window.confirm(
      'Start MFA Enrollment will regenerate your secret and invalidate the previously scanned QR. Continue?'
    );
    if (!shouldRegenerate) {
      return;
    }
  }
  authState.mfaEnrollInFlight = true;
  setMfaActionBusyState();
  setMfaSetupMessage('Generating MFA secret and backup codes...', false, 'loading');
  try {
    const data = await api('/auth/mfa/enroll', { method: 'POST' });
    renderMfaSetupData(data);
    setMfaSetupMessage('MFA setup generated. Save backup codes securely, then activate with TOTP.', false, 'success');
    log('MFA enrollment initiated');
  } catch (error) {
    setMfaSetupMessage(error?.message || 'Unable to start MFA enrollment.', true);
    throw error;
  } finally {
    authState.mfaEnrollInFlight = false;
    setMfaActionBusyState();
  }
}

async function activateMfaSetup() {
  if (authState.mfaActivateInFlight || authState.mfaEnrollInFlight) {
    return;
  }
  const totpCode = String(els.mfaTotpCode?.value || '').replace(/\D+/g, '');
  if (els.mfaTotpCode) {
    els.mfaTotpCode.value = totpCode;
  }
  if (totpCode.length !== 6) {
    throw new Error('Enter a valid 6-digit authenticator TOTP code.');
  }
  authState.mfaActivateInFlight = true;
  setMfaActionBusyState();
  setMfaSetupMessage('Activating MFA...', false, 'loading');
  try {
    await api('/auth/mfa/activate', {
      method: 'POST',
      body: JSON.stringify({ totp_code: totpCode }),
    });
    authState.mfaSetupRequired = false;
    if (authState.user && typeof authState.user === 'object') {
      authState.user.mfa_enabled = true;
    }
    setMfaSetupMessage('MFA activated. Continuing to dashboard...', false, 'success');
    log('MFA activated');
    setMfaSetupModal(false);
    setAuthMfaInputVisible(false);
    const restored = await restoreSession();
    if (restored) {
      await refreshAll();
    }
  } catch (error) {
    setMfaSetupMessage(error?.message || 'Unable to activate MFA.', true);
    throw error;
  } finally {
    authState.mfaActivateInFlight = false;
    setMfaActionBusyState();
  }
}

function passwordStrengthMeta(password) {
  const value = String(password || '');
  const checks = {
    minLen: value.length >= 8,
    letter: /[A-Za-z]/.test(value),
    digit: /\d/.test(value),
    special: /[^A-Za-z0-9]/.test(value),
  };
  const score = Object.values(checks).filter(Boolean).length;
  return {
    checks,
    score,
    valid: score === 4,
  };
}

function passwordMissingList(meta) {
  const missing = [];
  if (!meta.checks.minLen) missing.push('8+ characters');
  if (!meta.checks.letter) missing.push('letters');
  if (!meta.checks.digit) missing.push('numbers');
  if (!meta.checks.special) missing.push('special character');
  return missing;
}

function renderPasswordStrengthHint(element, password) {
  if (!element) {
    return;
  }
  element.classList.remove('weak', 'medium', 'strong');
  const value = String(password || '');
  if (!value) {
    element.textContent = `Password: ${PASSWORD_POLICY_TEXT}`;
    return;
  }

  const meta = passwordStrengthMeta(value);
  if (meta.valid) {
    element.classList.add('strong');
    element.textContent = 'Strong password. Requirements satisfied.';
    return;
  }

  const missing = passwordMissingList(meta).join(', ');
  if (meta.score >= 2) {
    element.classList.add('medium');
    element.textContent = `Almost there. Add: ${missing}.`;
    return;
  }
  element.classList.add('weak');
  element.textContent = `Weak password. Add: ${missing}.`;
}

function validatePasswordStrengthOrThrow(password, label = 'Password') {
  const meta = passwordStrengthMeta(password);
  if (!meta.valid) {
    throw new Error(`${label} must be at least 8 characters and include letters, numbers, and special characters.`);
  }
}

function isForgotPasswordPanelOpen() {
  return Boolean(els.forgotPasswordPanel && !els.forgotPasswordPanel.classList.contains('hidden'));
}

function resetForgotPasswordState({ clearFields = false } = {}) {
  authState.forgotResetToken = '';
  authState.forgotResetTokenExpiresAt = '';
  authState.forgotOtpRequestInFlight = false;
  authState.forgotOtpCooldownUntilMs = 0;
  stopForgotOtpCooldownTicker();
  if (!clearFields) {
    renderForgotOtpCooldown();
    return;
  }
  if (els.forgotOtp) {
    els.forgotOtp.value = '';
  }
  if (els.forgotEmail) {
    els.forgotEmail.value = '';
  }
  if (els.forgotRegistrationNumber) {
    els.forgotRegistrationNumber.value = '';
  }
  if (els.forgotNewPassword) {
    els.forgotNewPassword.value = '';
  }
  if (els.forgotConfirmPassword) {
    els.forgotConfirmPassword.value = '';
  }
  setForgotMessage('');
  renderPasswordStrengthHint(els.forgotPasswordStrength, '');
  renderForgotOtpCooldown();
}

function setForgotPasswordPanel(open) {
  if (!els.forgotPasswordPanel) {
    return;
  }
  const shouldOpen = Boolean(open) && !isSignupMode();
  setHidden(els.forgotPasswordPanel, !shouldOpen);
  if (shouldOpen) {
    const loginEmail = (els.authEmail?.value || '').trim().toLowerCase();
    if (loginEmail && els.forgotEmail && !els.forgotEmail.value.trim()) {
      els.forgotEmail.value = loginEmail;
    }
    setForgotMessage('Enter email + registration number, then request OTP.');
    renderPasswordStrengthHint(els.forgotPasswordStrength, els.forgotNewPassword?.value || '');
  } else {
    resetForgotPasswordState({ clearFields: false });
  }
  renderOtpCooldown();
  renderForgotOtpCooldown();
}

function hideOtpPopup() {
  if (!els.otpPopup) {
    return;
  }
  if (els.otpPopupLoader) {
    els.otpPopupLoader.classList.add('hidden');
  }
  if (els.otpPopupCloseBtn) {
    els.otpPopupCloseBtn.disabled = false;
    els.otpPopupCloseBtn.classList.remove('hidden');
  }
  const card = els.otpPopup.querySelector('.otp-popup-card');
  if (card) {
    card.dataset.tone = 'info';
  }
  els.otpPopup.classList.add('hidden');
}

function showOtpPopup(title, text, options = {}) {
  if (!els.otpPopup || !els.otpPopupTitle || !els.otpPopupText) {
    return;
  }
  const tone = String(options.tone || 'info');
  const loading = Boolean(options.loading);
  const closable = options.closable !== false;
  const card = els.otpPopup.querySelector('.otp-popup-card');
  if (card) {
    card.dataset.tone = tone;
  }
  if (els.otpPopupLoader) {
    els.otpPopupLoader.classList.toggle('hidden', !loading);
  }
  if (els.otpPopupCloseBtn) {
    els.otpPopupCloseBtn.disabled = !closable;
    els.otpPopupCloseBtn.classList.toggle('hidden', !closable);
  }
  els.otpPopupTitle.textContent = title;
  els.otpPopupText.textContent = text;
  els.otpPopup.classList.remove('hidden');
}

function showFoodPopup(title, text, { isError = false, autoHideMs = 2200 } = {}) {
  if (!document.body.classList.contains('auth-open')) {
    showFoodToast(title, text, { isError, autoHideMs });
    return;
  }
  showOtpPopup(title, text, { tone: isError ? 'danger' : 'success' });
  if (foodPopupTimer) {
    window.clearTimeout(foodPopupTimer);
    foodPopupTimer = null;
  }
  const hideAfter = Number(autoHideMs || 0);
  if (hideAfter > 0) {
    foodPopupTimer = window.setTimeout(() => {
      if (!isForgotPasswordPanelOpen()) {
        hideOtpPopup();
      }
      foodPopupTimer = null;
    }, hideAfter);
  }
}

function hideFoodToast() {
  if (!els.foodToast) {
    return;
  }
  els.foodToast.classList.add('hidden');
  if (foodToastTimer) {
    window.clearTimeout(foodToastTimer);
    foodToastTimer = null;
  }
}

function showFoodToast(title, text, { isError = false, autoHideMs = 1800 } = {}) {
  if (!els.foodToast || !els.foodToastTitle || !els.foodToastText) {
    return;
  }
  if (els.foodToastCard) {
    els.foodToastCard.dataset.tone = isError ? 'error' : 'success';
  }
  els.foodToastTitle.textContent = String(title || 'Update');
  els.foodToastText.textContent = String(text || '');
  els.foodToast.classList.remove('hidden');
  if (foodToastTimer) {
    window.clearTimeout(foodToastTimer);
    foodToastTimer = null;
  }
  const hideAfter = Number(autoHideMs || 0);
  if (hideAfter > 0) {
    foodToastTimer = window.setTimeout(() => {
      hideFoodToast();
    }, hideAfter);
  }
}

function setOtpRequestInFlight(flag) {
  authState.otpRequestInFlight = Boolean(flag);
  renderOtpCooldown();
}

function setOtpVerifyInFlight(flag) {
  authState.otpVerifyInFlight = Boolean(flag);
  renderOtpCooldown();
}

function setRegisterInFlight(flag) {
  authState.registerInFlight = Boolean(flag);
  if (!els.registerBtn) {
    return;
  }
  els.registerBtn.disabled = authState.registerInFlight;
  els.registerBtn.textContent = authState.registerInFlight ? 'Registering...' : 'Register Account';
}

function setForgotOtpRequestInFlight(flag) {
  authState.forgotOtpRequestInFlight = Boolean(flag);
  renderForgotOtpCooldown();
}

function getOtpCooldownRemainingSeconds() {
  const remainingMs = Number(authState.otpCooldownUntilMs || 0) - Date.now();
  return Math.max(0, Math.ceil(remainingMs / 1000));
}

function renderOtpCooldown() {
  if (!els.requestOtpBtn) {
    return;
  }
  const remaining = getOtpCooldownRemainingSeconds();
  const cooldownActive = remaining > 0;
  const otpLoading = Boolean(authState.otpRequestInFlight);
  const verifyLoading = Boolean(authState.otpVerifyInFlight);
  const loginMode = !isSignupMode();
  const forgotActive = isForgotPasswordPanelOpen();
  els.requestOtpBtn.disabled = otpLoading || cooldownActive || !loginMode || forgotActive;
  if (els.verifyOtpBtn) {
    els.verifyOtpBtn.disabled = !loginMode || forgotActive || verifyLoading;
    els.verifyOtpBtn.textContent = verifyLoading ? 'Verifying...' : 'Verify OTP & Login';
  }
  if (otpLoading) {
    els.requestOtpBtn.textContent = 'Sending OTP...';
    return;
  }
  els.requestOtpBtn.textContent = cooldownActive ? `Request OTP (${remaining}s)` : 'Request OTP';
}

function stopOtpCooldownTicker() {
  if (otpCooldownTimer) {
    window.clearInterval(otpCooldownTimer);
    otpCooldownTimer = null;
  }
}

function startOtpCooldown(seconds = 30) {
  const safeSeconds = Math.max(1, Number(seconds) || 30);
  authState.otpCooldownUntilMs = Date.now() + (safeSeconds * 1000);
  stopOtpCooldownTicker();
  renderOtpCooldown();
  otpCooldownTimer = window.setInterval(() => {
    renderOtpCooldown();
    if (getOtpCooldownRemainingSeconds() <= 0) {
      stopOtpCooldownTicker();
    }
  }, 250);
}

function getForgotOtpCooldownRemainingSeconds() {
  const remainingMs = Number(authState.forgotOtpCooldownUntilMs || 0) - Date.now();
  return Math.max(0, Math.ceil(remainingMs / 1000));
}

function renderForgotOtpCooldown() {
  if (!els.forgotRequestOtpBtn) {
    return;
  }
  const remaining = getForgotOtpCooldownRemainingSeconds();
  const cooldownActive = remaining > 0;
  const loading = Boolean(authState.forgotOtpRequestInFlight);
  if (loading) {
    els.forgotRequestOtpBtn.disabled = true;
    els.forgotRequestOtpBtn.textContent = 'Sending...';
  } else {
    els.forgotRequestOtpBtn.disabled = cooldownActive;
    els.forgotRequestOtpBtn.textContent = cooldownActive
      ? `Request Reset OTP (${remaining}s)`
      : 'Request Reset OTP';
  }
  if (els.forgotResetBtn) {
    els.forgotResetBtn.disabled = !authState.forgotResetToken;
  }
}

function stopForgotOtpCooldownTicker() {
  if (forgotOtpCooldownTimer) {
    window.clearInterval(forgotOtpCooldownTimer);
    forgotOtpCooldownTimer = null;
  }
}

function startForgotOtpCooldown(seconds = 30) {
  const safeSeconds = Math.max(1, Number(seconds) || 30);
  authState.forgotOtpCooldownUntilMs = Date.now() + (safeSeconds * 1000);
  stopForgotOtpCooldownTicker();
  renderForgotOtpCooldown();
  forgotOtpCooldownTimer = window.setInterval(() => {
    renderForgotOtpCooldown();
    if (getForgotOtpCooldownRemainingSeconds() <= 0) {
      stopForgotOtpCooldownTicker();
    }
  }, 250);
}

function openAuthOverlay(message = 'Sign in to continue.') {
  closeAccountDropdown();
  stopFoodDemandLiveTicker();
  document.body.classList.add('auth-open');
  els.authOverlay.classList.remove('hidden');
  setMfaSetupModal(false);
  authState.mfaSetupRequired = false;
  resetMfaSetupUiState();
  setAuthMfaInputVisible(false);
  hideOtpPopup();
  setAuthMode('login');
  setForgotPasswordPanel(false);
  resetForgotPasswordState({ clearFields: true });
  setAuthMessage(message);
}

function closeAuthOverlay() {
  document.body.classList.remove('auth-open');
  document.body.classList.remove('auth-signup-mode');
  els.authOverlay.classList.add('hidden');
  setMfaSetupModal(false);
  hideOtpPopup();
  syncFoodDemandLiveTicker();
}

function closeAccountDropdown() {
  if (!els.accountMenuDropdown || !els.accountMenuBtn) {
    return;
  }
  els.accountMenuDropdown.classList.add('hidden');
  els.accountMenuBtn.setAttribute('aria-expanded', 'false');
}

function normalizeTheme(raw) {
  const value = String(raw || '').trim().toLowerCase();
  if (value === 'light' || value === 'dark') {
    return value;
  }
  return '';
}

function themeStorageKey(userEmail = '') {
  const normalizedEmail = String(userEmail || '').trim().toLowerCase() || 'guest';
  return normalizedEmail;
}

function profilePromptStorageKey(userEmail = '') {
  const normalizedEmail = String(userEmail || '').trim().toLowerCase() || 'guest';
  return normalizedEmail;
}

function mfaGuideStorageKey(userEmail = '') {
  const normalizedEmail = String(userEmail || '').trim().toLowerCase() || 'guest';
  return normalizedEmail;
}

function hasSeenProfileSetupPrompt(userEmail = '') {
  return runtimeUiStore.profilePromptSeenByUser.has(profilePromptStorageKey(userEmail));
}

function markProfileSetupPromptSeen(userEmail = '') {
  runtimeUiStore.profilePromptSeenByUser.add(profilePromptStorageKey(userEmail));
}

function hasSeenMfaGuidePrompt(userEmail = '') {
  return runtimeUiStore.mfaGuideSeenByUser.has(mfaGuideStorageKey(userEmail));
}

function markMfaGuidePromptSeen(userEmail = '') {
  runtimeUiStore.mfaGuideSeenByUser.add(mfaGuideStorageKey(userEmail));
}

function getInitialTheme(userEmail = '') {
  const scoped = normalizeTheme(runtimeUiStore.themeByUser.get(themeStorageKey(userEmail)));
  if (scoped) {
    return scoped;
  }
  return 'light';
}

function applyDaylightTint(now = new Date()) {
  const hour = Number(now?.getHours?.());
  const isWarm = Number.isFinite(hour) && hour >= 17;
  document.body.classList.toggle('ums-daylight-warm', isWarm);
  document.body.classList.toggle('ums-daylight-day', !isWarm);
}

function syncTopNavActiveButtonIntoView() {
  if (window.matchMedia('(max-width: 700px)').matches) {
    return;
  }
  const activeButton = [
    els.topNavAttendanceBtn,
    els.topNavSaarthiBtn,
    els.topNavFoodBtn,
    els.topNavAdministrativeBtn,
    els.topNavRmsBtn,
    els.topNavRemedialBtn,
  ].find((button) => button && button.classList.contains('active'));
  if (!activeButton || typeof activeButton.scrollIntoView !== 'function') {
    return;
  }
  activeButton.scrollIntoView({
    behavior: 'auto',
    block: 'nearest',
    inline: 'nearest',
  });
}

function applyTheme(theme, options = {}) {
  const { persist = true, userEmail = authState.user?.email || '' } = options;
  const resolved = theme === 'light' ? 'light' : 'dark';
  state.ui.theme = resolved;
  document.body.classList.toggle('ums-theme', resolved === 'light');
  applyDaylightTint(new Date());
  if (persist) {
    runtimeUiStore.themeByUser.set(themeStorageKey(userEmail), resolved);
  }

  if (els.themeToggleBtn) {
    els.themeToggleBtn.textContent = resolved === 'dark' ? 'Light Mode' : 'Dark Mode';
    els.themeToggleBtn.setAttribute(
      'aria-label',
      resolved === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'
    );
  }
  window.requestAnimationFrame(() => {
    syncTopNavActiveButtonIntoView();
  });
}

function toggleTheme() {
  applyTheme(state.ui.theme === 'dark' ? 'light' : 'dark', {
    persist: true,
    userEmail: authState.user?.email || '',
  });
}

function bindStaticAssetFallbacks() {
  document.querySelectorAll('img[data-fallback-src]').forEach((image) => {
    if (!(image instanceof HTMLImageElement)) {
      return;
    }

    image.addEventListener('error', () => {
      const fallbackSrc = String(image.dataset.fallbackSrc || '').trim();
      if (!fallbackSrc) {
        return;
      }
      const currentSrc = String(image.getAttribute('src') || '').trim();
      if (!currentSrc || currentSrc === fallbackSrc) {
        return;
      }
      image.setAttribute('src', fallbackSrc);
    }, { once: true });
  });
}

function formatUtcOffsetLabel(offsetMinutes) {
  const normalized = Number.isFinite(offsetMinutes) ? Math.trunc(offsetMinutes) : 0;
  const sign = normalized >= 0 ? '+' : '-';
  const absolute = Math.abs(normalized);
  const hours = String(Math.floor(absolute / 60)).padStart(2, '0');
  const minutes = String(absolute % 60).padStart(2, '0');
  return `UTC${sign}${hours}:${minutes}`;
}

function extractTimeZoneName(formatter, dateValue) {
  const parts = formatter.formatToParts(dateValue);
  const zonePart = parts.find((part) => part.type === 'timeZoneName');
  return String(zonePart?.value || '').trim();
}

function renderLiveDateTime() {
  if (!els.liveDateTime) {
    return;
  }
  const now = new Date();
  const dateLabel = LIVE_DATE_FORMATTER.format(now);
  const timeLabel = LIVE_TIME_FORMATTER.format(now);
  const zoneShort = extractTimeZoneName(LIVE_TIMEZONE_SHORT_FORMATTER, now) || 'Local';
  const zoneLong = extractTimeZoneName(LIVE_TIMEZONE_LONG_FORMATTER, now);
  const utcOffset = formatUtcOffsetLabel(-now.getTimezoneOffset());
  const nextLabel = `${dateLabel} • ${timeLabel} ${zoneShort} (${utcOffset})`;

  if (nextLabel !== liveDateTimeLabelCache) {
    liveDateTimeLabelCache = nextLabel;
    els.liveDateTime.textContent = nextLabel;
  }

  const tooltip = `${LIVE_DATE_TOOLTIP_FORMATTER.format(now)}${zoneLong ? ` • ${zoneLong}` : ''} • ${utcOffset}`;
  els.liveDateTime.setAttribute('title', tooltip);
  els.liveDateTime.setAttribute('datetime', now.toISOString());

  const nowMs = now.getTime();
  if (nowMs - liveDateUtilityLastRunMs >= LIVE_OPERATIONAL_REFRESH_MS) {
    liveDateUtilityLastRunMs = nowMs;
    applyDaylightTint(now);
    renderFoodFreshnessIndicators();
    renderFoodDemandFreshnessIndicator();
    applyFoodRealtimeAvailability({ showStatusOnTransition: true });
  }
}

function startLiveDateTimeTicker() {
  renderLiveDateTime();
  if (liveDateTimeTimer) {
    clearInterval(liveDateTimeTimer);
  }
  liveDateTimeTimer = setInterval(renderLiveDateTime, 1000);
}

function stopStudentRealtimeTicker() {
  if (!studentRealtimeTimer) {
    return;
  }
  clearInterval(studentRealtimeTimer);
  studentRealtimeTimer = null;
}

function stopStudentTimetableStatusTicker() {
  if (!studentTimetableStatusTimer) {
    return;
  }
  clearInterval(studentTimetableStatusTimer);
  studentTimetableStatusTimer = null;
}

function startStudentTimetableStatusTicker() {
  if (studentTimetableStatusTimer) {
    return;
  }
  studentTimetableStatusTimer = setInterval(() => {
    if (authState.user?.role !== 'student') {
      return;
    }
    refreshStudentTimetableRealtimeStatus();
  }, 1000);
}

function startStudentRealtimeTicker() {
  // Student attendance/message realtime is event-driven via SSE route modules.
  stopStudentRealtimeTicker();
}

function stopModuleRealtimeTicker() {
  if (!moduleRealtimeTimer) {
    return;
  }
  clearInterval(moduleRealtimeTimer);
  moduleRealtimeTimer = null;
  moduleRealtimeBusy = false;
}

function startModuleRealtimeTicker() {
  stopModuleRealtimeTicker();
}

function canRunRemedialLiveTicker() {
  if (!authState.user || authState.user.role !== 'student') {
    return false;
  }
  if (document.body.classList.contains('auth-open')) {
    return false;
  }
  const activeModule = getSanitizedModuleKey(state.ui.activeModule);
  return activeModule === 'attendance' || activeModule === 'remedial';
}

function stopRemedialLiveTicker() {
  if (!remedialLiveTimer) {
    return;
  }
  window.clearInterval(remedialLiveTimer);
  remedialLiveTimer = null;
  remedialLiveBusy = false;
}

function startRemedialLiveTicker() {
  // Remedial + message updates are event-driven via SSE route modules.
  stopRemedialLiveTicker();
}

function syncRemedialLiveTicker() {
  stopRemedialLiveTicker();
}

function getActiveProfilePhotoDataUrl() {
  const role = authState.user?.role;
  if (role === 'faculty') {
    return state.facultyProfile.profilePhotoDataUrl || state.facultyProfile.pendingProfilePhotoDataUrl || '';
  }
  if (role === 'student') {
    return state.student.profilePhotoDataUrl || state.student.pendingProfilePhotoDataUrl || '';
  }
  return '';
}

function normalizeProfileName(value) {
  return String(value || '').trim().replace(/\s+/g, ' ');
}

function getActiveProfileName() {
  const role = authState.user?.role;
  if (role === 'faculty') {
    return normalizeProfileName(state.facultyProfile.name || authState.user?.name || '');
  }
  if (role === 'student') {
    return normalizeProfileName(state.student.name || authState.user?.name || '');
  }
  return normalizeProfileName(authState.user?.name || '');
}

function hasValidProfileName(value) {
  return normalizeProfileName(value).length >= 2;
}

function getAccountIdentitySummary() {
  const role = authState.user?.role || 'unauthenticated';
  if (role === 'student') {
    return {
      label: 'Reg No',
      value: state.student.registrationNumber || 'Not set',
    };
  }
  if (role === 'faculty') {
    return {
      label: 'Faculty ID',
      value: state.facultyProfile.facultyIdentifier || 'Not set',
    };
  }
  if (role === 'owner') {
    return {
      label: 'Vendor ID',
      value: authState.user?.id ? `OWNER-${authState.user.id}` : 'Not set',
    };
  }
  return {
    label: 'Role',
    value: role,
  };
}

function renderAccountMenuProfile() {
  const photo = getActiveProfilePhotoDataUrl();
  const email = authState.user?.email || 'guest@example.com';
  const displayName = getActiveProfileName() || email;
  const identity = getAccountIdentitySummary();

  if (els.accountDropdownEmail) {
    els.accountDropdownEmail.textContent = displayName;
  }
  if (els.accountDropdownReg) {
    els.accountDropdownReg.textContent = `${email} • ${identity.label}: ${identity.value}`;
  }

  if (els.accountMenuInitial) {
    els.accountMenuInitial.textContent = displayName.charAt(0).toUpperCase() || 'G';
  }

  if (els.accountDropdownPhoto) {
    if (photo) {
      els.accountDropdownPhoto.src = photo;
      els.accountDropdownPhoto.classList.remove('hidden');
    } else {
      els.accountDropdownPhoto.removeAttribute('src');
      els.accountDropdownPhoto.classList.add('hidden');
    }
  }
  if (els.accountMenuAvatar) {
    if (photo) {
      els.accountMenuAvatar.src = photo;
      els.accountMenuAvatar.classList.remove('hidden');
      if (els.accountMenuInitial) {
        els.accountMenuInitial.classList.add('hidden');
      }
    } else {
      els.accountMenuAvatar.classList.add('hidden');
      if (els.accountMenuInitial) {
        els.accountMenuInitial.classList.remove('hidden');
      }
    }
  }
}

function updateAuthBadges() {
  if (!authState.user) {
    if (els.accountMfaSetupBtn) {
      els.accountMfaSetupBtn.classList.add('hidden');
    }
    if (els.logoutBtn) {
      els.logoutBtn.classList.add('hidden');
    }
    closeAccountDropdown();
    renderAccountMenuProfile();
    return;
  }

  if (els.accountMfaSetupBtn) {
    const canSetupMfa = isPrivilegedMfaRole(authState.user.role) && !Boolean(authState.user.mfa_enabled);
    els.accountMfaSetupBtn.classList.toggle('hidden', !canSetupMfa);
  }
  if (els.logoutBtn) {
    els.logoutBtn.classList.remove('hidden');
  }
  renderAccountMenuProfile();
}

function setChotuOpen(open) {
  if (!els.chotuWidget || !els.chotuPanel || !els.chotuToggleBtn) {
    return;
  }
  const shouldOpen = Boolean(open);
  state.ui.chotuOpen = shouldOpen;
  els.chotuWidget.classList.remove('is-closing');
  els.chotuWidget.classList.toggle('is-open', shouldOpen);
  els.chotuToggleBtn.classList.toggle('is-active', shouldOpen);
  els.chotuToggleBtn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
  if (shouldOpen) {
    window.clearTimeout(setChotuOpen._closeTimer);
    return;
  }
  els.chotuWidget.classList.add('is-closing');
  window.clearTimeout(setChotuOpen._closeTimer);
  setChotuOpen._closeTimer = window.setTimeout(() => {
    els.chotuWidget?.classList.remove('is-closing');
  }, 320);
}

function toggleChotuOpen() {
  setChotuOpen(!state.ui.chotuOpen);
}

function isCompactMobileViewport() {
  return window.matchMedia('(max-width: 900px)').matches;
}

function updateChotuVisibility() {
  if (!els.chotuWidget) {
    return;
  }
  const visible = Boolean(
    authState.user
    && !isCompactMobileViewport()
    && getSanitizedModuleKey(state.ui.activeModule) === 'food'
  );
  setHidden(els.chotuWidget, !visible);
  if (!visible) {
    setChotuOpen(false);
    return;
  }
  void renderFoodAiQuickChips();
}

function setVerlynStatus(message, isError = false, state = 'neutral') {
  if (!els.verlynStatus) {
    return;
  }
  setUiStateMessage(els.verlynStatus, message, {
    state: isError ? 'error' : state,
  });
}

function setVerlynOpen(open) {
  if (!els.verlynSidebarWidget || !els.verlynPanel || !els.verlynToggleBtn) {
    return;
  }
  const shouldOpen = Boolean(open);
  state.ui.verlynOpen = shouldOpen;
  els.verlynSidebarWidget.classList.remove('is-closing');
  els.verlynSidebarWidget.classList.toggle('is-open', shouldOpen);
  els.verlynToggleBtn.classList.toggle('is-active', shouldOpen);
  els.verlynToggleBtn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
  if (shouldOpen) {
    window.clearTimeout(setVerlynOpen._closeTimer);
    return;
  }
  els.verlynSidebarWidget.classList.add('is-closing');
  window.clearTimeout(setVerlynOpen._closeTimer);
  setVerlynOpen._closeTimer = window.setTimeout(() => {
    els.verlynSidebarWidget?.classList.remove('is-closing');
  }, 260);
}

function toggleVerlynOpen() {
  setVerlynOpen(!state.ui.verlynOpen);
}

function updateVerlynVisibility() {
  if (!els.verlynSidebarWidget) {
    return;
  }
  const compactLayout = window.matchMedia('(max-width: 940px)').matches;
  const visible = !compactLayout;
  setHidden(els.verlynSidebarWidget, !visible);
  if (!visible) {
    setVerlynOpen(false);
  }
}

function getVerlynRoleLabel() {
  const role = String(authState.user?.role || '').trim().toLowerCase();
  if (!role) {
    return 'Guest';
  }
  return asTitleCase(role);
}

function getVerlynModuleLabel(moduleKey = getSanitizedModuleKey(state.ui.activeModule)) {
  const normalized = getSanitizedModuleKey(moduleKey);
  return MODULE_LABELS[normalized] || asTitleCase(normalized);
}

function getVerlynAccessibleModuleLabels() {
  const role = authState.user?.role;
  if (!role) {
    return [];
  }
  return Object.keys(MODULE_LABELS)
    .filter((moduleKey) => isModuleAccessible(moduleKey, role))
    .map((moduleKey) => MODULE_LABELS[moduleKey] || asTitleCase(moduleKey));
}

function syncVerlynVisualContext() {
  const moduleKey = getSanitizedModuleKey(state.ui.activeModule);
  const moduleLabel = getVerlynModuleLabel(moduleKey);
  const roleLabel = getVerlynRoleLabel();
  if (els.verlynSidebarWidget) {
    els.verlynSidebarWidget.dataset.module = moduleKey;
  }
  if (els.verlynPanel) {
    els.verlynPanel.dataset.module = moduleKey;
  }
  if (els.verlynScopeChip) {
    els.verlynScopeChip.textContent = moduleLabel;
  }
  if (els.verlynRoleChip) {
    els.verlynRoleChip.textContent = roleLabel;
  }
  if (els.verlynToggleMeta) {
    els.verlynToggleMeta.textContent = authState.user
      ? `${moduleLabel} • ${roleLabel}`
      : 'Sign in for Copilot';
  }
}

function getVerlynSeedRegistration() {
  const candidates = [
    state.rms?.selectedStudent?.registration_number,
    els.adminSearchStudentRegistration?.value,
    els.rmsAttendanceRegistration?.value,
    els.rmsSearchRegistration?.value,
    els.adminGradeStudentRegistration?.value,
  ];
  for (const candidate of candidates) {
    const normalized = normalizedRegistrationInput(candidate || '');
    if (normalized) {
      return normalized;
    }
  }
  return '';
}

function resolveRemedialCourseCodeFromId(courseId) {
  const numericId = Number(courseId || 0);
  if (!numericId) {
    return '';
  }
  const sourceCourses = [
    ...(Array.isArray(state.remedial.eligibleCourses) ? state.remedial.eligibleCourses : []),
    ...Object.values(state.coursesById || {}),
  ];
  const matched = sourceCourses.find((course) => Number(course?.id || 0) === numericId);
  return normalizeRemedialCourseCode(matched?.code || '');
}

function getVerlynRemedialDefaults() {
  const courseId = Number(els.remedialCourseSelect?.value || 0) || null;
  const courseCode = normalizeRemedialCourseCode(
    els.remedialCourseCodeInput?.value || resolveRemedialCourseCodeFromId(courseId)
  );
  const sections = normalizeRemedialSections(els.remedialSectionsInput?.value);
  const classMode = String(els.remedialModeSelect?.value || 'offline').trim().toLowerCase() === 'online'
    ? 'online'
    : 'offline';
  return {
    courseId,
    courseCode,
    section: sections[0] || '',
    classDate: String(els.remedialDate?.value || '').trim(),
    startTime: String(els.remedialStartTime?.value || '').trim(),
    classMode,
    roomNumber: String(els.remedialRoomInput?.value || '').trim(),
    sendMessage: true,
  };
}

function getVerlynPromptExamples() {
  const role = String(authState.user?.role || '').trim().toLowerCase();
  if (role === 'student') {
    return [
      'Summarize my pending tasks across attendance, food, Saarthi, and remedial.',
      "Why can't I mark attendance?",
      'What is pending in my food orders this week?',
    ];
  }
  if (role === 'faculty') {
    return [
      'Show why student 22BCS777 is flagged',
      'Create a remedial plan for course CSE501 section P132 on 2026-03-10 at 15:00',
      'Give me a module-wise summary for attendance, RMS, remedial, and food.',
    ];
  }
  if (role === 'admin') {
    return [
      'Show why student 22BCS777 is flagged',
      'Give me an administrative and RMS summary for today.',
      'Create a remedial plan for course CSE501 section P132 on 2026-03-10 at 15:00',
    ];
  }
  if (role === 'owner') {
    return [
      'Summarize active food orders and delivery flow for my shops today.',
    ];
  }
  return ['Login to use explainable campus actions.'];
}

function getVerlynDefaultOutput() {
  const roleLabel = getVerlynRoleLabel();
  const moduleLabels = getVerlynAccessibleModuleLabels();
  const examples = getVerlynPromptExamples();
  const scope = moduleLabels.length ? moduleLabels.join(', ') : getVerlynModuleLabel();
  const lines = [
    `${roleLabel} Copilot`,
    `Scope: ${scope}`,
    `Try: ${examples[0] || 'Ask for a module summary.'}`,
  ];
  if (examples[1]) {
    lines.push(`Next: ${examples[1]}`);
  }
  return lines.join('\n');
}

function syncVerlynQuickActionFieldState() {
  const modeSelect = document.getElementById('verlyn-remedial-mode');
  const roomInput = document.getElementById('verlyn-remedial-room');
  const roomLabel = roomInput?.closest('.verlyn-quick-field');
  if (!modeSelect || !roomInput || !roomLabel) {
    return;
  }
  const isOnline = String(modeSelect.value || 'offline').trim().toLowerCase() === 'online';
  roomInput.disabled = isOnline;
  roomInput.placeholder = isOnline ? 'Not required for online remedial' : 'e.g. 34-101';
  roomLabel.classList.toggle('is-disabled', isOnline);
}

function renderVerlynQuickActions() {
  if (!els.verlynQuickActions) {
    return;
  }
  const role = String(authState.user?.role || '').trim().toLowerCase();
  const seedRegistration = getVerlynSeedRegistration();
  const remedialDefaults = getVerlynRemedialDefaults();
  let markup = '';

  if (!authState.user) {
    markup = `
      <div class="verlyn-empty-note">
        Sign in to run audited Campus Copilot actions.
      </div>
    `;
  } else if (role === 'student') {
    markup = `
      <section class="verlyn-action-card verlyn-action-card-compact">
        <div class="verlyn-action-head">
          <strong>Quick Actions</strong>
        </div>
        <div class="verlyn-chip-row">
          <button class="btn verlyn-chip-btn" type="button" data-verlyn-action="attendance_blocker">
            Attendance blocker
          </button>
          <button class="btn verlyn-chip-btn" type="button" data-verlyn-action="eligibility_risk">
            Eligibility risk
          </button>
          <button class="btn verlyn-chip-btn" type="button" data-verlyn-action="student_module_summary">
            Module summary
          </button>
        </div>
      </section>
    `;
  } else if (role === 'faculty' || role === 'admin') {
    const auditAction = role === 'admin'
      ? '<button class="btn verlyn-chip-btn" type="button" data-verlyn-action="focus_audit_timeline">Audit Timeline</button>'
      : '';
    markup = `
      <form class="verlyn-action-card verlyn-action-card-inline" data-verlyn-action="flag_reason">
        <div class="verlyn-action-head">
          <strong>Flag Review</strong>
        </div>
        <div class="verlyn-action-inline">
          <input id="verlyn-flag-registration" type="text" value="${escapeHtml(seedRegistration)}" placeholder="Registration no. e.g. 22BCS777">
          <button class="btn btn-primary" type="submit">Explain</button>
          ${auditAction}
        </div>
      </form>
      <details class="verlyn-action-card verlyn-action-disclosure" open>
        <summary>Remedial Planner</summary>
        <form class="verlyn-action-form" data-verlyn-action="create_remedial_plan">
          <div class="verlyn-field-grid">
            <label class="field verlyn-quick-field">
              <span>Course</span>
              <input id="verlyn-remedial-course-code" type="text" value="${escapeHtml(remedialDefaults.courseCode)}" placeholder="e.g. CSE501">
            </label>
            <label class="field verlyn-quick-field">
              <span>Section</span>
              <input id="verlyn-remedial-section" type="text" value="${escapeHtml(remedialDefaults.section)}" placeholder="e.g. P132">
            </label>
            <label class="field verlyn-quick-field">
              <span>Date</span>
              <input id="verlyn-remedial-date" type="date" value="${escapeHtml(remedialDefaults.classDate)}">
            </label>
            <label class="field verlyn-quick-field">
              <span>Time</span>
              <input id="verlyn-remedial-time" type="time" value="${escapeHtml(remedialDefaults.startTime)}">
            </label>
            <label class="field verlyn-quick-field">
              <span>Mode</span>
              <select id="verlyn-remedial-mode">
                <option value="offline"${remedialDefaults.classMode === 'offline' ? ' selected' : ''}>Offline</option>
                <option value="online"${remedialDefaults.classMode === 'online' ? ' selected' : ''}>Online</option>
              </select>
            </label>
            <label class="field verlyn-quick-field">
              <span>Room</span>
              <input id="verlyn-remedial-room" type="text" value="${escapeHtml(remedialDefaults.roomNumber)}" placeholder="e.g. 34-101">
            </label>
          </div>
          <label class="verlyn-inline-check">
            <input id="verlyn-remedial-send-message" type="checkbox" ${remedialDefaults.sendMessage ? 'checked' : ''}>
            Notify section
          </label>
          <div class="verlyn-chip-row">
            <button class="btn btn-primary" type="submit">Schedule</button>
          </div>
        </form>
      </details>
    `;
  } else if (role === 'owner') {
    markup = `
      <section class="verlyn-action-card verlyn-action-card-compact">
        <div class="verlyn-action-head">
          <strong>Quick Actions</strong>
        </div>
        <div class="verlyn-chip-row">
          <button class="btn verlyn-chip-btn" type="button" data-verlyn-action="owner_food_summary">
            Shop order summary
          </button>
        </div>
      </section>
    `;
  } else {
    markup = `
      <div class="verlyn-empty-note">
        Use Ask to run audited, role-scoped module queries.
      </div>
    `;
  }

  els.verlynQuickActions.innerHTML = markup;
  if (els.verlynInput) {
    const firstExample = getVerlynPromptExamples()[0] || 'Ask for a module summary.';
    els.verlynInput.placeholder = `e.g. ${firstExample}`;
  }
  syncVerlynVisualContext();
  syncVerlynQuickActionFieldState();
}

function syncVisibleVerlynQuickActions() {
  if (!state.ui.verlynOpen) {
    return;
  }
  renderVerlynQuickActions();
}

function formatVerlynCopilotResponse(response = {}) {
  const lines = [];
  const title = String(response?.title || 'Campus Copilot').trim();
  const outcome = asTitleCase(String(response?.outcome || 'completed').replaceAll('_', ' '));
  lines.push(`${title} (${outcome})`);

  const explanation = Array.isArray(response?.explanation) ? response.explanation : [];
  if (explanation.length) {
    lines.push('');
    explanation.forEach((item, index) => {
      lines.push(`${index + 1}. ${String(item || '').trim()}`);
    });
  }

  const evidence = Array.isArray(response?.evidence) ? response.evidence : [];
  if (evidence.length) {
    lines.push('', 'Evidence');
    evidence.forEach((item) => {
      const status = String(item?.status || 'info').toUpperCase();
      const label = String(item?.label || 'Item').trim();
      const value = String(item?.value || '').trim();
      lines.push(`- [${status}] ${label}: ${value}`);
    });
  }

  const actions = Array.isArray(response?.actions) ? response.actions : [];
  if (actions.length) {
    lines.push('', 'Actions');
    actions.forEach((item) => {
      const action = String(item?.action || 'action').replaceAll('_', ' ');
      const status = String(item?.status || 'preview').toUpperCase();
      const detail = String(item?.detail || '').trim();
      lines.push(`- [${status}] ${action}${detail ? `: ${detail}` : ''}`);
    });
  }

  const nextSteps = Array.isArray(response?.next_steps) ? response.next_steps : [];
  if (nextSteps.length) {
    lines.push('', 'Next Steps');
    nextSteps.forEach((item, index) => {
      lines.push(`${index + 1}. ${String(item || '').trim()}`);
    });
  }

  if (response?.audit_id) {
    lines.push('', `Audit Log: #${response.audit_id}`);
  }

  return lines.join('\n');
}

function buildVerlynFlagPayload() {
  const registration = normalizedRegistrationInput(document.getElementById('verlyn-flag-registration')?.value || getVerlynSeedRegistration());
  const studentIdRaw = String(document.getElementById('verlyn-flag-student-id')?.value || '').trim();
  const studentId = Number(studentIdRaw || 0) || null;
  if (!registration && !studentId) {
    throw new Error('Enter a registration number or student id for flag review.');
  }
  return {
    query_text: registration
      ? `Show why student ${registration} is flagged`
      : `Show why student id ${studentId} is flagged`,
    registration_number: registration || null,
    student_id: studentId,
  };
}

function buildVerlynRemedialPayload() {
  const defaults = getVerlynRemedialDefaults();
  const courseCode = normalizeRemedialCourseCode(
    document.getElementById('verlyn-remedial-course-code')?.value || defaults.courseCode
  );
  const courseId = courseCode && courseCode !== defaults.courseCode ? null : defaults.courseId;
  const section = normalizeRemedialSections(
    document.getElementById('verlyn-remedial-section')?.value || defaults.section
  )[0] || '';
  const classDate = String(document.getElementById('verlyn-remedial-date')?.value || defaults.classDate || '').trim();
  const startTime = String(document.getElementById('verlyn-remedial-time')?.value || defaults.startTime || '').trim();
  const classMode = String(
    document.getElementById('verlyn-remedial-mode')?.value || defaults.classMode || 'offline'
  ).trim().toLowerCase() === 'online'
    ? 'online'
    : 'offline';
  const roomNumber = String(document.getElementById('verlyn-remedial-room')?.value || defaults.roomNumber || '').trim();
  const sendMessage = Boolean(document.getElementById('verlyn-remedial-send-message')?.checked);
  if (!courseCode && !courseId) {
    throw new Error('Enter a course code or pick a course from the Remedial module.');
  }
  if (!section) {
    throw new Error('Enter the target section.');
  }

  const queryParts = ['Create a remedial plan for'];
  if (courseCode) {
    queryParts.push(`course ${courseCode}`);
  } else {
    queryParts.push(`course id ${courseId}`);
  }
  queryParts.push(`section ${section}`);
  if (classDate) {
    queryParts.push(`on ${classDate}`);
  }
  if (startTime) {
    queryParts.push(`at ${startTime}`);
  }
  if (classMode === 'offline' && roomNumber) {
    queryParts.push(`room ${roomNumber}`);
  }

  return {
    query_text: queryParts.join(' '),
    course_id: courseId,
    course_code: courseCode || null,
    section,
    class_date: classDate || null,
    start_time: startTime || null,
    class_mode: classMode,
    room_number: classMode === 'offline' ? (roomNumber || null) : null,
    send_message: sendMessage,
  };
}

function extractRemedialCodeFromCopilotResponse(response = {}) {
  const entityCode = String(response?.entities?.remedial_code || '').trim().toUpperCase();
  if (entityCode) {
    return entityCode;
  }
  const actionDetail = Array.isArray(response?.actions)
    ? response.actions
      .map((item) => String(item?.detail || '').trim())
      .find((detail) => /[A-Z0-9]{4,16}/.test(detail) && /remedial class/i.test(detail))
    : '';
  const actionCodeMatch = actionDetail.match(/\b([A-Z0-9]{4,16})\b/);
  if (actionCodeMatch) {
    return actionCodeMatch[1];
  }
  return '';
}

function inferRemedialEndTime(startTime = '') {
  const parts = parseTimeStringToParts(startTime);
  if (!parts) {
    return '';
  }
  const totalMinutes = (parts.hour * 60) + parts.minute + 60;
  const nextHour = Math.floor((totalMinutes % (24 * 60)) / 60);
  const nextMinute = totalMinutes % 60;
  return `${String(nextHour).padStart(2, '0')}:${String(nextMinute).padStart(2, '0')}:00`;
}

function resolveVerlynRemedialCourseTitle(payload = {}) {
  const directTitle = normalizeRemedialCourseTitle(els.remedialCourseTitleInput?.value || '');
  if (directTitle) {
    return directTitle;
  }
  const eligibleCourses = Array.isArray(state.remedial.eligibleCourses) ? state.remedial.eligibleCourses : [];
  const normalizedCode = normalizeRemedialCourseCode(payload.course_code || '');
  if (normalizedCode) {
    const matchedEligible = eligibleCourses.find((course) => normalizeRemedialCourseCode(course?.code || '') === normalizedCode);
    if (matchedEligible?.title) {
      return normalizeRemedialCourseTitle(matchedEligible.title);
    }
    const matchedCourse = Object.values(state.coursesById || {}).find(
      (course) => normalizeRemedialCourseCode(course?.code || '') === normalizedCode
    );
    if (matchedCourse?.title) {
      return normalizeRemedialCourseTitle(matchedCourse.title);
    }
  }
  const courseId = Number(payload.course_id || 0);
  if (courseId > 0) {
    return normalizeRemedialCourseTitle(state.coursesById?.[courseId]?.title || '');
  }
  return '';
}

function upsertRemedialClassFromCopilot(payload = {}, response = {}) {
  const nextId = Number(response?.entities?.class_id || response?.audit_id || 0);
  const nextCode = extractRemedialCodeFromCopilotResponse(response);
  const nextSection = normalizeRemedialSections(payload.section || '');
  const nextTitle = resolveVerlynRemedialCourseTitle(payload);
  const nextStartTime = parseTimeStringToParts(payload.start_time)
    ? `${String(payload.start_time).slice(0, 5)}:00`
    : '';
  const optimisticEntry = {
    id: nextId || Date.now(),
    course_id: Number(payload.course_id || 0) || null,
    course_code: normalizeRemedialCourseCode(payload.course_code || ''),
    course_title: nextTitle,
    class_date: String(payload.class_date || '').trim() || null,
    start_time: nextStartTime,
    end_time: inferRemedialEndTime(nextStartTime),
    topic: 'Remedial Session',
    sections: nextSection,
    class_mode: String(payload.class_mode || 'offline').trim().toLowerCase() === 'online' ? 'online' : 'offline',
    room_number: String(payload.room_number || '').trim() || null,
    remedial_code: nextCode || '--',
    is_active: true,
  };
  const matchIndex = (Array.isArray(state.remedial.classes) ? state.remedial.classes : []).findIndex((entry) => (
    (nextId > 0 && Number(entry?.id || 0) === nextId)
    || (nextCode && String(entry?.remedial_code || '').trim().toUpperCase() === nextCode)
  ));
  if (matchIndex >= 0) {
    state.remedial.classes[matchIndex] = {
      ...state.remedial.classes[matchIndex],
      ...optimisticEntry,
    };
  } else {
    state.remedial.classes = [optimisticEntry, ...(Array.isArray(state.remedial.classes) ? state.remedial.classes : [])];
  }
  renderRemedialClassesList();
  renderRemedialClassSelect();
}

function focusAdminCopilotAuditTimeline({ refresh = true } = {}) {
  if (!authState.user || authState.user.role !== 'admin') {
    throw new Error('Only admin can open the copilot audit timeline.');
  }
  if (getSanitizedModuleKey(state.ui.activeModule) !== 'administrative') {
    setActiveModule('administrative');
  }
  window.setTimeout(() => {
    document.getElementById('admin-copilot-audit-card')?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    });
    els.adminCopilotAuditSearch?.focus();
  }, 60);
  if (refresh) {
    void refreshCopilotAuditTimeline({ silent: true });
  }
}

function buildVerlynAttendanceClientContext() {
  const role = String(authState.user?.role || '').trim().toLowerCase();
  if (role === 'student') {
    const aggregate = state.student.attendanceAggregate && typeof state.student.attendanceAggregate === 'object'
      ? state.student.attendanceAggregate
      : null;
    const courses = Array.isArray(aggregate?.courses) ? aggregate.courses : [];
    const selectedScheduleId = Number(state.student.selectedScheduleId || state.student.kpiScheduleId || 0) || null;
    const selectedClass = (Array.isArray(state.student.timetable) ? state.student.timetable : [])
      .find((entry) => Number(entry?.schedule_id || 0) === selectedScheduleId)
      || null;
    return {
      role_view: 'student',
      aggregate_percent: Number(aggregate?.aggregate_percent || 0),
      attended_total: Number(aggregate?.attended_total || 0),
      delivered_total: Number(aggregate?.delivered_total || 0),
      at_risk_course_codes: courses
        .filter((row) => Number(row?.delivered_classes || 0) >= 4 && Number(row?.attendance_percent || 0) < 75)
        .map((row) => String(row?.course_code || '').trim())
        .filter(Boolean),
      watch_course_codes: courses
        .filter((row) => Number(row?.delivered_classes || 0) > 0 && Number(row?.attendance_percent || 0) >= 75 && Number(row?.attendance_percent || 0) < 80)
        .map((row) => String(row?.course_code || '').trim())
        .filter(Boolean),
      selected_schedule_id: selectedScheduleId,
      selected_class: selectedClass
        ? {
          schedule_id: Number(selectedClass.schedule_id || 0),
          course_code: String(selectedClass.course_code || '').trim() || null,
          course_title: String(selectedClass.course_title || '').trim() || null,
          start_time: String(selectedClass.start_time || '').trim() || null,
          end_time: String(selectedClass.end_time || '').trim() || null,
        }
        : null,
      pending_rectifications: Array.isArray(state.student.attendanceRectificationRequests) ? state.student.attendanceRectificationRequests.filter((row) => String(row?.status || '').trim().toLowerCase() === 'pending').length : 0,
      recovery_plan_count: Array.isArray(state.student.recoveryPlans) ? state.student.recoveryPlans.length : 0,
      profile_ready: Boolean(state.student.registrationNumber && state.student.profilePhotoDataUrl && state.student.hasEnrollmentVideo),
      registration_ready: Boolean(state.student.registrationNumber),
      profile_photo_ready: Boolean(state.student.profilePhotoDataUrl),
      enrollment_ready: Boolean(state.student.hasEnrollmentVideo),
    };
  }
  if (role === 'faculty') {
    const selectedScheduleId = Number(state.faculty.selectedScheduleId || 0) || null;
    const selectedSchedule = (Array.isArray(state.faculty.schedules) ? state.faculty.schedules : [])
      .find((entry) => Number(entry?.schedule_id || entry?.id || 0) === selectedScheduleId)
      || null;
    return {
      role_view: 'faculty',
      schedule_count: Array.isArray(state.faculty.schedules) ? state.faculty.schedules.length : 0,
      selected_schedule_id: selectedScheduleId,
      selected_schedule: selectedSchedule
        ? {
          schedule_id: Number(selectedSchedule.schedule_id || selectedSchedule.id || 0),
          course_code: String(selectedSchedule.course_code || '').trim() || null,
          classroom_label: String(selectedSchedule.classroom_label || '').trim() || null,
          class_date: String(selectedSchedule.class_date || '').trim() || null,
        }
        : null,
      pending_rectifications: Array.isArray(state.faculty.rectificationRequests) ? state.faculty.rectificationRequests.filter((row) => String(row?.status || '').trim().toLowerCase() === 'pending').length : 0,
      recovery_plan_count: Array.isArray(state.faculty.recoveryPlans) ? state.faculty.recoveryPlans.length : 0,
    };
  }
  const adminSummary = state.admin.summary && typeof state.admin.summary === 'object' ? state.admin.summary : {};
  return {
    role_view: role || 'admin',
    work_date: String(els.workDate?.value || todayISO()).trim() || todayISO(),
    pending_correction_approvals: Number(adminSummary?.pending_correction_approvals || 0),
    pending_identity_reviews: Number(adminSummary?.pending_identity_reviews || 0),
    alerts_count: Array.isArray(state.admin.alerts) ? state.admin.alerts.length : 0,
  };
}

function buildVerlynSaarthiClientContext() {
  const status = state.student.saarthiStatus && typeof state.student.saarthiStatus === 'object'
    ? state.student.saarthiStatus
    : {};
  const messages = Array.isArray(state.student.saarthiMessages) ? state.student.saarthiMessages : [];
  return {
    session_started: Boolean(messages.length || status?.session_id || status?.week_started),
    message_count: messages.length,
    attendance_credited: Boolean(status?.attendance_credited || status?.attendance_marked_at),
    mandatory_date: String(status?.mandatory_date || '').trim() || null,
    status_message: String(status?.status_message || state.student.saarthiUiMessage || '').trim() || null,
    ui_state: String(state.student.saarthiUiState || 'neutral').trim().toLowerCase(),
  };
}

function buildVerlynRemedialClientContext() {
  const classes = Array.isArray(state.remedial.classes) ? state.remedial.classes : [];
  const selectedClassId = Number(state.remedial.selectedClassId || 0) || null;
  const selectedClass = classes.find((entry) => Number(entry?.id || 0) === selectedClassId)
    || (state.remedial.validatedClass && typeof state.remedial.validatedClass === 'object' ? state.remedial.validatedClass : null);
  return {
    class_count: classes.length,
    message_count: Array.isArray(state.remedial.messages) ? state.remedial.messages.length : 0,
    selected_class_id: selectedClassId,
    selected_class: selectedClass
      ? {
        id: Number(selectedClass.id || 0) || null,
        course_code: String(selectedClass.course_code || '').trim() || null,
        course_title: String(selectedClass.course_title || '').trim() || null,
        class_date: String(selectedClass.class_date || '').trim() || null,
        start_time: String(selectedClass.start_time || '').trim() || null,
        remedial_code: String(selectedClass.remedial_code || '').trim() || null,
      }
      : null,
    validated_class_id: Number(state.remedial.validatedClass?.id || 0) || null,
    demo_bypass_lead_time: Boolean(state.remedial.demoBypassLeadTime),
  };
}

function buildVerlynRmsClientContext() {
  const dashboard = state.rms.dashboard && typeof state.rms.dashboard === 'object' ? state.rms.dashboard : {};
  const selectedStudent = state.rms.selectedStudent && typeof state.rms.selectedStudent === 'object'
    ? state.rms.selectedStudent
    : (state.rms.attendanceContext?.student && typeof state.rms.attendanceContext.student === 'object' ? state.rms.attendanceContext.student : null);
  const selectedThread = state.rms.selectedThread && typeof state.rms.selectedThread === 'object'
    ? state.rms.selectedThread
    : null;
  const selectedSubject = resolveRmsAttendanceSelectedSubject();
  const selectedSlot = resolveRmsAttendanceSelectedSlot();
  return {
    filters: {
      category: String(state.rms.selectedCategory || '').trim() || 'all',
      status: String(state.rms.selectedStatus || '').trim() || 'all',
      thread_action: String(state.rms.threadAction || '').trim() || 'approve',
    },
    total_threads: Number(dashboard?.total_threads || 0),
    total_pending: Number(dashboard?.total_pending || 0),
    selected_student: selectedStudent
      ? {
        student_id: Number(selectedStudent.student_id || 0) || null,
        name: String(selectedStudent.name || '').trim() || null,
        registration_number: String(selectedStudent.registration_number || '').trim() || null,
        section: String(selectedStudent.section || '').trim() || null,
      }
      : null,
    selected_thread: selectedThread
      ? {
        category: String(selectedThread.category || '').trim() || null,
        subject: String(selectedThread.subject || '').trim() || null,
        pending_action: Boolean(selectedThread.pending_action),
        action_state: String(selectedThread.action_state || '').trim() || null,
      }
      : null,
    attendance_context: state.rms.attendanceContext
      ? {
        attendance_date: String(state.rms.attendanceContext.attendance_date || '').trim() || null,
        subject_count: Array.isArray(state.rms.attendanceContext.subjects) ? state.rms.attendanceContext.subjects.length : 0,
        selected_course_code: String(selectedSubject?.course_code || state.rms.attendanceSelectedCourseCode || '').trim() || null,
        selected_schedule_id: Number(selectedSlot?.schedule_id || state.rms.attendanceSelectedScheduleId || 0) || null,
        selected_slot_status: String(selectedSlot?.current_status_label || selectedSubject?.current_status_label || '').trim() || null,
      }
      : null,
  };
}

function buildVerlynAdministrativeClientContext() {
  const summary = state.admin.summary && typeof state.admin.summary === 'object' ? state.admin.summary : {};
  return {
    work_date: String(els.workDate?.value || todayISO()).trim() || todayISO(),
    alerts_count: Array.isArray(state.admin.alerts) ? state.admin.alerts.length : 0,
    identity_case_count: Array.isArray(state.admin.identityCases) ? state.admin.identityCases.length : 0,
    recovery_plan_count: Array.isArray(state.admin.recoveryPlans) ? state.admin.recoveryPlans.length : 0,
    copilot_runs_today: Number(summary?.copilot_runs_today || 0),
    pending_correction_approvals: Number(summary?.pending_correction_approvals || 0),
    pending_identity_reviews: Number(summary?.pending_identity_reviews || 0),
    flagged_identity_cases: Number(summary?.flagged_identity_cases || 0),
  };
}

function buildVerlynActiveModuleSummary(activeModule, moduleContext = {}) {
  const lines = [];
  const role = String(authState.user?.role || '').trim().toLowerCase();
  if (activeModule === 'attendance') {
    if (role === 'student') {
      if (Number.isFinite(Number(moduleContext.aggregate_percent))) {
        lines.push(`Attendance aggregate ${Number(moduleContext.aggregate_percent || 0).toFixed(2)}% across ${Number(moduleContext.delivered_total || 0)} delivered classes.`);
      }
      if (moduleContext.selected_class?.course_code) {
        lines.push(`Selected class ${String(moduleContext.selected_class.course_code)} schedule ${Number(moduleContext.selected_schedule_id || 0)} ${String(moduleContext.selected_class.start_time || '--')}-${String(moduleContext.selected_class.end_time || '--')}.`);
      }
      if (Number(moduleContext.pending_rectifications || 0) > 0) {
        lines.push(`${Number(moduleContext.pending_rectifications || 0)} attendance rectification request(s) are pending.`);
      }
      if (!moduleContext.profile_ready) {
        lines.push('Attendance profile prerequisites are incomplete on the current student account.');
      }
    } else if (role === 'faculty') {
      lines.push(`${Number(moduleContext.schedule_count || 0)} attendance schedule(s) are loaded in faculty view.`);
      if (Number(moduleContext.pending_rectifications || 0) > 0) {
        lines.push(`${Number(moduleContext.pending_rectifications || 0)} rectification request(s) are pending review.`);
      }
    } else {
      lines.push(`Admin attendance view is loaded for ${String(moduleContext.work_date || todayISO())}.`);
      if (Number(moduleContext.pending_correction_approvals || 0) > 0) {
        lines.push(`${Number(moduleContext.pending_correction_approvals || 0)} correction approval(s) are pending.`);
      }
    }
  } else if (activeModule === 'food') {
    if (moduleContext.order_gate?.reason) {
      lines.push(`Food Hall gate: ${String(moduleContext.order_gate.reason).replaceAll('_', ' ')}.`);
    }
    if (moduleContext.slot?.selected && moduleContext.slot?.label) {
      lines.push(`Selected food slot: ${String(moduleContext.slot.label)}.`);
    }
    lines.push(`Cart has ${Number(moduleContext.cart?.item_count || 0)} item(s) and ${Number(moduleContext.cart?.total_quantity || 0)} total quantity.`);
    if (moduleContext.location?.message) {
      lines.push(`Location status: ${String(moduleContext.location.message)}.`);
    }
  } else if (activeModule === 'saarthi') {
    lines.push(`Saarthi messages this week: ${Number(moduleContext.message_count || 0)}.`);
    if (moduleContext.status_message) {
      lines.push(String(moduleContext.status_message));
    }
  } else if (activeModule === 'remedial') {
    lines.push(`Remedial classes loaded: ${Number(moduleContext.class_count || 0)}.`);
    if (moduleContext.selected_class?.course_code) {
      lines.push(`Selected remedial class ${String(moduleContext.selected_class.course_code)} on ${String(moduleContext.selected_class.class_date || '--')}.`);
    }
  } else if (activeModule === 'rms') {
    lines.push(`RMS dashboard shows ${Number(moduleContext.total_threads || 0)} thread(s) and ${Number(moduleContext.total_pending || 0)} pending.`);
    if (moduleContext.selected_student?.registration_number) {
      lines.push(`Selected RMS student ${String(moduleContext.selected_student.registration_number)} (${String(moduleContext.selected_student.name || 'student')}).`);
    }
    if (moduleContext.selected_thread?.subject) {
      lines.push(`Selected RMS thread subject: ${String(moduleContext.selected_thread.subject)}.`);
    }
  } else if (activeModule === 'administrative') {
    lines.push(`Administrative live view is loaded for ${String(moduleContext.work_date || todayISO())}.`);
    if (Number(moduleContext.pending_identity_reviews || 0) > 0) {
      lines.push(`${Number(moduleContext.pending_identity_reviews || 0)} identity review(s) are pending.`);
    }
    if (Number(moduleContext.recovery_plan_count || 0) > 0) {
      lines.push(`${Number(moduleContext.recovery_plan_count || 0)} recovery plan(s) are visible.`);
    }
  }
  return lines.filter((line) => String(line || '').trim());
}

function buildVerlynFoodClientContext() {
  const orderDate = resolveFoodOrderDateValue();
  const selectedSlot = getSelectedFoodSlot();
  const orderGate = getFoodRuntimeOrderGate({ slot: selectedSlot, orderDate });
  const cartItems = Array.isArray(state.food.cart.items) ? state.food.cart.items : [];
  const totalQuantity = cartItems.reduce((sum, item) => sum + Number(item?.quantity || 0), 0);
  const cartShopId = String(state.food.cart.shopId || '').trim();
  const cartShop = getShopById(cartShopId);
  const deliveryPoint = String(state.food.checkoutDeliveryPoint || els.foodDeliveryBlockSelect?.value || '').trim();
  return {
    demo_enabled: isFoodDemoEnabled(),
    order_date: orderDate,
    order_gate: {
      can_order_now: Boolean(orderGate.canOrderNow),
      can_browse_shops: Boolean(orderGate.canBrowseShops),
      reason: String(orderGate.reason || '').trim(),
      message: String(orderGate.message || '').trim(),
      service_open_now: Boolean(orderGate.serviceOpenNow),
      date_allowed: Boolean(orderGate.dateAllowed),
      slot_elapsed: Boolean(orderGate.slotElapsed),
    },
    slot: {
      selected: Boolean(selectedSlot),
      slot_id: selectedSlot ? Number(selectedSlot.id) : null,
      label: String(selectedSlot?.label || '').trim(),
      start_time: String(selectedSlot?.start_time || '').trim() || null,
      end_time: String(selectedSlot?.end_time || '').trim() || null,
    },
    cart: {
      item_count: cartItems.length,
      total_quantity: totalQuantity,
      shop_id: cartShopId ? Number(cartShopId) : null,
      shop_name: String(cartShop?.name || '').trim() || null,
    },
    checkout: {
      review_open: Boolean(state.food.checkoutPreviewOpen),
      delivery_point_selected: Boolean(deliveryPoint),
      delivery_point: deliveryPoint || null,
    },
    location: {
      verified: Boolean(state.food.location.verified),
      allowed: Boolean(state.food.location.allowed),
      fresh: Boolean(isFoodLocationFresh()),
      checking: Boolean(state.food.location.checking),
      message: String(state.food.location.message || '').trim() || null,
    },
    shops: {
      active_count: Array.isArray(state.food.shops) ? state.food.shops.length : 0,
    },
  };
}

function buildVerlynRuntimePayload(payload = {}) {
  const basePayload = (payload && typeof payload === 'object' && !Array.isArray(payload)) ? payload : {};
  const activeModule = getSanitizedModuleKey(state.ui.activeModule);
  const nextClientContext = (
    basePayload.client_context
    && typeof basePayload.client_context === 'object'
    && !Array.isArray(basePayload.client_context)
  )
    ? { ...basePayload.client_context }
    : {};
  const moduleContextBuilders = {
    attendance: buildVerlynAttendanceClientContext,
    food: buildVerlynFoodClientContext,
    saarthi: buildVerlynSaarthiClientContext,
    remedial: buildVerlynRemedialClientContext,
    rms: buildVerlynRmsClientContext,
    administrative: buildVerlynAdministrativeClientContext,
  };
  const moduleBuilder = moduleContextBuilders[activeModule];
  const activeModuleContext = typeof moduleBuilder === 'function' ? moduleBuilder() : {};
  if (activeModule && activeModuleContext && typeof activeModuleContext === 'object' && !Array.isArray(activeModuleContext)) {
    nextClientContext[activeModule] = {
      ...((nextClientContext[activeModule] && typeof nextClientContext[activeModule] === 'object' && !Array.isArray(nextClientContext[activeModule]))
        ? nextClientContext[activeModule]
        : {}),
      ...activeModuleContext,
    };
  }
  nextClientContext.ui = {
    ...((nextClientContext.ui && typeof nextClientContext.ui === 'object' && !Array.isArray(nextClientContext.ui))
      ? nextClientContext.ui
      : {}),
    active_module: activeModule || null,
    active_module_label: activeModule ? getVerlynModuleLabel(activeModule) : null,
    screen_summary: buildVerlynActiveModuleSummary(activeModule, activeModuleContext),
  };
  return {
    ...basePayload,
    active_module: activeModule || null,
    client_context: nextClientContext,
  };
}

async function runVerlynCopilot(payload, { syncInput = true } = {}) {
  if (!els.verlynOutput) {
    return null;
  }
  // Copilot should work for any authenticated session, including cookie-backed sessions
  // where a bearer token may be intentionally absent on the client.
  if (!authState.user) {
    setVerlynStatus('Login is required to run campus copilot actions.', true, 'error');
    els.verlynOutput.textContent = getVerlynDefaultOutput();
    return null;
  }
  const requestPayload = buildVerlynRuntimePayload(payload);
  const queryText = String(requestPayload?.query_text || '').trim();
  if (!queryText) {
    setVerlynStatus('Type your question first.', true, 'empty');
    els.verlynOutput.textContent = getVerlynDefaultOutput();
    return null;
  }
  if (syncInput && els.verlynInput) {
    els.verlynInput.value = queryText;
  }
  setVerlynStatus('Running...', false, 'loading');
  try {
    const response = await api('/copilot/query', {
      method: 'POST',
      body: JSON.stringify(requestPayload),
    });
    els.verlynOutput.textContent = formatVerlynCopilotResponse(response);
    const outcome = String(response?.outcome || '').trim().toLowerCase();
    if (outcome === 'completed') {
      setVerlynStatus('Done. Logged.', false, 'success');
    } else if (outcome === 'blocked') {
      const hasExplanation = Array.isArray(response?.explanation) && response.explanation.length > 0;
      setVerlynStatus(
        hasExplanation ? 'Blocked by current campus checks.' : 'Need a bit more context.',
        hasExplanation,
        hasExplanation ? 'error' : 'neutral',
      );
    } else if (outcome === 'denied') {
      setVerlynStatus('Denied by role guardrails.', true, 'error');
    } else {
      setVerlynStatus('Could not complete the request.', true, 'error');
    }
    if (
      outcome === 'completed'
      && String(response?.intent || '').trim().toLowerCase() === 'create_remedial_plan'
      && getSanitizedModuleKey(state.ui.activeModule) === 'remedial'
    ) {
      upsertRemedialClassFromCopilot(requestPayload, response);
      try {
        await refreshRemedialModule();
      } catch (refreshError) {
        log(refreshError?.message || 'Remedial module refresh failed after copilot scheduling');
      }
      syncVisibleVerlynQuickActions();
    }
    if (authState.user?.role === 'admin' && getSanitizedModuleKey(state.ui.activeModule) === 'administrative') {
      void refreshCopilotAuditTimeline({ silent: true, force: true });
    }
    return response;
  } catch (error) {
    setVerlynStatus(
      error?.message || 'Campus copilot is unavailable right now. Retry in a moment.',
      true,
      'error',
    );
    return null;
  }
}

async function askVerlyn() {
  const queryText = String(els.verlynInput?.value || '').trim();
  if (!queryText) {
    setVerlynStatus('Type your question first.', true, 'empty');
    els.verlynOutput.textContent = getVerlynDefaultOutput();
    return;
  }
  await runVerlynCopilot({ query_text: queryText }, { syncInput: false });
}

function normalizeSupportDeskCategory(value = '') {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'attendance') {
    return 'Attendance';
  }
  if (normalized === 'academics') {
    return 'Academics';
  }
  if (normalized === 'discrepancy') {
    return 'Discrepancy';
  }
  return 'Other';
}

function formatSupportDeskDateTime(rawValue) {
  const parsed = new Date(rawValue);
  if (Number.isNaN(parsed.getTime())) {
    return '--';
  }
  return parsed.toLocaleString([], {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function setSupportDeskStatus(message, isError = false, state = 'neutral') {
  if (!els.supportDeskStatus) {
    return;
  }
  setUiStateMessage(els.supportDeskStatus, message, {
    state: isError ? 'error' : state,
  });
}

function setSupportDeskOpen(open) {
  if (!els.supportDeskWidget || !els.supportDeskPanel || !els.supportDeskToggleBtn) {
    return;
  }
  const shouldOpen = Boolean(open);
  state.ui.supportDeskOpen = shouldOpen;
  els.supportDeskWidget.classList.remove('is-closing');
  els.supportDeskWidget.classList.toggle('is-open', shouldOpen);
  els.supportDeskToggleBtn.classList.toggle('is-active', shouldOpen);
  els.supportDeskToggleBtn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
  if (shouldOpen) {
    window.clearTimeout(setSupportDeskOpen._closeTimer);
    return;
  }
  els.supportDeskWidget.classList.add('is-closing');
  window.clearTimeout(setSupportDeskOpen._closeTimer);
  setSupportDeskOpen._closeTimer = window.setTimeout(() => {
    els.supportDeskWidget?.classList.remove('is-closing');
  }, 320);
}

function toggleSupportDeskOpen() {
  setSupportDeskOpen(!state.ui.supportDeskOpen);
}

function updateSupportDeskVisibility() {
  if (!els.supportDeskWidget) {
    return;
  }
  const role = authState.user?.role;
  const visible = Boolean(
    !isCompactMobileViewport()
    && (
    (role === 'student' || role === 'faculty')
    && getSanitizedModuleKey(state.ui.activeModule) === 'attendance'
    )
  );
  setHidden(els.supportDeskWidget, !visible);
  if (!visible) {
    setSupportDeskOpen(false);
    return;
  }
  if (!state.supportDesk.contacts.length && !state.supportDesk.threads.length) {
    void refreshSupportDeskContext({ silent: true, refreshThread: false }).catch(() => {});
  } else {
    renderSupportDeskWidget();
  }
}

function recomputeSupportDeskUnread() {
  const threads = Array.isArray(state.supportDesk.threads) ? state.supportDesk.threads : [];
  state.supportDesk.unreadTotal = threads.reduce(
    (sum, item) => sum + Math.max(0, Number(item?.unread_count || 0)),
    0,
  );
}

function ensureSupportDeskSelection() {
  const currentId = Number(state.supportDesk.selectedCounterpartyId || 0);
  const currentCategory = normalizeSupportDeskCategory(state.supportDesk.selectedCategory);
  const threads = Array.isArray(state.supportDesk.threads) ? state.supportDesk.threads : [];
  const contacts = Array.isArray(state.supportDesk.contacts) ? state.supportDesk.contacts : [];
  const validContactIds = new Set(contacts.map((entry) => Number(entry?.id || 0)).filter((id) => id > 0));
  if (currentId > 0 && validContactIds.has(currentId)) {
    state.supportDesk.selectedCounterpartyId = currentId;
    state.supportDesk.selectedCategory = currentCategory;
    return;
  }
  const firstThread = threads[0];
  if (firstThread && Number(firstThread.counterparty_id || 0) > 0) {
    state.supportDesk.selectedCounterpartyId = Number(firstThread.counterparty_id);
    state.supportDesk.selectedCategory = normalizeSupportDeskCategory(firstThread.category);
    state.supportDesk.selectedCounterpartyName = String(firstThread.counterparty_name || '').trim();
    state.supportDesk.selectedCounterpartySection = String(firstThread.section || '').trim();
    return;
  }
  const firstContact = contacts[0];
  if (firstContact && Number(firstContact.id || 0) > 0) {
    state.supportDesk.selectedCounterpartyId = Number(firstContact.id);
    state.supportDesk.selectedCategory = 'Attendance';
    state.supportDesk.selectedCounterpartyName = String(firstContact.name || '').trim();
    state.supportDesk.selectedCounterpartySection = String(firstContact.section || '').trim();
    return;
  }
  state.supportDesk.selectedCounterpartyId = null;
  state.supportDesk.selectedCounterpartyName = '';
  state.supportDesk.selectedCounterpartySection = '';
}

function renderSupportDeskRecipientOptions() {
  if (!els.supportDeskRecipientSelect) {
    return;
  }
  const contacts = Array.isArray(state.supportDesk.contacts) ? state.supportDesk.contacts : [];
  const selectedId = Number(state.supportDesk.selectedCounterpartyId || 0);
  const role = authState.user?.role;
  if (els.supportDeskRecipientLabel) {
    els.supportDeskRecipientLabel.textContent = role === 'faculty' ? 'Student' : 'Faculty';
  }

  if (!contacts.length) {
    els.supportDeskRecipientSelect.innerHTML = '<option value="">No contacts available</option>';
    els.supportDeskRecipientSelect.disabled = true;
    return;
  }
  const options = contacts
    .map((item) => {
      const id = Number(item?.id || 0);
      if (!id) {
        return '';
      }
      const section = String(item?.section || '').trim();
      const descriptor = String(item?.descriptor || '').trim();
      const extra = descriptor || section;
      const label = extra ? `${item.name} • ${extra}` : item.name;
      const selected = id === selectedId ? 'selected' : '';
      return `<option value="${id}" ${selected}>${escapeHtml(label)}</option>`;
    })
    .filter(Boolean)
    .join('');
  els.supportDeskRecipientSelect.innerHTML = options;
  els.supportDeskRecipientSelect.disabled = false;
}

function renderSupportDeskMessages() {
  if (!els.supportDeskMessages) {
    return;
  }
  const rows = Array.isArray(state.supportDesk.messages) ? state.supportDesk.messages : [];
  if (!rows.length) {
    els.supportDeskMessages.innerHTML = '<div class="support-desk-empty">No messages yet. Start with a query below.</div>';
    return;
  }
  const role = String(authState.user?.role || '').trim().toLowerCase();
  els.supportDeskMessages.innerHTML = rows.map((row) => {
    const senderRole = String(row?.sender_role || '').trim().toLowerCase();
    const mine = senderRole === role;
    const senderLabel = mine ? 'You' : (senderRole === 'faculty' ? 'Faculty' : 'Student');
    return `
      <article class="support-desk-message ${mine ? 'mine' : 'theirs'}">
        <div class="support-desk-message-header">
          <strong>${escapeHtml(senderLabel)}</strong>
          <span>${escapeHtml(formatSupportDeskDateTime(row?.created_at))}</span>
        </div>
        <p class="support-desk-message-text">${escapeHtml(String(row?.message || ''))}</p>
      </article>
    `;
  }).join('');
  els.supportDeskMessages.scrollTop = els.supportDeskMessages.scrollHeight;
}

function renderSupportDeskWidget() {
  const unread = Math.max(0, Number(state.supportDesk.unreadTotal || 0));
  if (els.supportDeskUnreadBadge) {
    if (unread > 0) {
      els.supportDeskUnreadBadge.textContent = unread > 99 ? '99+' : String(unread);
      els.supportDeskUnreadBadge.classList.remove('hidden');
    } else {
      els.supportDeskUnreadBadge.classList.add('hidden');
    }
  }
  renderSupportDeskRecipientOptions();

  if (els.supportDeskCategorySelect) {
    const categories = Array.isArray(state.supportDesk.categories) && state.supportDesk.categories.length
      ? state.supportDesk.categories
      : ['Attendance', 'Academics', 'Discrepancy', 'Other'];
    if (!els.supportDeskCategorySelect.dataset.ready) {
      els.supportDeskCategorySelect.innerHTML = categories
        .map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`)
        .join('');
      els.supportDeskCategorySelect.dataset.ready = 'true';
    }
    els.supportDeskCategorySelect.value = normalizeSupportDeskCategory(state.supportDesk.selectedCategory);
  }

  const selectedId = Number(state.supportDesk.selectedCounterpartyId || 0);
  const selectedCategory = normalizeSupportDeskCategory(state.supportDesk.selectedCategory);
  const selectedThread = (Array.isArray(state.supportDesk.threads) ? state.supportDesk.threads : []).find((item) => (
    Number(item?.counterparty_id || 0) === selectedId
    && normalizeSupportDeskCategory(item?.category) === selectedCategory
  ));
  const selectedContact = (Array.isArray(state.supportDesk.contacts) ? state.supportDesk.contacts : []).find(
    (item) => Number(item?.id || 0) === selectedId
  );
  if (els.supportDeskThreadMeta) {
    if (selectedThread) {
      const unreadLabel = Number(selectedThread.unread_count || 0) > 0
        ? `${selectedThread.unread_count} unread`
        : 'up to date';
      const section = selectedThread.section ? ` • ${selectedThread.section}` : '';
      els.supportDeskThreadMeta.textContent =
        `${selectedThread.counterparty_name}${section} • ${selectedCategory} • ${unreadLabel}`;
    } else if (selectedContact) {
      els.supportDeskThreadMeta.textContent =
        `${selectedContact.name} • ${selectedCategory} • Start a new conversation`;
    } else {
      els.supportDeskThreadMeta.textContent = 'Choose a recipient to start realtime messaging.';
    }
  }
  renderSupportDeskMessages();
}

async function refreshSupportDeskThread({ silent = false } = {}) {
  const role = authState.user?.role;
  if (role !== 'student' && role !== 'faculty') {
    state.supportDesk.messages = [];
    renderSupportDeskWidget();
    return;
  }
  const counterpartyId = Number(state.supportDesk.selectedCounterpartyId || 0);
  const category = normalizeSupportDeskCategory(state.supportDesk.selectedCategory);
  if (!counterpartyId) {
    state.supportDesk.messages = [];
    renderSupportDeskWidget();
    return;
  }
  const rows = await api(
    `/messages/support/thread?counterparty_id=${counterpartyId}&category=${encodeURIComponent(category)}&limit=160`,
  );
  state.supportDesk.messages = Array.isArray(rows) ? rows : [];
  const thread = (Array.isArray(state.supportDesk.threads) ? state.supportDesk.threads : []).find(
    (item) => Number(item?.counterparty_id || 0) === counterpartyId
      && normalizeSupportDeskCategory(item?.category) === category
  );
  if (thread) {
    thread.unread_count = 0;
    const latest = state.supportDesk.messages[state.supportDesk.messages.length - 1];
    if (latest) {
      thread.last_message = String(latest.message || thread.last_message || '');
      thread.last_sender_role = String(latest.sender_role || thread.last_sender_role || '');
      thread.last_created_at = latest.created_at || thread.last_created_at;
    }
  }
  recomputeSupportDeskUnread();
  renderSupportDeskWidget();
  if (!silent && state.ui.supportDeskOpen) {
    setSupportDeskStatus('Messages synced in realtime.');
  }
}

async function refreshSupportDeskContext({ silent = false, refreshThread = false } = {}) {
  const role = authState.user?.role;
  if (role !== 'student' && role !== 'faculty') {
    state.supportDesk.contacts = [];
    state.supportDesk.threads = [];
    state.supportDesk.messages = [];
    state.supportDesk.unreadTotal = 0;
    renderSupportDeskWidget();
    return;
  }
  const payload = await api('/messages/support/context?limit=180');
  state.supportDesk.categories = Array.isArray(payload?.categories) && payload.categories.length
    ? payload.categories.map((value) => normalizeSupportDeskCategory(value))
    : ['Attendance', 'Academics', 'Discrepancy', 'Other'];
  state.supportDesk.contacts = Array.isArray(payload?.contacts) ? payload.contacts : [];
  state.supportDesk.threads = Array.isArray(payload?.threads) ? payload.threads : [];
  state.supportDesk.unreadTotal = Math.max(0, Number(payload?.unread_total || 0));
  ensureSupportDeskSelection();
  renderSupportDeskWidget();
  if (refreshThread) {
    await refreshSupportDeskThread({ silent: true });
  }
  if (!silent && state.ui.supportDeskOpen) {
    setSupportDeskStatus('Realtime inbox refreshed.');
  }
}

async function sendSupportDeskMessage() {
  const role = authState.user?.role;
  if (role !== 'student' && role !== 'faculty') {
    return;
  }
  const recipientId = Number(state.supportDesk.selectedCounterpartyId || els.supportDeskRecipientSelect?.value || 0);
  if (!recipientId) {
    throw new Error('Select a recipient first.');
  }
  const category = normalizeSupportDeskCategory(
    els.supportDeskCategorySelect?.value || state.supportDesk.selectedCategory
  );
  const message = String(els.supportDeskComposeInput?.value || '').trim();
  if (!message) {
    throw new Error('Type your query before sending.');
  }
  if (els.supportDeskSendBtn) {
    els.supportDeskSendBtn.disabled = true;
  }
  try {
    await api('/messages/support/send', {
      method: 'POST',
      body: JSON.stringify({
        recipient_id: recipientId,
        category,
        message,
      }),
    });
    if (els.supportDeskComposeInput) {
      els.supportDeskComposeInput.value = '';
    }
    state.supportDesk.selectedCounterpartyId = recipientId;
    state.supportDesk.selectedCategory = category;
    await refreshSupportDeskContext({ silent: true, refreshThread: false });
    await refreshSupportDeskThread({ silent: true });
    setSupportDeskStatus('Message sent. Waiting for realtime response...');
  } finally {
    if (els.supportDeskSendBtn) {
      els.supportDeskSendBtn.disabled = false;
    }
  }
}

function canRunSupportDeskLiveTicker() {
  const role = authState.user?.role;
  if (role !== 'student' && role !== 'faculty') {
    return false;
  }
  if (document.body.classList.contains('auth-open')) {
    return false;
  }
  if (els.supportDeskWidget?.classList.contains('hidden')) {
    return false;
  }
  return true;
}

function stopSupportDeskLiveTicker() {
  if (!supportDeskLiveTimer) {
    return;
  }
  window.clearInterval(supportDeskLiveTimer);
  supportDeskLiveTimer = null;
  supportDeskLiveBusy = false;
}

function startSupportDeskLiveTicker() {
  // Support-desk realtime is event-driven via SSE route modules.
  stopSupportDeskLiveTicker();
}

function syncSupportDeskLiveTicker() {
  stopSupportDeskLiveTicker();
}

function setHidden(element, hidden) {
  if (!element) {
    return;
  }
  element.classList.toggle('hidden', hidden);
  if (isModalFocusTarget(element)) {
    syncModalFocusTrap(element);
  }
}

function buildDefaultFoodSlotFallback() {
  return Array.from({ length: 11 }, (_, index) => {
    const startHour = 10 + index;
    const endHour = startHour + 1;
    return {
      id: index + 1,
      label: `${String(startHour).padStart(2, '0')}:00 - ${String(endHour).padStart(2, '0')}:00`,
      start_time: `${String(startHour).padStart(2, '0')}:00:00`,
      end_time: `${String(endHour).padStart(2, '0')}:00:00`,
      max_orders: 250,
    };
  });
}

if (!FOOD_SLOT_FALLBACK.length) {
  FOOD_SLOT_FALLBACK = buildDefaultFoodSlotFallback();
}

let FOOD_SHOP_COVER_BY_ALIAS = new Map();
let FOOD_SHOP_COVER_BY_NAME = new Map();
let FOOD_SHOP_FALLBACK_BY_ALIAS = new Map();
let FOOD_SHOP_FALLBACK_BY_NAME = new Map();

function rebuildFoodCoverIndexes() {
  FOOD_SHOP_COVER_BY_ALIAS = new Map(
    FOOD_SHOP_DIRECTORY.map((shop) => [shopAliasKey(shop.name, shop.block), shop.cover || ''])
  );
  FOOD_SHOP_COVER_BY_NAME = new Map(
    FOOD_SHOP_DIRECTORY.map((shop) => [normalizeFoodKey(shop.name), shop.cover || ''])
  );
  FOOD_SHOP_FALLBACK_BY_ALIAS = new Map(
    FOOD_SHOP_DIRECTORY.map((shop) => [shopAliasKey(shop.name, shop.block), shop.fallbackCover || FOOD_COVER_FALLBACK_URL || ''])
  );
  FOOD_SHOP_FALLBACK_BY_NAME = new Map(
    FOOD_SHOP_DIRECTORY.map((shop) => [normalizeFoodKey(shop.name), shop.fallbackCover || FOOD_COVER_FALLBACK_URL || ''])
  );
}

function applyFoodCatalogPayload(payload = {}) {
  const catalog = payload && typeof payload === 'object' ? payload : {};

  FOOD_POPULAR_SPOT_IDS = Array.isArray(catalog.popularSpotIds) && catalog.popularSpotIds.length
    ? [...catalog.popularSpotIds]
    : FOOD_POPULAR_SPOT_IDS;

  FOOD_SHOP_GROUPS = Array.isArray(catalog.shopGroups) && catalog.shopGroups.length
    ? [...catalog.shopGroups]
    : FOOD_SHOP_GROUPS;

  FOOD_SLOT_FALLBACK = Array.isArray(catalog.slotFallback) && catalog.slotFallback.length
    ? catalog.slotFallback.map((slot) => ({ ...slot }))
    : buildDefaultFoodSlotFallback();

  FOOD_AI_QUICK_CRAVINGS = Array.isArray(catalog.aiQuickCravings) && catalog.aiQuickCravings.length
    ? [...catalog.aiQuickCravings]
    : FOOD_AI_QUICK_CRAVINGS;

  FOOD_DELIVERY_POINTS = Array.isArray(catalog.deliveryPoints)
    ? catalog.deliveryPoints.map((row) => [String(row?.[0] || ''), String(row?.[1] || '')])
    : FOOD_DELIVERY_POINTS;

  FOOD_SHOP_DIRECTORY = Array.isArray(catalog.shopDirectory)
    ? catalog.shopDirectory.map((shop) => ({ ...shop }))
    : FOOD_SHOP_DIRECTORY;

  FOOD_COVER_FALLBACK_URL = String(catalog.fallbackCoverUrl || FOOD_COVER_FALLBACK_URL || '').trim()
    || '/web/assets/food-covers/fallback.svg';

  rebuildFoodCoverIndexes();
  foodCatalogReady = true;
}

async function ensureFoodCatalogLoaded({ preloadOnly = false } = {}) {
  if (foodCatalogReady) {
    return;
  }
  if (foodCatalogModulePromise) {
    await foodCatalogModulePromise;
    return;
  }
  foodCatalogModulePromise = import(`/web/modules/food-catalog.js?v=${ROUTE_SPLIT_ASSET_VERSION}`)
    .then((module) => {
      applyFoodCatalogPayload(module?.foodCatalog || {});
      if (!preloadOnly && getSanitizedModuleKey(state.ui.activeModule) === 'food') {
        void renderFoodAiQuickChips();
      }
    })
    .catch((error) => {
      if (!foodCatalogReady) {
        applyFoodCatalogPayload({});
      }
      if (!preloadOnly) {
        log(`Food catalog fallback active: ${error?.message || 'deferred bundle unavailable'}`);
      }
    })
    .finally(() => {
      foodCatalogModulePromise = null;
    });
  await foodCatalogModulePromise;
}

async function ensureVerlynHelpModule() {
  if (verlynHelpModulePromise) {
    return verlynHelpModulePromise;
  }
  verlynHelpModulePromise = import(`/web/modules/verlyn-help.js?v=${ROUTE_SPLIT_ASSET_VERSION}`)
    .catch((error) => {
      verlynHelpModulePromise = null;
      throw error;
  });
  return verlynHelpModulePromise;
}

const MODAL_FOCUS_TARGET_SELECTOR = '.auth-overlay, .auth-modal, .camera-modal, .otp-popup, [aria-modal="true"]';
const MODAL_FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');
const modalFocusTrapState = {
  activeModal: null,
  restoreFocusEl: null,
  keydownHandler: null,
  focusinHandler: null,
  observers: new Map(),
};

function isModalFocusTarget(element) {
  return element instanceof HTMLElement && element.matches(MODAL_FOCUS_TARGET_SELECTOR);
}

function isElementVisibleForFocus(element) {
  return element instanceof HTMLElement
    && element.isConnected
    && !element.hasAttribute('disabled')
    && element.getAttribute('aria-hidden') !== 'true'
    && element.getClientRects().length > 0;
}

function collectFocusableInModal(modal) {
  if (!(modal instanceof HTMLElement)) {
    return [];
  }
  const nodes = [...modal.querySelectorAll(MODAL_FOCUSABLE_SELECTOR)];
  return nodes.filter((node) => isElementVisibleForFocus(node));
}

function isModalVisible(modal) {
  return modal instanceof HTMLElement
    && !modal.classList.contains('hidden')
    && modal.getAttribute('aria-hidden') !== 'true';
}

function deactivateModalFocusTrap({ restoreFocus = true } = {}) {
  const { activeModal, keydownHandler, focusinHandler, restoreFocusEl } = modalFocusTrapState;
  if (!activeModal) {
    return;
  }
  if (keydownHandler) {
    document.removeEventListener('keydown', keydownHandler, true);
  }
  if (focusinHandler) {
    document.removeEventListener('focusin', focusinHandler, true);
  }
  modalFocusTrapState.activeModal = null;
  modalFocusTrapState.keydownHandler = null;
  modalFocusTrapState.focusinHandler = null;
  if (restoreFocus && isElementVisibleForFocus(restoreFocusEl)) {
    restoreFocusEl.focus({ preventScroll: true });
  }
  modalFocusTrapState.restoreFocusEl = null;
}

function activateModalFocusTrap(modal) {
  if (!(modal instanceof HTMLElement) || !isModalVisible(modal)) {
    return;
  }
  if (modalFocusTrapState.activeModal === modal) {
    return;
  }
  deactivateModalFocusTrap({ restoreFocus: false });
  modalFocusTrapState.activeModal = modal;
  modalFocusTrapState.restoreFocusEl = document.activeElement instanceof HTMLElement
    ? document.activeElement
    : null;

  const keydownHandler = (event) => {
    if (event.key !== 'Tab') {
      return;
    }
    const focusables = collectFocusableInModal(modal);
    if (!focusables.length) {
      event.preventDefault();
      modal.focus({ preventScroll: true });
      return;
    }
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    const active = document.activeElement;
    if (event.shiftKey) {
      if (active === first || !modal.contains(active)) {
        event.preventDefault();
        last.focus({ preventScroll: true });
      }
      return;
    }
    if (active === last || !modal.contains(active)) {
      event.preventDefault();
      first.focus({ preventScroll: true });
    }
  };

  const focusinHandler = (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (modal.contains(target)) {
      return;
    }
    const focusables = collectFocusableInModal(modal);
    if (focusables.length) {
      focusables[0].focus({ preventScroll: true });
      return;
    }
    modal.focus({ preventScroll: true });
  };

  modalFocusTrapState.keydownHandler = keydownHandler;
  modalFocusTrapState.focusinHandler = focusinHandler;
  document.addEventListener('keydown', keydownHandler, true);
  document.addEventListener('focusin', focusinHandler, true);

  if (!modal.hasAttribute('tabindex')) {
    modal.setAttribute('tabindex', '-1');
  }
  const preferred = modal.querySelector('[data-autofocus], [autofocus]');
  if (isElementVisibleForFocus(preferred)) {
    preferred.focus({ preventScroll: true });
    return;
  }
  const focusables = collectFocusableInModal(modal);
  if (focusables.length) {
    focusables[0].focus({ preventScroll: true });
    return;
  }
  modal.focus({ preventScroll: true });
}

function syncModalFocusTrap(modal) {
  if (!isModalFocusTarget(modal)) {
    return;
  }
  if (isModalVisible(modal)) {
    activateModalFocusTrap(modal);
    return;
  }
  if (modalFocusTrapState.activeModal === modal) {
    deactivateModalFocusTrap({ restoreFocus: true });
  }
}

function initModalFocusTrapObserver() {
  const modals = [...document.querySelectorAll(MODAL_FOCUS_TARGET_SELECTOR)];
  for (const modal of modals) {
    if (!(modal instanceof HTMLElement) || modalFocusTrapState.observers.has(modal)) {
      continue;
    }
    const observer = new MutationObserver(() => {
      syncModalFocusTrap(modal);
    });
    observer.observe(modal, { attributes: true, attributeFilter: ['class', 'aria-hidden', 'hidden'] });
    modalFocusTrapState.observers.set(modal, observer);
    syncModalFocusTrap(modal);
  }
}

function buildEmptyStateRow({
  title = 'No data available.',
  description = '',
  iconLabel = 'INFO',
  ctaLabel = '',
  ctaClassName = 'btn',
  onCta = null,
} = {}) {
  const row = document.createElement('div');
  row.className = 'list-item empty-state-row';
  row.innerHTML = `
    <span class="empty-state-icon" aria-hidden="true">${escapeHtml(iconLabel)}</span>
    <strong>${escapeHtml(title)}</strong>
    ${description ? `<small>${escapeHtml(description)}</small>` : ''}
  `;
  if (ctaLabel && typeof onCta === 'function') {
    const action = document.createElement('button');
    action.type = 'button';
    action.className = ctaClassName;
    action.textContent = ctaLabel;
    action.addEventListener('click', () => {
      onCta();
    });
    row.appendChild(action);
  }
  return row;
}

function selectedAuthRole() {
  const role = String(els.authRoleSelect?.value || '').trim().toLowerCase();
  if (role === 'admin' || role === 'faculty' || role === 'owner') {
    return role;
  }
  return 'student';
}

function isSignupMode() {
  return authState.mode === 'signup';
}

function setAuthMode(mode) {
  authState.mode = mode === 'signup' ? 'signup' : 'login';
  const signup = isSignupMode();
  document.body.classList.toggle('auth-signup-mode', signup);

  setHidden(els.authLoginSection, signup);
  setHidden(els.authRoleWrap, !signup);
  setHidden(els.authSignupFields, !signup);
  setHidden(els.authSignupActions, !signup);
  setHidden(els.authLoginControls, signup);

  if (els.authModeLoginBtn) {
    els.authModeLoginBtn.classList.toggle('active', !signup);
    els.authModeLoginBtn.setAttribute('aria-selected', String(!signup));
    els.authModeLoginBtn.setAttribute('tabindex', signup ? '-1' : '0');
  }
  if (els.authModeSignupBtn) {
    els.authModeSignupBtn.classList.toggle('active', signup);
    els.authModeSignupBtn.setAttribute('aria-selected', String(signup));
    els.authModeSignupBtn.setAttribute('tabindex', signup ? '0' : '-1');
  }

  syncAuthRoleForm();
  if (signup) {
    setAuthMfaInputVisible(false);
    setForgotPasswordPanel(false);
    const loginEmail = (els.authEmail?.value || '').trim().toLowerCase();
    if (loginEmail && els.authSignupEmail && !els.authSignupEmail.value.trim()) {
      els.authSignupEmail.value = loginEmail;
    }
  }
  renderPasswordStrengthHint(els.authPasswordStrength, els.authPassword?.value || '');
  renderPasswordStrengthHint(els.authSignupPasswordStrength, els.authSignupPassword?.value || '');

  if (signup) {
    setAuthMessage('Signup mode: fill all details and register your account.');
  } else {
    setAuthMessage('Login first with email/password, request OTP, then verify to continue. Use MFA code if your role requires it.');
  }
  renderOtpCooldown();
  renderForgotOtpCooldown();
}

function setSignupAdminPhotoPreview(dataUrl) {
  if (!els.authSignupAdminPhotoPreview) {
    return;
  }
  const safeUrl = String(dataUrl || '').trim();
  if (!safeUrl) {
    els.authSignupAdminPhotoPreview.removeAttribute('src');
    setHidden(els.authSignupAdminPhotoPreview, true);
    return;
  }
  els.authSignupAdminPhotoPreview.src = safeUrl;
  setHidden(els.authSignupAdminPhotoPreview, false);
}

function resetSignupAdminPhoto() {
  authState.signupAdminPhotoDataUrl = '';
  if (els.authSignupAdminPhoto) {
    els.authSignupAdminPhoto.value = '';
  }
  setSignupAdminPhotoPreview('');
}

function syncAuthRoleForm() {
  if (!isSignupMode()) {
    setHidden(els.authSignupRegistrationWrap, true);
    setHidden(els.authSignupFacultyIdWrap, true);
    setHidden(els.authSectionWrap, true);
    setHidden(els.authSemesterWrap, true);
    setHidden(els.authParentEmailWrap, true);
    setHidden(els.authSignupAdminPhotoWrap, true);
    resetSignupAdminPhoto();
    return;
  }
  const role = selectedAuthRole();
  const isStudent = role === 'student';
  const isFaculty = role === 'faculty';
  const isAdmin = role === 'admin';
  setHidden(els.authSignupRegistrationWrap, !isStudent);
  setHidden(els.authSignupFacultyIdWrap, !isFaculty);
  setHidden(els.authSectionWrap, !isStudent);
  setHidden(els.authSemesterWrap, !isStudent);
  setHidden(els.authParentEmailWrap, !isStudent);
  setHidden(els.authSignupAdminPhotoWrap, !isAdmin);
  if (!isAdmin) {
    resetSignupAdminPhoto();
  }
}

const MODULE_KEYS = new Set(['attendance', 'saarthi', 'food', 'administrative', 'rms', 'remedial']);
const ROUTE_SPLIT_MODULES_BY_ROUTE = {
  attendance: ['attendance', 'messages'],
  saarthi: ['attendance'],
  remedial: ['messages', 'remedial'],
  rms: ['rms'],
  food: ['food'],
  administrative: ['administrative'],
};
const ROUTE_SPLIT_IMPORTERS = {
  attendance: () => import(`/web/routes/attendance-live-updates.js?v=${ROUTE_SPLIT_ASSET_VERSION}`),
  messages: () => import(`/web/routes/messages-live-updates.js?v=${ROUTE_SPLIT_ASSET_VERSION}`),
  rms: () => import(`/web/routes/rms-dashboard-live-updates.js?v=${ROUTE_SPLIT_ASSET_VERSION}`),
  food: () => import(`/web/routes/food.route.js?v=${ROUTE_SPLIT_ASSET_VERSION}`),
  remedial: () => import(`/web/routes/remedial-live-updates.js?v=${ROUTE_SPLIT_ASSET_VERSION}`),
  administrative: () => import(`/web/routes/administrative-live-updates.js?v=${ROUTE_SPLIT_ASSET_VERSION}`),
};

function isRealtimeBusConnected() {
  return Boolean(realtimeBusController && typeof realtimeBusController.isConnected === 'function' && realtimeBusController.isConnected());
}

function routeSplitKeysForRoute(moduleKey) {
  const key = normalizeModuleKey(moduleKey);
  const keys = ROUTE_SPLIT_MODULES_BY_ROUTE[key];
  return Array.isArray(keys) ? keys : [];
}

async function refreshStudentAttendanceRealtime() {
  await Promise.allSettled([
    refreshStudentTimetableSurface({ forceNetwork: true }),
    loadStudentAttendanceInsights(),
    loadSaarthiStatus({ silent: true }),
  ]);
}

async function refreshFacultyAttendanceRealtime() {
  if (!authState.user) {
    return;
  }
  await refreshAttendanceData();
  if (authState.user.role === 'faculty' || authState.user.role === 'admin') {
    if (state.faculty.selectedScheduleId) {
      await refreshFacultyDashboard();
    }
  }
}

async function refreshSupportDeskRealtime() {
  await refreshSupportDeskContext({ silent: true, refreshThread: false });
  if (state.ui.supportDeskOpen && Number(state.supportDesk.selectedCounterpartyId || 0) > 0) {
    await refreshSupportDeskThread({ silent: true });
  }
}

async function refreshStudentMessagesRealtime() {
  await refreshStudentMessages();
}

async function refreshRemedialRealtime() {
  await refreshRemedialMessages();
}

async function refreshRemedialModuleRealtime() {
  await refreshRemedialModule();
}

async function refreshRmsRealtime() {
  await refreshRmsModule();
}

async function refreshFoodRealtime() {
  await refreshFoodModule();
}

async function refreshAdministrativeRealtime() {
  await refreshAdministrativeModule();
}

function buildRouteModuleRuntime() {
  return {
    realtimeBus: realtimeBusController,
    getUserRole: () => String(authState.user?.role || ''),
    getActiveModule: () => getSanitizedModuleKey(state.ui.activeModule),
    isSupportDeskOpen: () => Boolean(state.ui.supportDeskOpen),
    refreshStudentAttendance: async () => refreshStudentAttendanceRealtime(),
    refreshFacultyAttendance: async () => refreshFacultyAttendanceRealtime(),
    refreshSupportDesk: async () => refreshSupportDeskRealtime(),
    refreshStudentMessages: async () => refreshStudentMessagesRealtime(),
    refreshRemedialMessages: async () => refreshRemedialRealtime(),
    refreshRemedialModule: async () => refreshRemedialModuleRealtime(),
    refreshRms: async () => refreshRmsRealtime(),
    refreshFood: async () => refreshFoodRealtime(),
    refreshAdministrative: async () => refreshAdministrativeRealtime(),
    ensureFoodDeferredAssets: async () => ensureFoodCatalogLoaded({ preloadOnly: true }),
    log,
  };
}

async function ensureRealtimeBusController() {
  if (realtimeBusController) {
    return realtimeBusController;
  }
  if (realtimeBusLoadingPromise) {
    return realtimeBusLoadingPromise;
  }
  realtimeBusLoadingPromise = import(`/web/modules/realtime-event-bus.js?v=${ROUTE_SPLIT_ASSET_VERSION}`)
    .then((module) => {
      realtimeBusController = module.createRealtimeBus({
        url: `/events/stream?topics=${encodeURIComponent(REALTIME_TOPICS)}`,
        onStatus: (stateLabel) => {
          if (stateLabel === 'connected' || stateLabel === 'disconnected') {
            return;
          }
          log(`Realtime ${stateLabel}`);
        },
        onLog: () => {},
      });
      return realtimeBusController;
    })
    .finally(() => {
      realtimeBusLoadingPromise = null;
    });
  return realtimeBusLoadingPromise;
}

async function loadRouteSplitModule(moduleKey) {
  if (routeModuleInstances.has(moduleKey)) {
    return routeModuleInstances.get(moduleKey);
  }
  const importer = ROUTE_SPLIT_IMPORTERS[moduleKey];
  if (typeof importer !== 'function') {
    return null;
  }
  const loaded = await importer();
  routeModuleInstances.set(moduleKey, loaded || null);
  return loaded || null;
}

async function deactivateAllRouteModules() {
  for (const key of [...routeModuleActiveKeys]) {
    const module = routeModuleInstances.get(key);
    if (module && typeof module.onDeactivate === 'function') {
      module.onDeactivate();
    }
    routeModuleActiveKeys.delete(key);
  }
}

async function syncRouteCodeSplit(moduleKey) {
  const syncToken = ++routeModuleSyncToken;
  if (!authState.user || !realtimeBusController) {
    await deactivateAllRouteModules();
    routeModuleRuntime = null;
    return;
  }

  const requiredKeys = routeSplitKeysForRoute(moduleKey);
  if (!requiredKeys.length) {
    await deactivateAllRouteModules();
    routeModuleRuntime = null;
    return;
  }

  routeModuleRuntime = buildRouteModuleRuntime();
  for (const key of requiredKeys) {
    await loadRouteSplitModule(key);
  }
  if (syncToken !== routeModuleSyncToken) {
    return;
  }

  for (const key of [...routeModuleActiveKeys]) {
    if (requiredKeys.includes(key)) {
      continue;
    }
    const existing = routeModuleInstances.get(key);
    if (existing && typeof existing.onDeactivate === 'function') {
      existing.onDeactivate();
    }
    routeModuleActiveKeys.delete(key);
  }

  for (const key of requiredKeys) {
    const loaded = routeModuleInstances.get(key);
    if (!loaded || typeof loaded.onActivate !== 'function') {
      continue;
    }
    if (!routeModuleActiveKeys.has(key)) {
      loaded.onActivate(routeModuleRuntime);
      routeModuleActiveKeys.add(key);
    }
  }
}

function stopRealtimeEventBus() {
  routeModuleSyncToken += 1;
  void deactivateAllRouteModules();
  routeModuleRuntime = null;
  if (realtimeBusController && typeof realtimeBusController.disconnect === 'function') {
    realtimeBusController.disconnect();
  }
}

async function syncRealtimeEventBus() {
  if (!authState.user) {
    stopRealtimeEventBus();
    return;
  }
  const bus = await ensureRealtimeBusController();
  if (bus && typeof bus.connect === 'function') {
    bus.connect();
  }
  await syncRouteCodeSplit(getSanitizedModuleKey(state.ui.activeModule));
}

function normalizeModuleKey(rawModule) {
  const candidate = String(rawModule || '').trim().toLowerCase();
  if (MODULE_KEYS.has(candidate)) {
    return candidate;
  }
  return 'attendance';
}

function moduleFromHash() {
  const hash = String(window.location.hash || '').replace(/^#/, '').trim().toLowerCase();
  if (MODULE_KEYS.has(hash)) {
    return hash;
  }
  return '';
}

function defaultModuleForRole(role = authState.user?.role) {
  if (role === 'admin') {
    return 'rms';
  }
  if (role === 'owner') {
    return 'food';
  }
  return 'attendance';
}

function isModuleAccessible(moduleKey, role = authState.user?.role) {
  if (!role) {
    return false;
  }
  const key = normalizeModuleKey(moduleKey);
  if (key === 'saarthi') {
    return role === 'student';
  }
  if (key === 'attendance') {
    return role === 'student' || role === 'faculty' || role === 'admin';
  }
  if (key === 'food') {
    return role === 'student' || role === 'faculty' || role === 'owner';
  }
  if (key === 'administrative') {
    return role === 'admin';
  }
  if (key === 'rms') {
    return role === 'admin' || role === 'faculty';
  }
  if (key === 'remedial') {
    return role === 'student' || role === 'faculty';
  }
  return false;
}

function getSanitizedModuleKey(rawModule) {
  const candidate = normalizeModuleKey(rawModule || state.ui.activeModule);
  if (isModuleAccessible(candidate)) {
    return candidate;
  }
  return defaultModuleForRole();
}

function setTopNavActive(moduleKey) {
  const active = normalizeModuleKey(moduleKey);
  const topButtons = [
    els.topNavAttendanceBtn,
    els.topNavSaarthiBtn,
    els.topNavFoodBtn,
    els.topNavAdministrativeBtn,
    els.topNavRmsBtn,
    els.topNavRemedialBtn,
  ].filter(Boolean);

  for (const button of topButtons) {
    const isActive = button.dataset.module === active;
    button.classList.toggle('active', isActive);
    button.setAttribute('aria-current', isActive ? 'page' : 'false');
  }
  syncTopNavActiveButtonIntoView();
}

function updateModuleHash(moduleKey) {
  const nextHash = `#${normalizeModuleKey(moduleKey)}`;
  if (window.location.hash === nextHash) {
    return;
  }
  if (window.history?.replaceState) {
    window.history.replaceState(null, '', nextHash);
    return;
  }
  window.location.hash = nextHash;
}

function resolveSidebarModuleTarget() {
  const currentModule = getSanitizedModuleKey(state.ui.activeModule);
  if (isModuleAccessible(currentModule)) {
    return currentModule;
  }
  return defaultModuleForRole();
}

function setActiveModule(moduleKey, { updateHash = true } = {}) {
  if (!authState.user) {
    return;
  }
  const nextModule = getSanitizedModuleKey(moduleKey);
  state.ui.activeModule = nextModule;
  if (updateHash) {
    updateModuleHash(nextModule);
  }
  applyRoleUI();
  setTopNavActive(nextModule);
  syncFoodDemandLiveTicker();
  void syncRouteCodeSplit(nextModule);
}

function updateDashboardHeroByRole() {
  if (!els.dashboardTitle || !els.dashboardSubtitle) {
    return;
  }
  const role = authState.user?.role;
  if (role === 'admin') {
    els.dashboardTitle.textContent = 'Administrative Operations Command Center';
    els.dashboardSubtitle.textContent = 'Monitor attendance, capacity, demand, and institutional health in real time.';
  } else if (role === 'faculty') {
    els.dashboardTitle.textContent = 'Faculty Instruction Console';
    els.dashboardSubtitle.textContent = 'Run classes, review attendance queues, and track section performance.';
  } else if (role === 'student') {
    els.dashboardTitle.textContent = 'Student Success Dashboard';
    els.dashboardSubtitle.textContent = 'Track attendance, Saarthi mentoring, schedules, remedials, and campus food workflows from one place.';
  } else if (role === 'owner') {
    els.dashboardTitle.textContent = 'Vendor Operations Console';
    els.dashboardSubtitle.textContent = 'Manage order intake, preparation flow, and delivery timelines for your shop.';
  } else {
    els.dashboardTitle.textContent = 'Campus Command Center';
    els.dashboardSubtitle.textContent = 'Unified attendance, remedial, food, and operations workflows.';
  }
}

const ADMIN_SUBMODULE_DEFAULTS = {
  attendance: 'attendance-ops',
  rms: 'rms-overview',
};

const ROLE_CLASS_LIST = ['role-admin', 'role-faculty', 'role-student', 'role-owner', 'role-guest'];

function syncRoleClass(role) {
  const body = document.body;
  if (!body) {
    return;
  }
  ROLE_CLASS_LIST.forEach((className) => body.classList.remove(className));
  const safeRole = role || 'guest';
  body.classList.add(`role-${safeRole}`);
  body.dataset.role = safeRole;
}

function resolveAdminSubmodule(scope, panels) {
  const candidates = Array.from(panels)
    .map((panel) => String(panel.dataset.adminSubmodule || '').trim())
    .filter(Boolean);
  const available = new Set(candidates);
  const stored = state.ui.adminSubmodules?.[scope];
  const fallback = ADMIN_SUBMODULE_DEFAULTS[scope];
  let active = String(stored || fallback || '').trim();
  if (!active || !available.has(active)) {
    active = candidates[0] || active;
    if (active) {
      state.ui.adminSubmodules[scope] = active;
    }
  }
  return active;
}

function syncAdminSubmodulePanels(scope) {
  if (!scope) {
    return;
  }
  const panels = document.querySelectorAll(`[data-admin-submodule-scope="${scope}"]`);
  if (!panels.length) {
    return;
  }
  const isAdmin = authState.user?.role === 'admin';
  if (!isAdmin) {
    panels.forEach((panel) => {
      panel.classList.remove('is-active');
      panel.removeAttribute('aria-hidden');
    });
    return;
  }
  const active = resolveAdminSubmodule(scope, panels);
  panels.forEach((panel) => {
    const isActive = panel.dataset.adminSubmodule === active;
    panel.classList.toggle('is-active', isActive);
    panel.setAttribute('aria-hidden', isActive ? 'false' : 'true');
  });
  const select = document.querySelector(`[data-admin-submodule-select="${scope}"]`);
  if (select && active && select.value !== active) {
    select.value = active;
  }
}

function syncAdminSubmodulesForRole() {
  syncAdminSubmodulePanels('attendance');
  syncAdminSubmodulePanels('rms');
}

function setAdminSubmodule(scope, submodule) {
  if (!scope || !submodule) {
    return;
  }
  if (!state.ui.adminSubmodules) {
    state.ui.adminSubmodules = {};
  }
  state.ui.adminSubmodules[scope] = submodule;
  syncAdminSubmodulePanels(scope);
}

function bindAdminSubmodulePickers() {
  const selects = document.querySelectorAll('[data-admin-submodule-select]');
  selects.forEach((select) => {
    select.addEventListener('change', () => {
      const scope = select.dataset.adminSubmoduleSelect;
      const nextValue = String(select.value || '').trim();
      if (!scope || !nextValue) {
        return;
      }
      setAdminSubmodule(scope, nextValue);
    });
  });
}

function applyRoleUI() {
  const role = authState.user?.role;
  const isAdmin = role === 'admin';
  const isFaculty = role === 'faculty';
  const isFacultyOrAdmin = isFaculty || isAdmin;
  const isOwner = role === 'owner';
  const isStudent = role === 'student';
  const isFoodOperator = isFaculty || isOwner;
  const activeModule = getSanitizedModuleKey(state.ui.activeModule);
  state.ui.activeModule = activeModule;

  syncRoleClass(role);

  setHidden(els.accountSection, true);
  setHidden(els.executiveSection, !isAdmin || activeModule !== 'administrative');
  setHidden(els.rmsSection, !isFacultyOrAdmin || activeModule !== 'rms');
  setHidden(els.rmsAdminDedicatedNote, !isAdmin || activeModule !== 'rms');
  setHidden(els.studentSection, !isStudent || activeModule !== 'attendance');
  setHidden(els.saarthiSection, !isStudent || activeModule !== 'saarthi');
  setHidden(els.facultySection, !isFacultyOrAdmin || activeModule !== 'attendance');
  setHidden(els.adminAttendanceActionsCard, !isAdmin || activeModule !== 'attendance');
  setHidden(els.foodSection, !authState.user || activeModule !== 'food');
  setHidden(els.remedialSection, !authState.user || activeModule !== 'remedial');
  setHidden(els.remedialFacultyPanel, !isFaculty);
  setHidden(els.remedialStudentPanel, !isStudent);
  setHidden(els.foodAdminPanel, !isFoodOperator);
  setHidden(els.foodGlobalItemControls, !isFaculty);
  setHidden(els.foodGlobalSlotControls, !isFaculty);
  setHidden(els.foodOrderStatusControls, !isFoodOperator);

  if (els.foodAdminPanelTitle) {
    els.foodAdminPanelTitle.textContent = isOwner
      ? 'Shop Owner Control Panel'
      : 'Food Configuration & Status Control';
  }
  if (els.foodAdminPanelSubtitle) {
    els.foodAdminPanelSubtitle.textContent = isOwner
      ? 'Manage only your assigned shop orders and statuses'
      : 'Create items/slots and push live order status updates';
  }

  setHidden(els.absenteeCard, isStudent);
  setHidden(els.aiAbsentBtn, isStudent);
  setHidden(els.aiRushBtn, isStudent);
  setHidden(els.capacityCard, !authState.user);

  if (isStudent && els.courseId) {
    els.courseId.value = '1';
  }

  if (!authState.user && els.aiOutput) {
    els.aiOutput.textContent = 'AI output will appear here.';
  }

  syncAdminSubmodulesForRole();

  setTopNavActive(activeModule);
  const moduleButtons = [
    els.topNavAttendanceBtn,
    els.topNavSaarthiBtn,
    els.topNavFoodBtn,
    els.topNavAdministrativeBtn,
    els.topNavRmsBtn,
    els.topNavRemedialBtn,
  ].filter(Boolean);
  for (const button of moduleButtons) {
    const moduleKey = normalizeModuleKey(button.dataset.module);
    const visible = Boolean(role) && isModuleAccessible(moduleKey, role);
    setHidden(button, !visible);
    button.disabled = !visible;
  }

  if (isStudent) {
    startStudentTimetableStatusTicker();
  } else {
    stopStudentTimetableStatusTicker();
    closeAttendanceDetailsModal();
  }
  if (!isFaculty) {
    closeRemedialAttendanceModal();
  }

  if (!authState.user) {
    setSidebarActive('dashboard');
  }
  updateDashboardHeroByRole();
  renderFoodDemoToggle();
  renderEnrollmentSummary();
  syncFoodLocationMonitoringByModule();
  syncRemedialLiveTicker();
  syncVerlynVisualContext();
  updateVerlynVisibility();
  renderVerlynQuickActions();
  updateChotuVisibility();
  updateSupportDeskVisibility();
  syncSupportDeskLiveTicker();
  if (isAdmin && activeModule === 'administrative') {
    void refreshCopilotAuditTimeline({ silent: true });
  }
  void syncRealtimeEventBus();
}

function setSidebarActive(navKey) {
  const navItems = document.querySelectorAll('.ums-side-item[data-nav]');
  for (const item of navItems) {
    const active = item.dataset.nav === navKey;
    item.classList.toggle('active', active);
    item.setAttribute('aria-current', active ? 'page' : 'false');
  }
}

function resolveSidebarTarget(navKey) {
  if (navKey === 'dashboard') {
    return document.getElementById('main-dashboard-header') || document.getElementById('dashboard-root');
  }

  const role = authState.user?.role;
  const activeModule = getSanitizedModuleKey(state.ui.activeModule);

  if (activeModule !== 'attendance') {
    const moduleRouteMap = {
      saarthi: {
        courses: document.getElementById('student-saarthi-card'),
        attendance: document.getElementById('student-saarthi-card'),
        fallback: els.saarthiSection,
      },
      food: {
        courses: document.getElementById('food-shop-grid'),
        attendance: document.getElementById('food-orders-panel'),
        fallback: els.foodSection,
      },
      administrative: {
        courses: document.getElementById('admin-profile-card'),
        attendance: document.getElementById('admin-attendance-card') || document.getElementById('absentee-card'),
        fallback: els.executiveSection,
      },
      rms: {
        courses: document.getElementById('rms-query-list'),
        attendance: document.getElementById('rms-attendance-result') || document.getElementById('rms-attendance-registration'),
        fallback: els.rmsSection,
      },
      remedial: {
        courses: role === 'student'
          ? document.getElementById('remedial-messages-list')
          : document.getElementById('remedial-classes-list'),
        attendance: role === 'student'
          ? document.getElementById('remedial-code-input')
          : document.getElementById('remedial-attendance-list') || document.getElementById('remedial-refresh-attendance-btn'),
        fallback: role === 'student'
          ? document.getElementById('remedial-student-panel')
          : document.getElementById('remedial-faculty-panel') || els.remedialSection,
      },
    };
    const moduleTargets = moduleRouteMap[activeModule];
    if (moduleTargets) {
      return moduleTargets[navKey] || moduleTargets.fallback || document.getElementById('dashboard-root');
    }
  }

  if (role === 'student') {
    if (navKey === 'courses') {
      return document.getElementById('student-courses-card') || els.studentSection;
    }
    if (navKey === 'attendance') {
      return document.getElementById('student-attendance-card') || els.studentSection;
    }
  }

  if (role === 'faculty') {
    if (navKey === 'courses') {
      return document.getElementById('faculty-dashboard-card') || els.facultySection;
    }
    if (navKey === 'attendance') {
      return document.getElementById('faculty-attendance-card') || els.facultySection;
    }
  }

  if (navKey === 'courses') {
    return document.getElementById('faculty-dashboard-card')
      || document.getElementById('admin-profile-card')
      || els.facultySection
      || els.executiveSection
      || els.rmsSection
      || els.remedialSection
      || els.foodSection;
  }
  if (navKey === 'attendance') {
    return document.getElementById('faculty-attendance-card')
      || document.getElementById('student-attendance-card')
      || document.getElementById('admin-attendance-card')
      || document.getElementById('rms-attendance-result')
      || document.getElementById('remedial-code-input')
      || document.getElementById('food-orders-panel')
      || document.getElementById('absentee-card')
      || els.executiveSection
      || els.facultySection
      || els.studentSection;
  }
  return document.getElementById('dashboard-root');
}

function navigateSidebar(navKey) {
  if (!navKey) {
    return;
  }

  if (!authState.user) {
    setSidebarActive('dashboard');
    openAuthOverlay('Sign in to open dashboard sections.');
    return;
  }

  if (requiresRoleProfileSetup()) {
    openProfileModal({ required: true });
    return;
  }
  if (authState.user.role === 'student' && requiresStudentEnrollmentSetup()) {
    openEnrollmentModal({ required: true });
    return;
  }

  setActiveModule(resolveSidebarModuleTarget(), { updateHash: true });

  const target = resolveSidebarTarget(navKey);
  if (!target) {
    return;
  }

  setSidebarActive(navKey);
  target.scrollIntoView({ behavior: 'smooth', block: 'start', inline: 'nearest' });
  flashSection(target);
}

function renderAlternateEmailStatus() {
  if (!authState.user || !els.alternateEmailStatus) {
    return;
  }
  if (!authState.user.primary_login_verified) {
    els.alternateEmailStatus.textContent = 'Login once using your primary email before saving a secondary email.';
    return;
  }
  if (authState.user.alternate_email) {
    els.alternateEmailStatus.textContent = `Secondary email saved: ${authState.user.alternate_email}`;
    return;
  }
  els.alternateEmailStatus.textContent = 'No secondary email configured.';
}

function formatLockDateTime(dateValue) {
  if (!dateValue) {
    return 'later';
  }
  try {
    return new Date(dateValue).toLocaleString(undefined, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  } catch (_) {
    return String(dateValue);
  }
}

function formatRemainingMinutes(minutesValue) {
  const total = Math.max(0, Number(minutesValue || 0));
  if (!Number.isFinite(total) || total <= 0) {
    return '0m';
  }
  const days = Math.floor(total / 1440);
  const hours = Math.floor((total % 1440) / 60);
  const minutes = total % 60;
  const parts = [];
  if (days > 0) {
    parts.push(`${days}d`);
  }
  if (hours > 0) {
    parts.push(`${hours}h`);
  }
  if (minutes > 0 || !parts.length) {
    parts.push(`${minutes}m`);
  }
  return parts.join(' ');
}

function showProfilePhotoLockPopup() {
  const lockedUntil = formatLockDateTime(state.student.profilePhotoLockedUntil);
  const remaining = Math.max(0, Number(state.student.profilePhotoLockDaysRemaining || 0));
  showOtpPopup(
    'Profile Photo Locked',
    `Profile photo locked until ${lockedUntil}. Remaining: ${remaining} day(s).`,
    { tone: 'cooldown', loading: false, closable: true }
  );
}

function showFacultyProfilePhotoLockPopup() {
  const lockedUntil = formatLockDateTime(state.facultyProfile.profilePhotoLockedUntil);
  const remaining = Math.max(0, Number(state.facultyProfile.profilePhotoLockDaysRemaining || 0));
  showOtpPopup(
    'Faculty Photo Locked',
    `Faculty profile photo locked until ${lockedUntil}. Remaining: ${remaining} day(s).`,
    { tone: 'cooldown', loading: false, closable: true }
  );
}

function showFacultySectionLockPopup() {
  const lockedUntil = formatLockDateTime(state.facultyProfile.sectionLockedUntil);
  const remaining = Math.max(0, Number(state.facultyProfile.sectionLockMinutesRemaining || 0));
  showOtpPopup(
    'Section Update Locked',
    `Section can be changed again after ${lockedUntil}. Remaining: ${formatRemainingMinutes(remaining)}.`,
    { tone: 'cooldown', loading: false, closable: true }
  );
}

function showActiveProfilePhotoLockPopup() {
  if (authState.user?.role === 'faculty') {
    showFacultyProfilePhotoLockPopup();
    return;
  }
  showProfilePhotoLockPopup();
}

function showEnrollmentLockPopup() {
  const lockedUntil = formatLockDateTime(state.student.enrollmentLockedUntil);
  const remaining = Math.max(0, Number(state.student.enrollmentLockDaysRemaining || 0));
  showOtpPopup(
    'Enrollment Video Locked',
    `Enrollment video locked until ${lockedUntil}. Remaining: ${remaining} day(s).`,
    { tone: 'cooldown', loading: false, closable: true }
  );
}

function openEnrollmentPhotoUpdateFlow() {
  if (authState.user?.role !== 'student') {
    return;
  }
  setProfileTab('details');
  if (!els.profilePhotoInput) {
    return;
  }
  if (state.student.profilePhotoDataUrl && !state.student.profilePhotoCanUpdateNow) {
    showProfilePhotoLockPopup();
    return;
  }
  try {
    els.profilePhotoInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    els.profilePhotoInput.click();
  } catch (_) {
    // File chooser may be blocked by browser policy; input remains visible for manual action.
  }
}

function setProfileTab(tabKey = 'details') {
  const canShowEnrollment = authState.user?.role === 'student';
  const showEnrollment = canShowEnrollment && String(tabKey || '').toLowerCase() === 'enrollment';
  if (els.profileTabDetailsBtn && els.profileTabEnrollmentBtn) {
    setHidden(els.profileTabEnrollmentBtn, !canShowEnrollment);
    els.profileTabDetailsBtn.classList.toggle('active', !showEnrollment);
    els.profileTabDetailsBtn.setAttribute('aria-selected', showEnrollment ? 'false' : 'true');
    els.profileTabEnrollmentBtn.classList.toggle('active', showEnrollment);
    els.profileTabEnrollmentBtn.setAttribute('aria-selected', showEnrollment ? 'true' : 'false');
  }
  if (els.profileTabDetails) {
    els.profileTabDetails.classList.toggle('active', !showEnrollment);
    els.profileTabDetails.classList.toggle('hidden', showEnrollment);
  }
  if (els.profileTabEnrollment) {
    setHidden(els.profileTabEnrollment, !canShowEnrollment);
    els.profileTabEnrollment.classList.toggle('active', showEnrollment);
    els.profileTabEnrollment.classList.toggle('hidden', !showEnrollment);
  }
}

function renderEnrollmentSummary() {
  const photoUrl = state.student.profilePhotoDataUrl || state.student.pendingProfilePhotoDataUrl || '';

  if (els.enrollmentPhotoPreview) {
    if (photoUrl) {
      els.enrollmentPhotoPreview.src = photoUrl;
      els.enrollmentPhotoPreview.classList.remove('hidden');
    } else {
      els.enrollmentPhotoPreview.src = '';
      els.enrollmentPhotoPreview.classList.add('hidden');
    }
  }

  if (els.enrollmentSummaryStatus) {
    if (authState.user?.role !== 'student') {
      els.enrollmentSummaryStatus.textContent = 'Enrollment details are available for student accounts.';
    } else if (!state.student.profileLoaded) {
      els.enrollmentSummaryStatus.textContent = 'Loading profile details...';
    } else if (!state.student.enrollmentLoaded) {
      els.enrollmentSummaryStatus.textContent = 'Checking enrollment status...';
    } else if (state.student.hasEnrollmentVideo) {
      if (state.student.enrollmentCanUpdateNow) {
        els.enrollmentSummaryStatus.textContent = 'Enrollment video is active and used for attendance verification.';
      } else {
        els.enrollmentSummaryStatus.textContent = 'Enrollment video is active. Update is locked for the 14-day security window.';
      }
    } else {
      els.enrollmentSummaryStatus.textContent = 'Enrollment video not uploaded yet. Upload once to enable secure attendance.';
    }
  }

  if (els.enrollmentSummaryUpdated) {
    if (state.student.enrollmentUpdatedAt) {
      const updatedAtText = new Date(state.student.enrollmentUpdatedAt).toLocaleString(undefined, {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
      els.enrollmentSummaryUpdated.textContent = `Last updated: ${updatedAtText}`;
    } else if (authState.user?.role === 'student') {
      els.enrollmentSummaryUpdated.textContent = 'No enrollment video captured yet.';
    } else {
      els.enrollmentSummaryUpdated.textContent = '';
    }
  }

  if (els.enrollmentSummaryLock) {
    if (authState.user?.role !== 'student' || !state.student.enrollmentLoaded) {
      els.enrollmentSummaryLock.textContent = '';
    } else if (state.student.hasEnrollmentVideo && !state.student.enrollmentCanUpdateNow) {
      const remaining = Math.max(0, Number(state.student.enrollmentLockDaysRemaining || 0));
      els.enrollmentSummaryLock.textContent = `Locked until ${formatLockDateTime(state.student.enrollmentLockedUntil)} (${remaining} day(s) remaining).`;
    } else if (state.student.hasEnrollmentVideo) {
      els.enrollmentSummaryLock.textContent = 'You can re-capture enrollment video now.';
    } else {
      els.enrollmentSummaryLock.textContent = 'Capture once now. Next update will be locked for 14 days.';
    }
  }

  if (els.openEnrollmentModalBtn) {
    if (authState.user?.role !== 'student') {
      els.openEnrollmentModalBtn.disabled = true;
      els.openEnrollmentModalBtn.textContent = 'Enrollment Available For Students';
    } else if (!state.student.hasEnrollmentVideo) {
      els.openEnrollmentModalBtn.disabled = false;
      els.openEnrollmentModalBtn.textContent = 'Capture Enrollment Video';
    } else if (!state.student.enrollmentCanUpdateNow) {
      els.openEnrollmentModalBtn.disabled = false;
      els.openEnrollmentModalBtn.textContent = 'Update Enrollment Video';
    } else {
      els.openEnrollmentModalBtn.disabled = false;
      els.openEnrollmentModalBtn.textContent = 'Update Enrollment Video';
    }
  }

  if (els.openProfilePhotoUpdateBtn) {
    if (authState.user?.role !== 'student') {
      els.openProfilePhotoUpdateBtn.disabled = true;
      els.openProfilePhotoUpdateBtn.textContent = 'Photo Update (Students Only)';
    } else {
      els.openProfilePhotoUpdateBtn.disabled = false;
      els.openProfilePhotoUpdateBtn.textContent = 'Update Enrollment Photo';
    }
  }
}

function openProfileModal({ required = false } = {}) {
  if (!els.profileModal) {
    return;
  }
  const role = authState.user?.role;
  if (role === 'faculty') {
    state.facultyProfile.profileSetupRequired = Boolean(required);
  } else if (role === 'owner') {
    state.student.profileSetupRequired = false;
    state.facultyProfile.profileSetupRequired = false;
  } else {
    state.student.profileSetupRequired = Boolean(required);
  }
  els.profileModal.classList.remove('hidden');
  if (els.profileModalTitle) {
    if (role === 'faculty') {
      els.profileModalTitle.textContent = required ? 'Complete Faculty Profile Setup' : 'Faculty Profile Settings';
    } else if (role === 'admin') {
      els.profileModalTitle.textContent = 'Admin Profile';
    } else if (role === 'owner') {
      els.profileModalTitle.textContent = 'Vendor Profile';
    } else {
      els.profileModalTitle.textContent = required ? 'Complete Student Profile Setup' : 'Student Profile Settings';
    }
  }
  if (els.profileModalSubtitle) {
    if (role === 'faculty') {
      els.profileModalSubtitle.textContent = required
        ? 'Enter full name, upload profile photo, set faculty ID, and set section before using the portal.'
        : 'Manage faculty ID, section, profile photo, and secondary email.';
    } else if (role === 'admin') {
      els.profileModalSubtitle.textContent = 'Admin identity is managed centrally. Use attendance controls for approve/disapprove and schedule actions.';
    } else if (role === 'owner') {
      els.profileModalSubtitle.textContent = 'Vendor identity is separate and connected to your assigned shop data.';
    } else {
      els.profileModalSubtitle.textContent = required
        ? 'Enter full name, upload your profile photo, set registration number, and set section before using the portal.'
        : 'Manage profile photo, registration number, section, and secondary email.';
    }
  }
  if (els.profileCloseBtn) {
    els.profileCloseBtn.disabled = required;
    setHidden(els.profileCloseBtn, required);
  }
  setProfileTab('details');
  renderProfileSecurity();
}

function closeProfileModal() {
  if (!els.profileModal) {
    return;
  }
  if (authState.user?.role === 'faculty' && state.facultyProfile.profileSetupRequired) {
    return;
  }
  if (authState.user?.role !== 'faculty' && state.student.profileSetupRequired) {
    return;
  }
  els.profileModal.classList.add('hidden');
}

function stopEnrollmentCameraStream() {
  if (!state.student.enrollmentStream) {
    return;
  }
  for (const track of state.student.enrollmentStream.getTracks()) {
    track.stop();
  }
  state.student.enrollmentStream = null;
  if (els.enrollmentVideo) {
    els.enrollmentVideo.classList.remove('is-selfie');
    els.enrollmentVideo.srcObject = null;
  }
  if (els.enrollmentVideoDemo) {
    els.enrollmentVideoDemo.classList.remove('hidden');
  }
}

function requiresStudentEnrollmentSetup() {
  if (authState.user?.role !== 'student') {
    return false;
  }
  if (!state.student.profileLoaded || !state.student.enrollmentLoaded) {
    return false;
  }
  return !state.student.hasEnrollmentVideo;
}

function openEnrollmentModal({ required = false } = {}) {
  if (!els.enrollmentModal) {
    return;
  }
  if (!required && state.student.hasEnrollmentVideo && !state.student.enrollmentCanUpdateNow) {
    showEnrollmentLockPopup();
    return;
  }
  state.student.enrollmentRequired = Boolean(required);
  els.enrollmentModal.classList.remove('hidden');
  if (els.enrollmentModalTitle) {
    els.enrollmentModalTitle.textContent = required ? 'One-Time Video Enrollment Required' : 'Update Enrollment Video';
  }
  if (els.enrollmentModalSubtitle) {
    els.enrollmentModalSubtitle.textContent = required
      ? 'Complete guided face enrollment before accessing dashboard.'
      : 'Refresh enrollment template with guided multi-angle capture.';
  }
  if (els.enrollmentCloseBtn) {
    els.enrollmentCloseBtn.disabled = required;
    setHidden(els.enrollmentCloseBtn, required);
  }
  if (els.enrollmentVideoDemo && !state.student.enrollmentStream) {
    els.enrollmentVideoDemo.classList.remove('hidden');
  }
  state.student.enrollmentFrames = [];
  if (els.enrollmentInstruction) {
    els.enrollmentInstruction.textContent = 'Press Start Capture to begin guided recording.';
  }
  if (els.enrollmentProgress) {
    els.enrollmentProgress.textContent = '';
  }
  const updateLocked = !required && !state.student.enrollmentCanUpdateNow;
  if (els.enrollmentStartBtn) {
    els.enrollmentStartBtn.disabled = updateLocked;
  }
  if (els.enrollmentSaveBtn) {
    els.enrollmentSaveBtn.disabled = true;
  }
  if (els.enrollmentStatus) {
    if (required) {
      els.enrollmentStatus.textContent = 'Enrollment video is mandatory. Capture and save to continue.';
    } else if (state.student.enrollmentCanUpdateNow) {
      els.enrollmentStatus.textContent = 'Capture a new enrollment video to refresh identity template.';
    } else {
      const lockedUntil = state.student.enrollmentLockedUntil
        ? new Date(state.student.enrollmentLockedUntil).toLocaleString()
        : 'later';
      els.enrollmentStatus.textContent = `Enrollment update locked until ${lockedUntil}.`;
    }
  }
}

function closeEnrollmentModal() {
  if (!els.enrollmentModal) {
    return;
  }
  if (state.student.enrollmentRequired) {
    return;
  }
  els.enrollmentModal.classList.add('hidden');
  stopEnrollmentCameraStream();
}

function requiresStudentProfileSetup() {
  if (authState.user?.role !== 'student') {
    return false;
  }
  if (!state.student.profileLoaded) {
    return false;
  }
  return !hasValidProfileName(state.student.name || authState.user?.name || '')
    || !state.student.registrationNumber
    || !state.student.section
    || !state.student.profilePhotoDataUrl;
}

function requiresFacultyProfileSetup() {
  if (authState.user?.role !== 'faculty') {
    return false;
  }
  if (!state.facultyProfile.profileLoaded) {
    return false;
  }
  return !hasValidProfileName(state.facultyProfile.name || authState.user?.name || '')
    || !state.facultyProfile.facultyIdentifier
    || !state.facultyProfile.section
    || !state.facultyProfile.profilePhotoDataUrl;
}

function requiresRoleProfileSetup() {
  if (authState.user?.role === 'student') {
    return requiresStudentProfileSetup();
  }
  if (authState.user?.role === 'faculty') {
    return requiresFacultyProfileSetup();
  }
  return false;
}

function maybePromptProfileSetup() {
  if (authState.user?.role !== 'student') {
    return;
  }
  if (!state.student.profileLoaded) {
    return;
  }
  if (!requiresStudentProfileSetup()) {
    return;
  }
  const email = authState.user?.email || '';
  if (hasSeenProfileSetupPrompt(email)) {
    return;
  }
  markProfileSetupPromptSeen(email);
  openProfileModal({ required: true });
}

function maybePromptFacultyProfileSetup() {
  if (authState.user?.role !== 'faculty') {
    return;
  }
  if (!state.facultyProfile.profileLoaded || !requiresFacultyProfileSetup()) {
    return;
  }
  const email = authState.user?.email || '';
  if (hasSeenProfileSetupPrompt(email)) {
    return;
  }
  markProfileSetupPromptSeen(email);
  openProfileModal({ required: true });
}

function maybePromptEnrollmentSetup() {
  if (authState.user?.role !== 'student') {
    return;
  }
  if (!state.student.profileLoaded || !state.student.enrollmentLoaded) {
    return;
  }
  if (requiresStudentProfileSetup()) {
    return;
  }
  if (!requiresStudentEnrollmentSetup()) {
    return;
  }
  openEnrollmentModal({ required: true });
}

function renderProfileSecurity() {
  renderAccountMenuProfile();

  if (!authState.user) {
    if (els.profilePrimaryEmail) {
      els.profilePrimaryEmail.value = '';
    }
    if (els.profileFullName) {
      els.profileFullName.value = '';
      els.profileFullName.disabled = false;
    }
    if (els.profileIdLabel) {
      els.profileIdLabel.textContent = 'Registration Number';
    }
    if (els.profileRegistrationNumber) {
      els.profileRegistrationNumber.value = '';
      els.profileRegistrationNumber.disabled = false;
      els.profileRegistrationNumber.placeholder = 'e.g. R9P132A48';
    }
    if (els.profileRegistrationNote) {
      els.profileRegistrationNote.textContent = 'Registration number is permanent and cannot be changed without admin permissions.';
    }
    if (els.profileSectionWrap) {
      setHidden(els.profileSectionWrap, true);
    }
    if (els.profileSectionInput) {
      els.profileSectionInput.value = '';
      els.profileSectionInput.disabled = true;
    }
    if (els.profileSectionNote) {
      els.profileSectionNote.textContent = '';
      setHidden(els.profileSectionNote, true);
    }
    if (els.profilePhotoWrap) {
      setHidden(els.profilePhotoWrap, false);
    }
    if (els.profileAlternateEmail) {
      els.profileAlternateEmail.value = '';
      els.profileAlternateEmail.disabled = true;
    }
    if (els.saveAlternateEmailBtn) {
      els.saveAlternateEmailBtn.disabled = true;
    }
    if (els.alternateEmailStatus) {
      els.alternateEmailStatus.textContent = '';
    }
    renderProfilePhotoPreview('');
    setProfileTab('details');
    renderEnrollmentSummary();
    renderProfileStatusByRole();
    closeAccountDropdown();
    return;
  }

  if (els.profilePrimaryEmail) {
    els.profilePrimaryEmail.value = authState.user.email || '';
  }
  const role = authState.user.role;
  const isStudent = role === 'student';
  const isFaculty = role === 'faculty';
  const isAdmin = role === 'admin';
  const isOwner = role === 'owner';
  const isProfileEditableRole = isStudent || isFaculty;
  const normalizedActiveName = normalizeProfileName(
    isFaculty
      ? (state.facultyProfile.name || authState.user?.name || '')
      : isStudent
        ? (state.student.name || authState.user?.name || '')
        : (authState.user?.name || '')
  );
  if (els.profileFullName) {
    els.profileFullName.value = normalizedActiveName;
    els.profileFullName.disabled = !isProfileEditableRole || hasValidProfileName(normalizedActiveName);
  }
  const currentIdValue = isStudent
    ? (state.student.registrationNumber || '')
    : isFaculty
      ? (state.facultyProfile.facultyIdentifier || '')
      : isAdmin
        ? (authState.user?.id ? `ADMIN-${authState.user.id}` : '')
      : (authState.user?.id ? `OWNER-${authState.user.id}` : '');

  if (els.profileIdLabel) {
    els.profileIdLabel.textContent = isFaculty
      ? 'Faculty ID'
      : isAdmin
        ? 'Admin ID'
      : isOwner
        ? 'Vendor ID'
        : 'Registration Number';
  }
  if (els.profileRegistrationNumber) {
    els.profileRegistrationNumber.value = currentIdValue;
    els.profileRegistrationNumber.disabled = !isProfileEditableRole || Boolean(currentIdValue);
    els.profileRegistrationNumber.placeholder = isFaculty
      ? 'e.g. FAC-CSE-1024'
      : isOwner
        ? 'Auto-assigned from account'
        : 'e.g. R9P132A48';
  }
  if (els.profileRegistrationNote) {
    els.profileRegistrationNote.textContent = isFaculty
      ? 'Faculty ID is permanent and cannot be changed without admin permissions.'
      : isAdmin
        ? 'Admin ID is linked to your account and managed centrally.'
      : isOwner
        ? 'Vendor ID is mapped from your account and connected to owned shop data.'
        : 'Registration number is permanent and cannot be changed without admin permissions.';
  }
  if (els.profileSectionWrap) {
    setHidden(els.profileSectionWrap, !isFaculty && !isStudent);
  }
  if (els.profileSectionInput) {
    const facultyHasSection = Boolean(state.facultyProfile.section);
    const studentHasSection = Boolean(state.student.section);
    if (isFaculty) {
      els.profileSectionInput.value = state.facultyProfile.section || '';
      els.profileSectionInput.disabled = facultyHasSection && !state.facultyProfile.sectionCanUpdateNow;
    } else if (isStudent) {
      els.profileSectionInput.value = state.student.section || '';
      els.profileSectionInput.disabled = studentHasSection;
    } else {
      els.profileSectionInput.value = '';
      els.profileSectionInput.disabled = true;
    }
  }
  if (els.profileSectionNote) {
    if (isFaculty) {
      setHidden(els.profileSectionNote, false);
      if (!state.facultyProfile.section) {
        els.profileSectionNote.textContent = 'Section is required. After save, section can be changed every 24 hours.';
      } else if (!state.facultyProfile.sectionCanUpdateNow) {
        els.profileSectionNote.textContent = `Section update locked until ${formatLockDateTime(state.facultyProfile.sectionLockedUntil)} (${formatRemainingMinutes(state.facultyProfile.sectionLockMinutesRemaining)} remaining).`;
      } else {
        els.profileSectionNote.textContent = 'Section is set. You can update it now (next lock: 24 hours).';
      }
    } else if (isStudent) {
      setHidden(els.profileSectionNote, false);
      if (!state.student.section) {
        els.profileSectionNote.textContent = 'Section is required. Set it once to continue. Further changes require faculty approval after 48 hours.';
      } else if (state.student.sectionChangeRequiresFacultyApproval) {
        els.profileSectionNote.textContent = 'Section change window is open. Ask your faculty to approve the section update.';
      } else {
        els.profileSectionNote.textContent = `Section is set. Self-update is disabled. Faculty can approve change after ${formatLockDateTime(state.student.sectionLockedUntil)} (${formatRemainingMinutes(state.student.sectionLockMinutesRemaining)} remaining).`;
      }
    } else {
      els.profileSectionNote.textContent = '';
      setHidden(els.profileSectionNote, true);
    }
  }
  if (els.profileAlternateEmail) {
    els.profileAlternateEmail.value = authState.user.alternate_email || '';
    els.profileAlternateEmail.disabled = !authState.user.primary_login_verified;
  }
  if (els.profilePhotoInput) {
    els.profilePhotoInput.disabled = !isProfileEditableRole;
  }
  if (els.profilePhotoWrap) {
    setHidden(els.profilePhotoWrap, !isProfileEditableRole);
  }
  const activePhoto = isFaculty
    ? (state.facultyProfile.profilePhotoDataUrl || state.facultyProfile.pendingProfilePhotoDataUrl || '')
    : isStudent
      ? (state.student.profilePhotoDataUrl || state.student.pendingProfilePhotoDataUrl || '')
      : '';
  renderProfilePhotoPreview(activePhoto);
  if (els.saveAlternateEmailBtn) {
    els.saveAlternateEmailBtn.disabled = !authState.user.primary_login_verified;
  }
  if (els.saveProfilePhotoBtn) {
    els.saveProfilePhotoBtn.disabled = !isProfileEditableRole;
    setHidden(els.saveProfilePhotoBtn, !isProfileEditableRole);
  }
  if (!isStudent) {
    setProfileTab('details');
  }
  renderAlternateEmailStatus();
  renderEnrollmentSummary();
  renderProfileStatusByRole();

  if (requiresStudentProfileSetup()) {
    if (state.student.profileSetupRequired) {
      openProfileModal({ required: true });
    }
  } else if (els.profileModal && state.student.profileSetupRequired) {
    state.student.profileSetupRequired = false;
    els.profileModal.classList.add('hidden');
  }
  if (requiresFacultyProfileSetup()) {
    if (state.facultyProfile.profileSetupRequired) {
      openProfileModal({ required: true });
    }
  } else if (els.profileModal && state.facultyProfile.profileSetupRequired) {
    state.facultyProfile.profileSetupRequired = false;
    els.profileModal.classList.add('hidden');
  }

  if (requiresStudentEnrollmentSetup()) {
    if (state.student.enrollmentRequired) {
      openEnrollmentModal({ required: true });
    }
  } else if (els.enrollmentModal && state.student.enrollmentRequired) {
    state.student.enrollmentRequired = false;
    els.enrollmentModal.classList.add('hidden');
    stopEnrollmentCameraStream();
  }
}

function persistToken(token) {
  authState.token = token || '';
}

function clearSessionWatchdogTimers() {
  if (sessionIdleTimer) {
    window.clearTimeout(sessionIdleTimer);
    sessionIdleTimer = null;
  }
  if (sessionMaxTimer) {
    window.clearTimeout(sessionMaxTimer);
    sessionMaxTimer = null;
  }
}

function scheduleIdleLogoutTimer() {
  if (!authState.user) {
    return;
  }
  if (sessionIdleTimer) {
    window.clearTimeout(sessionIdleTimer);
  }
  sessionIdleTimer = window.setTimeout(async () => {
    if (!authState.user) {
      return;
    }
    await logout('Session ended after 15 minutes of inactivity. Please login again.');
  }, SESSION_IDLE_LOGOUT_MS);
}

function scheduleMaxLogoutTimer() {
  if (!authState.user) {
    return;
  }
  if (sessionMaxTimer) {
    window.clearTimeout(sessionMaxTimer);
  }
  sessionMaxTimer = window.setTimeout(async () => {
    if (!authState.user) {
      return;
    }
    await logout('Session ended after 30 minutes. Please login again.');
  }, SESSION_MAX_LOGOUT_MS);
}

function markSessionActivity() {
  if (!authState.user) {
    return;
  }
  authState.lastActivityAtMs = Date.now();
  scheduleIdleLogoutTimer();
}

function bindSessionActivityWatchdog() {
  if (sessionActivityBound) {
    return;
  }
  const activityEvents = ['pointerdown', 'keydown', 'mousemove', 'scroll', 'touchstart'];
  const onActivity = () => {
    if (!authState.user) {
      return;
    }
    const now = Date.now();
    if ((now - lastSessionActivityPingMs) < 1000) {
      return;
    }
    lastSessionActivityPingMs = now;
    markSessionActivity();
  };
  for (const eventName of activityEvents) {
    document.addEventListener(eventName, onActivity, { passive: true });
  }
  sessionActivityBound = true;
}

function startSessionWatchdog() {
  clearSessionWatchdogTimers();
  if (!authState.user) {
    return;
  }
  authState.sessionStartedAtMs = Date.now();
  markSessionActivity();
  scheduleMaxLogoutTimer();
}

function resetStudentProfileState() {
  state.student.name = '';
  state.student.registrationNumber = '';
  state.student.section = '';
  state.student.sectionUpdatedAt = null;
  state.student.profilePhotoDataUrl = '';
  state.student.profilePhotoLockedUntil = null;
  state.student.profilePhotoCanUpdateNow = true;
  state.student.profilePhotoLockDaysRemaining = 0;
  state.student.sectionCanUpdateNow = true;
  state.student.sectionLockedUntil = null;
  state.student.sectionLockMinutesRemaining = 0;
  state.student.sectionChangeRequiresFacultyApproval = false;
  state.student.profileLoaded = false;
  state.student.pendingProfilePhotoDataUrl = '';
  state.student.profileSetupRequired = false;
  state.student.enrollmentLoaded = false;
  state.student.hasEnrollmentVideo = false;
  state.student.enrollmentCanUpdateNow = true;
  state.student.enrollmentLockedUntil = null;
  state.student.enrollmentLockDaysRemaining = 0;
  state.student.enrollmentUpdatedAt = null;
  state.student.enrollmentRequired = false;
  state.student.enrollmentFrames = [];
  state.student.enrollmentCaptureRunning = false;
  state.student.autoRefreshBusy = false;
  state.student.demoAttendanceEnabled = false;
  state.student.selfieDataUrl = '';
  state.student.attendanceAggregate = null;
  state.student.attendanceHistory = [];
  state.student.attendanceHistoryByCourse = {};
  state.student.saarthiStatus = null;
  state.student.saarthiMessages = [];
  state.student.saarthiSending = false;
  state.student.saarthiResetting = false;
  state.student.saarthiUiMessage = 'Saarthi session will appear here.';
  state.student.saarthiUiState = 'neutral';
  state.student.attendanceDetailsCourseKey = '';
  state.student.attendanceRectificationRequests = [];
  state.student.attendanceRectificationByKey = {};
  state.student.attendanceRectificationTarget = null;
  state.student.attendanceRectificationProofDataUrl = '';
  renderSaarthiPanel();
}

function resetFacultyProfileState() {
  state.facultyProfile.name = '';
  state.facultyProfile.facultyIdentifier = '';
  state.facultyProfile.section = '';
  state.facultyProfile.sectionUpdatedAt = null;
  state.facultyProfile.profilePhotoDataUrl = '';
  state.facultyProfile.profilePhotoLockedUntil = null;
  state.facultyProfile.profilePhotoCanUpdateNow = true;
  state.facultyProfile.profilePhotoLockDaysRemaining = 0;
  state.facultyProfile.sectionCanUpdateNow = true;
  state.facultyProfile.sectionLockedUntil = null;
  state.facultyProfile.sectionLockMinutesRemaining = 0;
  state.facultyProfile.profileLoaded = false;
  state.facultyProfile.pendingProfilePhotoDataUrl = '';
  state.facultyProfile.profileSetupRequired = false;
}

function setSession(token, user) {
  stopFoodLocationMonitoring();
  stopFoodDemandLiveTicker();
  authState.token = token;
  authState.user = user;
  state.ui.activeModule = defaultModuleForRole(user?.role);
  state.food.orderDate = todayISO();
  state.food.slotHintsById = {};
  state.food.slotHintsDate = '';
  state.food.orderHistory = [];
  state.food.ordersTab = 'current';
  state.food.paymentRecovery = [];
  state.food.expandedOrderGroups.clear();
  state.food.liveFeedByOrderId.clear();
  state.food.liveFeedInitialized = false;
  state.food.freshnessDigest = '';
  state.food.lastOrdersSyncAtMs = 0;
  state.food.lastOrdersChangeAtMs = 0;
  state.food.syncPulseUntilMs = 0;
  state.food.ratingBusyOrderIds.clear();
  state.food.deliveryConfirmBusyOrderIds.clear();
  state.food.recoveryBusyRefs.clear();
  state.food.demandDigest = '';
  state.food.lastDemandSyncAtMs = 0;
  state.food.demandSyncPulseUntilMs = 0;
  state.food.demandSelectedSlotId = 0;
  state.food.demandLive.windowMinutes = 2;
  state.food.demandLive.activeOrders = 0;
  state.food.demandLive.ordersLastWindow = 0;
  state.food.demandLive.statusUpdatesLastWindow = 0;
  state.food.demandLive.paymentEventsLastWindow = 0;
  state.food.demandLive.hottestSlotLabel = '';
  state.food.demandLive.hottestSlotOrders = 0;
  state.food.demandLive.pulsesBySlotId = {};
  state.food.demandLive.pulses = [];
  state.food.demandLive.syncedAtMs = 0;
  state.food.demandLive.digest = '';
  state.food.demandLive.pulseUntilMs = 0;
  state.food.selectedShopId = '';
  state.food.menuByShop = {};
  state.food.cart.shopId = '';
  state.food.cart.items = [];
  state.food.cartUpdatedAt = '';
  setFoodCartModalTab('cart');
  state.food.checkoutPreviewOpen = false;
  state.food.checkoutDeliveryPoint = '';
  state.food.location.requestedOnce = false;
  state.food.location.autoPromptAttempted = false;
  state.food.location.checking = false;
  state.food.location.allowed = false;
  state.food.location.verified = false;
  state.food.location.monitoring = false;
  state.food.location.watchId = null;
  state.food.location.monitorBusy = false;
  state.food.location.latitude = null;
  state.food.location.longitude = null;
  state.food.location.accuracyM = null;
  state.food.location.lastVerifiedAtMs = 0;
  state.food.location.message = '';
  if (foodOrdersPulseTimer) {
    window.clearTimeout(foodOrdersPulseTimer);
    foodOrdersPulseTimer = null;
  }
  if (els.foodOrdersPanel) {
    els.foodOrdersPanel.classList.remove('is-sync-pulse');
  }
  renderFoodFreshnessIndicators();
  renderFoodDemandLiveSignal({ animate: false });
  state.ui.chotuOpen = false;
  state.ui.supportDeskOpen = false;
  state.ui.verlynOpen = false;
  state.remedial.eligibleCourses = [];
  state.remedial.classes = [];
  state.remedial.selectedClassId = null;
  state.remedial.selectedClassAttendance = [];
  state.remedial.selectedClassAttendanceSections = [];
  state.remedial.selectedClassAttendanceAllStudents = [];
  state.remedial.selectedAttendanceModalSection = '';
  state.remedial.selectedAttendanceModalCourseKey = '';
  state.remedial.messages = [];
  state.remedial.attendanceLedger = [];
  state.remedial.attendanceLedgerByCourse = {};
  state.remedial.validatedClass = null;
  state.remedial.markedClassId = null;
  state.remedial.markedOnlineLink = '';
  state.remedial.demoBypassLeadTime = false;
  state.supportDesk.contacts = [];
  state.supportDesk.threads = [];
  state.supportDesk.messages = [];
  state.supportDesk.selectedCounterpartyId = null;
  state.supportDesk.selectedCategory = 'Attendance';
  state.supportDesk.selectedCounterpartyName = '';
  state.supportDesk.selectedCounterpartySection = '';
  state.supportDesk.unreadTotal = 0;
  state.rms.dashboard = null;
  state.rms.selectedCategory = 'all';
  state.rms.selectedStatus = 'all';
  state.rms.selectedStudent = null;
  state.rms.selectedThread = null;
  state.rms.threadAction = 'approve';
  state.rms.attendanceContext = null;
  state.rms.attendanceSelectedCourseCode = '';
  state.rms.attendanceSelectedScheduleId = null;
  state.rms.attendanceUpdate = null;
  state.admin.telemetryHistory = [];
  state.admin.summary = null;
  state.admin.alerts = [];
  state.admin.insights = null;
  state.admin.identityCases = [];
  state.admin.lastUpdatedAt = null;
  state.admin.staleAfterSeconds = 60;
  state.admin.copilotAuditLoadedAtMs = 0;
  state.admin.copilotAuditBusy = false;
  state.admin.copilotAuditQueued = false;
  if (els.adminSearchResults) {
    els.adminSearchResults.innerHTML = '';
  }
  if (els.adminGradeHistoryWrap) {
    els.adminGradeHistoryWrap.innerHTML = '';
  }
  setAdminSearchStatus('Use registration number or faculty identifier for exact production lookup.');
  setAdminGradeStatus('Grade changes are audit logged and can be fetched by registration number.');
  if (els.rmsThreadAction) {
    els.rmsThreadAction.value = state.rms.threadAction;
  }
  if (els.rmsThreadNote) {
    els.rmsThreadNote.value = '';
  }
  if (els.rmsThreadScheduledFor) {
    els.rmsThreadScheduledFor.value = '';
  }
  if (els.rmsAttendanceRegistration) {
    els.rmsAttendanceRegistration.value = '';
  }
  if (els.rmsAttendanceStudentSummary) {
    els.rmsAttendanceStudentSummary.textContent = 'Search by registration number to load student day-wise classes.';
  }
  if (els.rmsAttendanceSubjectSelect) {
    els.rmsAttendanceSubjectSelect.innerHTML = '<option value="">Select subject</option>';
    els.rmsAttendanceSubjectSelect.value = '';
  }
  if (els.rmsAttendanceSlotSelect) {
    els.rmsAttendanceSlotSelect.innerHTML = '<option value="">Select time slot</option>';
    els.rmsAttendanceSlotSelect.value = '';
  }
  if (els.rmsAttendanceDate) {
    els.rmsAttendanceDate.value = todayISO();
  }
  if (els.rmsAttendanceCurrentStatus) {
    els.rmsAttendanceCurrentStatus.value = 'Not marked';
  }
  if (els.rmsAttendanceStatus) {
    els.rmsAttendanceStatus.value = 'present';
  }
  if (els.rmsAttendanceNote) {
    els.rmsAttendanceNote.value = '';
  }
  setRmsAttendanceStatus('Search by registration number, choose subject and slot, then apply attendance status.');
  syncRmsThreadActionForm();
  renderRmsSelectedThreadSummary(null);
  renderRmsAttendanceStudentSummary(null);
  renderRmsAttendanceSubjectOptions(null);
  renderRmsAttendanceResult(null);
  state.studentMessages = [];
  resetStudentProfileState();
  resetFacultyProfileState();
  state.student.weekStart = '';
  state.student.viewDate = '';
  state.student.timetable = [];
  state.student.timetableCache = {};
  state.student.timetableNetworkRequests.clear();
  state.student.timetablePrefetching.clear();
  state.student.timetableRequestToken = 0;
  if (user?.role === 'student') {
    state.student.minTimetableDate = STUDENT_TIMETABLE_START_DATE;
    state.student.kpiTimetable = [];
    state.student.kpiScheduleId = null;
    state.student.kpiRefreshInFlight = false;
  }
  applyTheme(getInitialTheme(user?.email || ''), { persist: false, userEmail: user?.email || '' });
  persistToken(token);
  updateAuthBadges();
  const hashModule = moduleFromHash();
  setActiveModule(hashModule || defaultModuleForRole(user?.role), { updateHash: true });
  renderProfileSecurity();
  closeAccountDropdown();
  closeAuthOverlay();

  if (authState.user?.role === 'student') {
    state.student.profileLoaded = false;
    state.student.viewDate = todayISO();
    if (els.weekStartDate) {
      els.weekStartDate.value = state.student.viewDate;
    }
    startStudentRealtimeTicker();
  } else {
    stopStudentRealtimeTicker();
  }
  startModuleRealtimeTicker();
  syncFoodDemandLiveTicker();
  startSessionWatchdog();
  void syncRealtimeEventBus();
}

function clearSession() {
  stopFoodLocationMonitoring();
  stopFoodDemandLiveTicker();
  stopPresentationTour({ silent: true });
  authState.token = '';
  authState.user = null;
  authState.pendingEmail = '';
  authState.otpCooldownUntilMs = 0;
  authState.otpRequestInFlight = false;
  authState.mfaSetupRequired = false;
  authState.mfaEnrollInFlight = false;
  authState.mfaActivateInFlight = false;
  authState.mfaSetup = null;
  authState.forgotOtpCooldownUntilMs = 0;
  authState.forgotOtpRequestInFlight = false;
  authState.forgotResetToken = '';
  authState.forgotResetTokenExpiresAt = '';
  authState.sessionStartedAtMs = 0;
  authState.lastActivityAtMs = 0;
  stopOtpCooldownTicker();
  stopForgotOtpCooldownTicker();
  clearSessionWatchdogTimers();
  hideOtpPopup();
  setMfaSetupModal(false);
  resetMfaSetupUiState();
  setAuthMfaInputVisible(false);
  applyTheme(getInitialTheme(''), { persist: false, userEmail: '' });
  persistToken('');
  state.ui.activeModule = 'attendance';
  state.student.selectedScheduleId = null;
  state.student.weekStart = '';
  state.student.minTimetableDate = STUDENT_TIMETABLE_START_DATE;
  state.student.viewDate = '';
  state.student.timetable = [];
  state.student.kpiTimetable = [];
  state.student.timetableCache = {};
  state.student.timetableNetworkRequests.clear();
  state.student.timetablePrefetching.clear();
  state.student.timetableRequestToken = 0;
  state.student.kpiRefreshInFlight = false;
  state.student.kpiScheduleId = null;
  resetStudentProfileState();
  resetFacultyProfileState();
  state.faculty.selectedScheduleId = null;
  state.faculty.selectedSubmissionIds.clear();
  state.faculty.rectificationRequests = [];
  closeAttendanceRectificationModal();
  state.camera.liveVerificationActive = false;
  state.camera.liveSessionToken += 1;
  state.food.items = [];
  state.food.slots = [];
  state.food.slotHintsById = {};
  state.food.slotHintsDate = '';
  state.food.orders = [];
  state.food.orderHistory = [];
  state.food.ordersTab = 'current';
  state.food.paymentRecovery = [];
  state.food.expandedOrderGroups.clear();
  state.food.liveFeedByOrderId.clear();
  state.food.liveFeedInitialized = false;
  state.food.freshnessDigest = '';
  state.food.lastOrdersSyncAtMs = 0;
  state.food.lastOrdersChangeAtMs = 0;
  state.food.syncPulseUntilMs = 0;
  state.food.ratingBusyOrderIds.clear();
  state.food.deliveryConfirmBusyOrderIds.clear();
  state.food.recoveryBusyRefs.clear();
  state.food.demandDigest = '';
  state.food.lastDemandSyncAtMs = 0;
  state.food.demandSyncPulseUntilMs = 0;
  state.food.demandSelectedSlotId = 0;
  state.food.demandLive.windowMinutes = 2;
  state.food.demandLive.activeOrders = 0;
  state.food.demandLive.ordersLastWindow = 0;
  state.food.demandLive.statusUpdatesLastWindow = 0;
  state.food.demandLive.paymentEventsLastWindow = 0;
  state.food.demandLive.hottestSlotLabel = '';
  state.food.demandLive.hottestSlotOrders = 0;
  state.food.demandLive.pulsesBySlotId = {};
  state.food.demandLive.pulses = [];
  state.food.demandLive.syncedAtMs = 0;
  state.food.demandLive.digest = '';
  state.food.demandLive.pulseUntilMs = 0;
  state.food.orderDate = '';
  state.food.shops = [];
  state.food.menuByShop = {};
  state.food.selectedShopId = '';
  state.food.cart.shopId = '';
  state.food.cart.items = [];
  state.food.cartUpdatedAt = '';
  setFoodCartModalTab('cart');
  state.food.location.requestedOnce = false;
  state.food.location.autoPromptAttempted = false;
  state.food.location.checking = false;
  state.food.location.allowed = false;
  state.food.location.verified = false;
  state.food.location.monitoring = false;
  state.food.location.watchId = null;
  if (foodOrdersPulseTimer) {
    window.clearTimeout(foodOrdersPulseTimer);
    foodOrdersPulseTimer = null;
  }
  if (els.foodOrdersPanel) {
    els.foodOrdersPanel.classList.remove('is-sync-pulse');
  }
  renderFoodFreshnessIndicators();
  renderFoodDemandLiveSignal({ animate: false });
  state.food.location.monitorBusy = false;
  state.food.location.latitude = null;
  state.food.location.longitude = null;
  state.food.location.accuracyM = null;
  state.food.location.lastVerifiedAtMs = 0;
  state.food.location.message = '';
  state.ui.chotuOpen = false;
  state.ui.supportDeskOpen = false;
  state.ui.verlynOpen = false;
  state.remedial.eligibleCourses = [];
  state.remedial.classes = [];
  state.remedial.selectedClassId = null;
  state.remedial.selectedClassAttendance = [];
  state.remedial.selectedClassAttendanceSections = [];
  state.remedial.selectedClassAttendanceAllStudents = [];
  state.remedial.selectedAttendanceModalSection = '';
  state.remedial.selectedAttendanceModalCourseKey = '';
  state.remedial.messages = [];
  state.remedial.attendanceLedger = [];
  state.remedial.attendanceLedgerByCourse = {};
  state.remedial.validatedClass = null;
  state.remedial.markedClassId = null;
  state.remedial.markedOnlineLink = '';
  state.remedial.demoBypassLeadTime = false;
  state.supportDesk.contacts = [];
  state.supportDesk.threads = [];
  state.supportDesk.messages = [];
  state.supportDesk.selectedCounterpartyId = null;
  state.supportDesk.selectedCategory = 'Attendance';
  state.supportDesk.selectedCounterpartyName = '';
  state.supportDesk.selectedCounterpartySection = '';
  state.supportDesk.unreadTotal = 0;
  state.rms.dashboard = null;
  state.rms.selectedCategory = 'all';
  state.rms.selectedStatus = 'all';
  state.rms.selectedStudent = null;
  state.rms.selectedThread = null;
  state.rms.threadAction = 'approve';
  state.rms.attendanceContext = null;
  state.rms.attendanceSelectedCourseCode = '';
  state.rms.attendanceSelectedScheduleId = null;
  state.rms.attendanceUpdate = null;
  if (els.adminSearchResults) {
    els.adminSearchResults.innerHTML = '';
  }
  if (els.adminGradeHistoryWrap) {
    els.adminGradeHistoryWrap.innerHTML = '';
  }
  setAdminSearchStatus('Use registration number or faculty identifier for exact production lookup.');
  setAdminGradeStatus('Grade changes are audit logged and can be fetched by registration number.');
  if (els.rmsThreadAction) {
    els.rmsThreadAction.value = state.rms.threadAction;
  }
  if (els.rmsThreadNote) {
    els.rmsThreadNote.value = '';
  }
  if (els.rmsThreadScheduledFor) {
    els.rmsThreadScheduledFor.value = '';
  }
  if (els.rmsAttendanceRegistration) {
    els.rmsAttendanceRegistration.value = '';
  }
  if (els.rmsAttendanceStudentSummary) {
    els.rmsAttendanceStudentSummary.textContent = 'Search by registration number to load student day-wise classes.';
  }
  if (els.rmsAttendanceSubjectSelect) {
    els.rmsAttendanceSubjectSelect.innerHTML = '<option value="">Select subject</option>';
    els.rmsAttendanceSubjectSelect.value = '';
  }
  if (els.rmsAttendanceSlotSelect) {
    els.rmsAttendanceSlotSelect.innerHTML = '<option value="">Select time slot</option>';
    els.rmsAttendanceSlotSelect.value = '';
  }
  if (els.rmsAttendanceDate) {
    els.rmsAttendanceDate.value = todayISO();
  }
  if (els.rmsAttendanceCurrentStatus) {
    els.rmsAttendanceCurrentStatus.value = 'Not marked';
  }
  if (els.rmsAttendanceStatus) {
    els.rmsAttendanceStatus.value = 'present';
  }
  if (els.rmsAttendanceNote) {
    els.rmsAttendanceNote.value = '';
  }
  setRmsAttendanceStatus('Search by registration number, choose subject and slot, then apply attendance status.');
  syncRmsThreadActionForm();
  renderRmsSelectedThreadSummary(null);
  renderRmsAttendanceStudentSummary(null);
  renderRmsAttendanceSubjectOptions(null);
  renderRmsAttendanceResult(null);
  state.studentMessages = [];
  updateAuthBadges();
  applyRoleUI();
  setTopNavActive('attendance');
  if (window.history?.replaceState) {
    window.history.replaceState(null, '', window.location.pathname + window.location.search);
  } else {
    window.location.hash = '';
  }
  renderOtpCooldown();
  renderForgotOtpCooldown();
  setForgotPasswordPanel(false);
  resetForgotPasswordState({ clearFields: true });
  renderProfileSecurity();
  if (els.profileModal) {
    els.profileModal.classList.add('hidden');
  }
  if (els.enrollmentModal) {
    els.enrollmentModal.classList.add('hidden');
  }
  if (els.foodShopModal) {
    els.foodShopModal.classList.add('hidden');
  }
  setVerlynOpen(false);
  setChotuOpen(false);
  setSupportDeskOpen(false);
  stopEnrollmentCameraStream();
  stopStudentRealtimeTicker();
  stopStudentTimetableStatusTicker();
  stopModuleRealtimeTicker();
  stopFoodDemandLiveTicker();
  stopRemedialLiveTicker();
  stopSupportDeskLiveTicker();
  stopRealtimeEventBus();
}

async function api(path, options = {}) {
  const { skipAuth = false, timeoutMs = 30000, ...requestOptions } = options;
  const method = String(requestOptions.method || 'GET').toUpperCase();
  const headers = {
    'Content-Type': 'application/json',
    ...(requestOptions.headers || {}),
  };

  if (!skipAuth && authState.token) {
    headers.Authorization = `Bearer ${authState.token}`;
  }

  const controller = requestOptions.signal ? null : new AbortController();
  const signal = requestOptions.signal || controller?.signal;
  const timeoutHandle = controller
    ? window.setTimeout(() => controller.abort(), Math.max(5000, Number(timeoutMs) || 30000))
    : null;

  let response;
  try {
    response = await fetch(path, {
      ...requestOptions,
      headers,
      signal,
      credentials: requestOptions.credentials || 'same-origin',
      cache: requestOptions.cache || (method === 'GET' || method === 'HEAD' ? 'no-store' : undefined),
    });
  } catch (err) {
    if (err?.name === 'AbortError') {
      const seconds = Math.max(5, Math.round((Math.max(5000, Number(timeoutMs) || 30000)) / 1000));
      const timeoutError = new Error(`Request timed out after ${seconds}s. Please retry.`);
      timeoutError.status = 408;
      throw timeoutError;
    }
    throw err;
  } finally {
    if (timeoutHandle) {
      window.clearTimeout(timeoutHandle);
    }
  }

  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || JSON.stringify(payload);
    } catch (_) {
      // Ignore non-JSON error bodies.
    }

    if (!skipAuth && response.status === 401) {
      clearSession();
      openAuthOverlay('Session expired. Please login again.');
    }
    if (!skipAuth && response.status === 428 && isMfaEnrollmentRequiredMessage(detail)) {
      void maybePromptPrivilegedMfaSetup(detail);
    }
    const error = new Error(detail);
    error.status = response.status;
    const retryAfter = response.headers.get('Retry-After');
    if (retryAfter) {
      const parsed = Number(retryAfter);
      if (Number.isFinite(parsed) && parsed > 0) {
        error.retryAfterSeconds = parsed;
      }
    }
    throw error;
  }

  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

async function apiWithTimeout(path, options = {}, timeoutMs = 9000, timeoutMessage = 'Request timed out') {
  const controller = new AbortController();
  const timerId = window.setTimeout(() => controller.abort(), Math.max(1000, Number(timeoutMs) || 9000));
  try {
    return await api(path, {
      ...options,
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new Error(timeoutMessage);
    }
    throw error;
  } finally {
    window.clearTimeout(timerId);
  }
}

function parseISODateLocal(inputDate = new Date()) {
  if (inputDate instanceof Date) {
    return new Date(inputDate.getFullYear(), inputDate.getMonth(), inputDate.getDate(), 12, 0, 0, 0);
  }

  if (typeof inputDate === 'string') {
    const match = inputDate.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (match) {
      const [, year, month, day] = match;
      return new Date(Number(year), Number(month) - 1, Number(day), 12, 0, 0, 0);
    }
  }

  const parsed = new Date(inputDate);
  if (Number.isNaN(parsed.getTime())) {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate(), 12, 0, 0, 0);
  }
  return new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate(), 12, 0, 0, 0);
}

function toISODateLocal(inputDate = new Date()) {
  const date = parseISODateLocal(inputDate);
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function shiftISODate(inputDate, deltaDays) {
  const date = parseISODateLocal(inputDate);
  date.setDate(date.getDate() + deltaDays);
  return toISODateLocal(date);
}

function todayISO() {
  return toISODateLocal(new Date());
}

function weekStartISO(inputDate = new Date()) {
  const date = parseISODateLocal(inputDate);
  const weekday = date.getDay();
  const distance = weekday === 0 ? 6 : weekday - 1;
  date.setDate(date.getDate() - distance);
  return toISODateLocal(date);
}

function isoDateMax(leftIso, rightIso) {
  const left = String(leftIso || '');
  const right = String(rightIso || '');
  if (!left) {
    return right;
  }
  if (!right) {
    return left;
  }
  return left >= right ? left : right;
}

function clampStudentViewDate(inputIsoDate) {
  const requested = String(inputIsoDate || todayISO());
  const minDate = String(state.student.minTimetableDate || STUDENT_TIMETABLE_START_DATE);
  return isoDateMax(requested, minDate);
}

function animateNumber(el, target) {
  if (!el) {
    return;
  }
  const start = Number(el.textContent.replace(/[^0-9.-]/g, '')) || 0;
  const duration = 450;
  const startTime = performance.now();

  function tick(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = Math.round(start + (target - start) * eased);
    el.textContent = String(value);
    if (progress < 1) {
      requestAnimationFrame(tick);
    }
  }

  requestAnimationFrame(tick);
}

function updateMetrics() {
  for (const [elKey, dataKey] of NUMERIC_METRICS) {
    animateNumber(els[elKey], state.overview[dataKey] || 0);
  }
}

function renderAttendanceDonut() {
  if (!els.attendanceDonut) {
    return;
  }
  const summary = state.admin?.summary || null;
  const hasLiveSummary = summary
    && Number.isFinite(Number(summary.active_today))
    && Number.isFinite(Number(summary.present_today))
    && Number.isFinite(Number(summary.absent_today));
  const enrolled = hasLiveSummary
    ? Math.max(0, Number(summary.active_today || 0))
    : (Array.isArray(state.attendanceSummary) ? state.attendanceSummary.length : 0);
  const absent = hasLiveSummary
    ? Math.max(0, Number(summary.absent_today || 0))
    : (Array.isArray(state.absentees) ? state.absentees.length : 0);
  const present = hasLiveSummary
    ? Math.max(0, Number(summary.present_today || 0))
    : Math.max(enrolled - absent, 0);
  const percent = enrolled ? Math.round((present / enrolled) * 100) : 0;

  els.attendanceDonut.style.background = `conic-gradient(var(--good) 0% ${percent}%, rgba(140, 181, 218, 0.18) ${percent}% 100%)`;
  els.attendanceRate.textContent = `${percent}%`;
  els.presentCount.textContent = String(present);
  els.absentCount.textContent = String(absent);
  els.enrolledCount.textContent = String(enrolled);

  const absentPercent = enrolled ? Math.round((absent / enrolled) * 100) : 0;
  const healthScore = clampPercent(percent - absentPercent * 0.45);

  if (els.attendancePresentPercent) {
    els.attendancePresentPercent.textContent = `${percent}%`;
  }
  if (els.attendancePresentFill) {
    els.attendancePresentFill.style.setProperty('--w', String(Math.max(5, percent)));
    els.attendancePresentFill.dataset.state = percent >= 75 ? 'good' : (percent >= 45 ? 'mid' : 'warn');
  }
  if (els.attendanceAbsentPercent) {
    els.attendanceAbsentPercent.textContent = `${absentPercent}%`;
  }
  if (els.attendanceAbsentFill) {
    els.attendanceAbsentFill.style.setProperty('--w', String(Math.max(4, absentPercent)));
    els.attendanceAbsentFill.dataset.state = absentPercent <= 20 ? 'good' : (absentPercent <= 45 ? 'mid' : 'warn');
  }
  if (els.attendanceHealthScore) {
    els.attendanceHealthScore.textContent = `${Math.round(healthScore)}%`;
  }
  if (els.attendanceHealthFill) {
    els.attendanceHealthFill.style.setProperty('--w', String(Math.max(5, Math.round(healthScore))));
    els.attendanceHealthFill.dataset.state = healthScore >= 70 ? 'good' : (healthScore >= 45 ? 'mid' : 'warn');
  }
  if (els.attendanceHealthNote) {
    if (!enrolled) {
      els.attendanceHealthNote.textContent = 'Awaiting attendance records.';
    } else if (hasLiveSummary && Number.isFinite(Number(summary.data_quality_score))) {
      const quality = Math.round(Number(summary.data_quality_score || 0));
      els.attendanceHealthNote.textContent = `Live feed quality ${quality}% • refreshed from backend telemetry`;
    } else if (percent >= 90) {
      els.attendanceHealthNote.textContent = 'Attendance signal is stable and healthy.';
    } else if (percent >= 70) {
      els.attendanceHealthNote.textContent = 'Attendance is moderate; monitor absence clusters.';
    } else {
      els.attendanceHealthNote.textContent = 'Low attendance detected; intervention recommended.';
    }
  }
}

function renderAbsentees() {
  if (!els.absenteesWrap) {
    return;
  }
  els.absenteesWrap.innerHTML = '';

  if (!state.absentees.length) {
    const row = document.createElement('div');
    row.className = 'list-item good';
    row.textContent = 'No absentees found for selected course/date.';
    els.absenteesWrap.appendChild(row);
    return;
  }

  for (const item of state.absentees) {
    const row = document.createElement('div');
    row.className = 'list-item warn';
    row.innerHTML = `<span>${item.name}</span><span>${item.email}</span>`;
    els.absenteesWrap.appendChild(row);
  }
}

function buildFoodDemandDigest(rows) {
  const sourceRows = Array.isArray(rows) ? rows : [];
  return sourceRows
    .map((slot) => [
      Number(slot?.slot_id || 0),
      Number(slot?.orders || 0),
      Number(slot?.capacity || 0),
      Number(slot?.utilization_percent || 0).toFixed(2),
    ].join(':'))
    .sort()
    .join('|');
}

function hasFoodDemandChanged(previousRows, nextRows) {
  return buildFoodDemandDigest(previousRows) !== buildFoodDemandDigest(nextRows);
}

function buildFoodDemandLiveDigest(payload) {
  if (!payload || typeof payload !== 'object') {
    return '';
  }
  const pulses = Array.isArray(payload.pulses) ? payload.pulses : [];
  const pulseDigest = pulses
    .map((pulse) => [
      Number(pulse?.slot_id || 0),
      Number(pulse?.event_count || 0),
      Number(pulse?.created_count || 0),
      Number(pulse?.status_count || 0),
      Number(pulse?.payment_count || 0),
    ].join(':'))
    .sort()
    .join('|');
  return [
    Number(payload?.window_minutes || 0),
    Number(payload?.active_orders || 0),
    Number(payload?.orders_last_window || 0),
    Number(payload?.status_updates_last_window || 0),
    Number(payload?.payment_events_last_window || 0),
    String(payload?.hottest_slot_label || ''),
    Number(payload?.hottest_slot_orders || 0),
    pulseDigest,
  ].join('~');
}

function normalizeFoodDemandLivePayload(payload) {
  const source = (payload && typeof payload === 'object') ? payload : {};
  const rawPulses = Array.isArray(source.pulses) ? source.pulses : [];
  const pulses = rawPulses
    .map((pulse) => ({
      slot_id: Number(pulse?.slot_id || 0),
      slot_label: String(pulse?.slot_label || '').trim(),
      event_count: Math.max(0, Number(pulse?.event_count || 0)),
      created_count: Math.max(0, Number(pulse?.created_count || 0)),
      status_count: Math.max(0, Number(pulse?.status_count || 0)),
      payment_count: Math.max(0, Number(pulse?.payment_count || 0)),
    }))
    .filter((pulse) => pulse.slot_id > 0 && pulse.event_count > 0)
    .sort((a, b) => b.event_count - a.event_count);

  const pulsesBySlotId = {};
  for (const pulse of pulses) {
    pulsesBySlotId[String(pulse.slot_id)] = pulse;
  }

  const syncedAtMs = Date.parse(String(source.synced_at || ''));
  return {
    windowMinutes: Math.max(1, Math.min(15, Number(source.window_minutes || 2))),
    activeOrders: Math.max(0, Number(source.active_orders || 0)),
    ordersLastWindow: Math.max(0, Number(source.orders_last_window || 0)),
    statusUpdatesLastWindow: Math.max(0, Number(source.status_updates_last_window || 0)),
    paymentEventsLastWindow: Math.max(0, Number(source.payment_events_last_window || 0)),
    hottestSlotLabel: String(source.hottest_slot_label || '').trim(),
    hottestSlotOrders: Math.max(0, Number(source.hottest_slot_orders || 0)),
    pulsesBySlotId,
    pulses,
    syncedAtMs: Number.isFinite(syncedAtMs) ? syncedAtMs : Date.now(),
    digest: buildFoodDemandLiveDigest(source),
  };
}

function pulseFoodDemandLiveNode(element, className = 'is-live-updated', durationMs = 1100) {
  if (!element) {
    return;
  }
  element.classList.remove(className);
  // Restart animation when updates land frequently.
  // eslint-disable-next-line no-unused-expressions
  element.offsetWidth;
  element.classList.add(className);
  if (element._pulseClassTimer) {
    window.clearTimeout(element._pulseClassTimer);
  }
  element._pulseClassTimer = window.setTimeout(() => {
    element.classList.remove(className);
    element._pulseClassTimer = null;
  }, durationMs);
}

function parseSlotLabelStartMinutes(label) {
  const match = String(label || '').match(/(\d{1,2}):(\d{2})/);
  if (!match) {
    return Number.POSITIVE_INFINITY;
  }
  return Number(match[1]) * 60 + Number(match[2]);
}

function getFoodDemandRowsInDisplayOrder() {
  const rows = Array.isArray(state.demand) ? state.demand : [];
  if (!rows.length) {
    return [];
  }
  const demandBySlotId = new Map(rows.map((row) => [Number(row?.slot_id || 0), row]));
  const slots = Array.isArray(state.food.slots) ? state.food.slots : [];
  if (slots.length) {
    const orderedSlots = [...slots].sort((a, b) => {
      const aMinutes = toMinutes(a?.start_time || '');
      const bMinutes = toMinutes(b?.start_time || '');
      return aMinutes - bMinutes;
    });
    return orderedSlots.map((slot) => {
      const slotId = Number(slot?.id || 0);
      const demandRow = demandBySlotId.get(slotId) || {};
      const capacity = Number(demandRow?.capacity || slot?.max_orders || 0);
      const orders = Math.max(0, Number(demandRow?.orders || 0));
      const utilization = capacity > 0 ? (orders / capacity) * 100 : Number(demandRow?.utilization_percent || 0);
      return {
        slot_id: slotId,
        slot_label: String(demandRow?.slot_label || slot?.label || `Slot #${slotId}`),
        orders,
        capacity,
        utilization_percent: Math.round(Math.max(0, Math.min(100, utilization)) * 100) / 100,
      };
    });
  }
  return [...rows].sort((a, b) => parseSlotLabelStartMinutes(a?.slot_label) - parseSlotLabelStartMinutes(b?.slot_label));
}

function resolveFoodDemandHotRow(rows) {
  const availableRows = Array.isArray(rows) ? rows : [];
  let bestRow = null;
  let bestOrders = 0;
  let bestUtilization = 0;
  for (const row of availableRows) {
    const slotId = Number(row?.slot_id || 0);
    if (slotId <= 0) {
      continue;
    }
    const orders = Math.max(0, Number(row?.orders || 0));
    const utilization = Math.max(0, Number(row?.utilization_percent || 0));
    if (
      bestRow === null
      || orders > bestOrders
      || (orders === bestOrders && utilization > bestUtilization)
    ) {
      bestRow = row;
      bestOrders = orders;
      bestUtilization = utilization;
    }
  }
  if (!bestRow || bestOrders <= 0) {
    return null;
  }
  return bestRow;
}

function resolveFoodDemandHotSlotId(rows) {
  const availableRows = Array.isArray(rows) ? rows : [];
  const activeSet = new Set(availableRows.map((row) => Number(row?.slot_id || 0)).filter((slotId) => slotId > 0));
  const liveHotId = Number(state.food?.demandLive?.pulses?.[0]?.slot_id || 0);
  if (liveHotId > 0 && activeSet.has(liveHotId)) {
    return liveHotId;
  }
  const hotRow = resolveFoodDemandHotRow(availableRows);
  return Number(hotRow?.slot_id || 0);
}

function resolveFoodDemandSelectedSlotId(rows) {
  const availableRows = Array.isArray(rows) ? rows : [];
  const activeSet = new Set(availableRows.map((row) => Number(row?.slot_id || 0)).filter((slotId) => slotId > 0));
  let selectedId = Number(state.food.demandSelectedSlotId || 0);
  const hotSlotId = resolveFoodDemandHotSlotId(availableRows);

  if (selectedId > 0 && activeSet.has(selectedId)) {
    const selectedRow = availableRows.find((row) => Number(row?.slot_id || 0) === selectedId);
    const selectedOrders = Math.max(0, Number(selectedRow?.orders || 0));
    const hotRow = resolveFoodDemandHotRow(availableRows);
    const hotOrders = Math.max(0, Number(hotRow?.orders || 0));
    if (selectedOrders > 0 || hotOrders <= 0 || selectedId === hotSlotId) {
      return selectedId;
    }
  }

  if (hotSlotId > 0 && activeSet.has(hotSlotId)) {
    state.food.demandSelectedSlotId = hotSlotId;
    return hotSlotId;
  }

  const firstBusy = availableRows.find((row) => Number(row?.orders || 0) > 0);
  selectedId = Number(firstBusy?.slot_id || availableRows[0]?.slot_id || 0);
  state.food.demandSelectedSlotId = selectedId;
  return selectedId;
}

function foodDemandColorBySlot(slotId, fallbackIndex = 0) {
  const palette = FOOD_DEMAND_PIE_COLORS;
  if (!Array.isArray(palette) || !palette.length) {
    return '#2FA8FF';
  }
  const numeric = Number(slotId || 0);
  const index = Number.isFinite(numeric) && numeric > 0
    ? numeric % palette.length
    : Math.max(0, Number(fallbackIndex || 0)) % palette.length;
  return palette[index];
}

function foodDemandPolarPoint(cx, cy, radius, angleDeg) {
  const radians = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(radians),
    y: cy + radius * Math.sin(radians),
  };
}

function buildFoodDemandDonutPath(cx, cy, outerRadius, innerRadius, startDeg, endDeg) {
  const start = foodDemandPolarPoint(cx, cy, outerRadius, startDeg);
  const end = foodDemandPolarPoint(cx, cy, outerRadius, endDeg);
  const innerEnd = foodDemandPolarPoint(cx, cy, innerRadius, endDeg);
  const innerStart = foodDemandPolarPoint(cx, cy, innerRadius, startDeg);
  const largeArcFlag = endDeg - startDeg > 180 ? 1 : 0;
  return [
    `M ${start.x.toFixed(3)} ${start.y.toFixed(3)}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${end.x.toFixed(3)} ${end.y.toFixed(3)}`,
    `L ${innerEnd.x.toFixed(3)} ${innerEnd.y.toFixed(3)}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${innerStart.x.toFixed(3)} ${innerStart.y.toFixed(3)}`,
    'Z',
  ].join(' ');
}

function renderFoodDemandSlotDetail(rows, { animate = false } = {}) {
  if (!els.foodDemandSlotDetail) {
    return;
  }
  const selectedId = resolveFoodDemandSelectedSlotId(rows);
  const selectedRow = Array.isArray(rows)
    ? rows.find((row) => Number(row?.slot_id || 0) === selectedId)
    : null;
  if (!selectedRow) {
    els.foodDemandSlotDetail.textContent = 'No slot demand data for selected date.';
    return;
  }
  const livePulse = state.food?.demandLive?.pulsesBySlotId?.[String(selectedId)] || null;
  const liveEvents = Math.max(0, Number(livePulse?.event_count || 0));
  const createdEvents = Math.max(0, Number(livePulse?.created_count || 0));
  const statusEvents = Math.max(0, Number(livePulse?.status_count || 0));
  const paymentEvents = Math.max(0, Number(livePulse?.payment_count || 0));
  const windowMinutes = Math.max(1, Number(state.food?.demandLive?.windowMinutes || 2));
  const utilization = Math.max(0, Number(selectedRow?.utilization_percent || 0));
  const totalOrders = Math.max(0, rows.reduce((sum, row) => sum + Math.max(0, Number(row?.orders || 0)), 0));
  const sharePercent = totalOrders > 0
    ? (Math.max(0, Number(selectedRow?.orders || 0)) / totalOrders) * 100
    : 0;
  els.foodDemandSlotDetail.innerHTML = `
    <strong>${escapeHtml(String(selectedRow.slot_label || '--'))}</strong>
    <span>${Number(selectedRow.orders || 0)}/${Number(selectedRow.capacity || 0)} orders • ${utilization.toFixed(0)}% utilization • ${sharePercent.toFixed(1)}% share</span>
    <span>${liveEvents} live event(s) in last ${windowMinutes}m • New ${createdEvents} • Status ${statusEvents} • Payment ${paymentEvents}</span>
  `;
  if (animate && liveEvents > 0) {
    pulseFoodDemandLiveNode(els.foodDemandSlotDetail);
  }
}

function renderFoodDemandMinimalChart({ animate = false } = {}) {
  if (!els.foodDemandChartModule) {
    return;
  }
  const rows = getFoodDemandRowsInDisplayOrder();
  els.foodDemandChartModule.innerHTML = '';
  if (!rows.length) {
    const empty = document.createElement('div');
    empty.className = 'list-item';
    empty.textContent = 'No slot demand data for selected date.';
    els.foodDemandChartModule.appendChild(empty);
    if (els.foodDemandSlotDetail) {
      els.foodDemandSlotDetail.textContent = 'No slot selected yet.';
    }
    return;
  }

  const selectedId = resolveFoodDemandSelectedSlotId(rows);
  const layout = document.createElement('div');
  layout.className = 'food-demand-pie-layout';
  const chartWrap = document.createElement('div');
  chartWrap.className = 'food-demand-pie-wrap';
  const legend = document.createElement('div');
  legend.className = 'food-demand-pie-legend';
  const namespace = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(namespace, 'svg');
  svg.setAttribute('viewBox', '0 0 240 240');
  svg.setAttribute('class', 'food-demand-pie-svg');

  const backgroundRing = document.createElementNS(namespace, 'circle');
  backgroundRing.setAttribute('cx', '120');
  backgroundRing.setAttribute('cy', '120');
  backgroundRing.setAttribute('r', '86');
  backgroundRing.setAttribute('fill', 'none');
  backgroundRing.setAttribute('class', 'food-demand-pie-base');
  svg.appendChild(backgroundRing);

  const allPieRows = rows
    .map((row, index) => ({ ...row, _index: index }))
    .filter((row) => Number(row?.slot_id || 0) > 0);
  const ordersTotal = Math.max(0, allPieRows.reduce((sum, row) => sum + Math.max(0, Number(row?.orders || 0)), 0));
  const pieRows = ordersTotal > 0
    ? allPieRows.filter((row) => Math.max(0, Number(row?.orders || 0)) > 0)
    : allPieRows;
  const weightTotal = ordersTotal > 0
    ? ordersTotal
    : Math.max(1, pieRows.length);

  let cursorDeg = 0;
  for (const row of pieRows) {
    const slotId = Number(row?.slot_id || 0);
    const orders = Math.max(0, Number(row?.orders || 0));
    const livePulse = state.food?.demandLive?.pulsesBySlotId?.[String(slotId)] || null;
    const liveEvents = Math.max(0, Number(livePulse?.event_count || 0));
    const weight = ordersTotal > 0 ? orders : 1;
    const sweep = (weight / weightTotal) * 360;
    const startDeg = cursorDeg;
    const endDeg = cursorDeg + sweep;
    cursorDeg = endDeg;

    const segment = document.createElementNS(namespace, 'path');
    segment.setAttribute(
      'd',
      buildFoodDemandDonutPath(120, 120, 86, 54, startDeg, endDeg),
    );
    segment.setAttribute('class', 'food-demand-pie-segment');
    segment.setAttribute('fill', foodDemandColorBySlot(slotId, row._index));
    segment.dataset.slotId = String(slotId);
    if (slotId === selectedId) {
      segment.classList.add('is-active');
    }
    if (liveEvents > 0) {
      segment.classList.add('is-live');
    }
    const slotLabel = String(row?.slot_label || `Slot #${slotId}`);
    const utilization = Math.max(0, Math.min(100, Number(row?.utilization_percent || 0)));
    segment.setAttribute(
      'aria-label',
      `${slotLabel}: ${orders}/${Number(row?.capacity || 0)} orders (${utilization.toFixed(0)}%), ${liveEvents} live events`,
    );
    segment.style.setProperty('--live-intensity', String(Math.max(0, Math.min(100, liveEvents * 20))));
    segment.addEventListener('click', () => {
      state.food.demandSelectedSlotId = slotId;
      renderFoodDemandMinimalChart({ animate: false });
      renderFoodDemandSlotDetail(rows, { animate: false });
    });
    svg.appendChild(segment);
  }

  const selectedRow = rows.find((row) => Number(row?.slot_id || 0) === selectedId) || rows[0];
  const selectedOrders = Math.max(0, Number(selectedRow?.orders || 0));
  const selectedShare = ordersTotal > 0 ? ((selectedOrders / ordersTotal) * 100) : 0;
  const center = document.createElement('div');
  center.className = 'food-demand-pie-center';
  center.style.setProperty('--selected-color', foodDemandColorBySlot(selectedId, 0));
  center.innerHTML = `
    <small>${escapeHtml(String(selectedRow?.slot_label || '--'))}</small>
    <strong>${selectedOrders}</strong>
    <span>${selectedShare.toFixed(1)}% share</span>
  `;

  chartWrap.append(svg, center);
  layout.appendChild(chartWrap);

  for (const row of pieRows) {
    const slotId = Number(row?.slot_id || 0);
    const orders = Math.max(0, Number(row?.orders || 0));
    const capacity = Math.max(0, Number(row?.capacity || 0));
    const utilization = Math.max(0, Math.min(100, Number(row?.utilization_percent || 0)));
    const livePulse = state.food?.demandLive?.pulsesBySlotId?.[String(slotId)] || null;
    const liveEvents = Math.max(0, Number(livePulse?.event_count || 0));
    const legendBtn = document.createElement('button');
    legendBtn.type = 'button';
    legendBtn.className = 'food-demand-legend-item';
    legendBtn.style.setProperty('--slot-color', foodDemandColorBySlot(slotId, Number(row?._index || 0)));
    if (slotId === selectedId) {
      legendBtn.classList.add('is-active');
    }
    if (liveEvents > 0) {
      legendBtn.classList.add('is-live');
    }
    legendBtn.innerHTML = `
      <span class="food-demand-legend-dot" aria-hidden="true"></span>
      <span class="food-demand-legend-main">${escapeHtml(String(row?.slot_label || `Slot #${slotId}`))}</span>
      <span class="food-demand-legend-meta">${orders}/${capacity} • ${utilization.toFixed(0)}%</span>
    `;
    legendBtn.title = `${orders} orders • ${liveEvents} live events`;
    legendBtn.addEventListener('click', () => {
      state.food.demandSelectedSlotId = slotId;
      renderFoodDemandMinimalChart({ animate: false });
      renderFoodDemandSlotDetail(rows, { animate: false });
    });
    if (animate && liveEvents > 0) {
      pulseFoodDemandLiveNode(legendBtn);
    }
    legend.appendChild(legendBtn);
  }

  layout.appendChild(legend);
  els.foodDemandChartModule.appendChild(layout);
  renderFoodDemandSlotDetail(rows, { animate });
}

function renderFoodDemandLiveSignal({ animate = false } = {}) {
  if (!els.foodDemandLiveCompactSummary) {
    return;
  }
  const live = state.food.demandLive || {};
  const windowMinutes = Math.max(1, Number(live.windowMinutes || 2));
  const created = Math.max(0, Number(live.ordersLastWindow || 0));
  const status = Math.max(0, Number(live.statusUpdatesLastWindow || 0));
  const payments = Math.max(0, Number(live.paymentEventsLastWindow || 0));
  const active = Math.max(0, Number(live.activeOrders || 0));
  const totalEvents = created + status + payments;
  const demandRows = getFoodDemandRowsInDisplayOrder();
  const fallbackHotRow = resolveFoodDemandHotRow(demandRows);
  let hottestText = '--';
  if (live.hottestSlotLabel && Number(live.hottestSlotOrders || 0) > 0) {
    hottestText = `${live.hottestSlotLabel} (${Number(live.hottestSlotOrders || 0)})`;
  } else if (fallbackHotRow) {
    hottestText = `${String(fallbackHotRow.slot_label || '--')} (${Number(fallbackHotRow.orders || 0)})`;
  }
  els.foodDemandLiveCompactSummary.textContent = `Active ${active} • Events ${totalEvents} in ${windowMinutes}m • Hot ${hottestText}`;
  if (els.foodDemandLiveCompact) {
    els.foodDemandLiveCompact.classList.toggle('is-live-active', totalEvents > 0);
  }
  if (els.foodDemandLiveHotBtn) {
    const hotSlotId = resolveFoodDemandHotSlotId(demandRows);
    els.foodDemandLiveHotBtn.disabled = hotSlotId <= 0;
    els.foodDemandLiveHotBtn.textContent = hotSlotId > 0 ? 'Focus hottest' : 'No hotspot';
  }
  if (animate) {
    pulseFoodDemandLiveNode(els.foodDemandLiveCompactSummary);
    if (els.foodDemandLiveCompact) {
      pulseFoodDemandLiveNode(els.foodDemandLiveCompact);
    }
  }
}

function demandFreshnessLabel(syncedAtMs) {
  const ts = Number(syncedAtMs || 0);
  if (!Number.isFinite(ts) || ts <= 0) {
    return 'Live sync --';
  }
  const deltaSeconds = Math.max(0, Math.floor((Date.now() - ts) / 1000));
  if (deltaSeconds <= 1) {
    return 'Live sync just now';
  }
  if (deltaSeconds < 60) {
    return `Live sync ${deltaSeconds}s ago`;
  }
  const deltaMinutes = Math.floor(deltaSeconds / 60);
  return `Live sync ${deltaMinutes}m ago`;
}

function markFoodDemandFreshness({ changed = false } = {}) {
  state.food.lastDemandSyncAtMs = Date.now();
  if (changed) {
    state.food.demandSyncPulseUntilMs = Date.now() + 1800;
  }
  renderFoodDemandFreshnessIndicator();
}

function renderFoodDemandFreshnessIndicator() {
  if (els.foodDemandFreshness) {
    els.foodDemandFreshness.textContent = demandFreshnessLabel(state.food.lastDemandSyncAtMs);
  }
  if (els.foodDemandChartModule) {
    const isPulseOn = Date.now() < Number(state.food.demandSyncPulseUntilMs || 0);
    els.foodDemandChartModule.classList.toggle('is-live-pulse', isPulseOn);
  }
}

function createDemandBarColumn(slot) {
  const column = document.createElement('div');
  column.className = 'bar-col';
  column.dataset.slotId = String(slot?.slot_id || '');
  column.dataset.orders = String(Number(slot?.orders || 0));
  column.dataset.utilization = String(Number(slot?.utilization_percent || 0));
  column.dataset.liveEvents = '0';

  const activity = document.createElement('div');
  activity.className = 'bar-activity is-idle';
  activity.dataset.role = 'activity';
  activity.textContent = 'idle';

  const wrap = document.createElement('div');
  wrap.className = 'bar-wrap';

  const bar = document.createElement('div');
  bar.className = 'bar';
  bar.dataset.role = 'bar';
  wrap.appendChild(bar);

  const value = document.createElement('div');
  value.className = 'bar-value';
  value.dataset.role = 'value';

  const label = document.createElement('div');
  label.className = 'bar-label';
  label.dataset.role = 'label';

  const delta = document.createElement('div');
  delta.className = 'bar-delta hidden';
  delta.dataset.role = 'delta';

  column.append(activity, wrap, value, label, delta);
  return column;
}

function triggerDemandBarPulse(column, deltaOrders) {
  if (!column) {
    return;
  }
  column.classList.remove('is-updated', 'delta-up', 'delta-down');
  // Force animation restart for repeated live updates.
  // eslint-disable-next-line no-unused-expressions
  column.offsetWidth;
  column.classList.add('is-updated');
  if (deltaOrders > 0) {
    column.classList.add('delta-up');
  } else if (deltaOrders < 0) {
    column.classList.add('delta-down');
  }
  if (column._demandPulseTimer) {
    window.clearTimeout(column._demandPulseTimer);
  }
  column._demandPulseTimer = window.setTimeout(() => {
    column.classList.remove('is-updated', 'delta-up', 'delta-down');
    const deltaEl = column.querySelector('[data-role="delta"]');
    if (deltaEl) {
      deltaEl.classList.add('hidden');
      deltaEl.textContent = '';
    }
    column._demandPulseTimer = null;
  }, 1800);
}

function triggerDemandLiveBurst(column) {
  if (!column) {
    return;
  }
  column.classList.remove('is-live-burst');
  // Force animation restart for frequent live activity bursts.
  // eslint-disable-next-line no-unused-expressions
  column.offsetWidth;
  column.classList.add('is-live-burst');
  if (column._demandLiveBurstTimer) {
    window.clearTimeout(column._demandLiveBurstTimer);
  }
  column._demandLiveBurstTimer = window.setTimeout(() => {
    column.classList.remove('is-live-burst');
    column._demandLiveBurstTimer = null;
  }, 1300);
}

function renderDemandChartIn(container, { animate = false } = {}) {
  if (!container) {
    return;
  }

  if (!state.demand.length) {
    container.innerHTML = '';
    const empty = document.createElement('div');
    empty.className = 'list-item';
    empty.textContent = 'No slot demand data for selected date.';
    container.appendChild(empty);
    return;
  }

  const existingColumns = new Map(
    Array.from(container.querySelectorAll('.bar-col[data-slot-id]'))
      .map((column) => [String(column.dataset.slotId || ''), column]),
  );
  const activeKeys = new Set();

  for (const slot of state.demand) {
    const slotKey = String(slot?.slot_id || '');
    if (!slotKey) {
      continue;
    }
    activeKeys.add(slotKey);
    let column = existingColumns.get(slotKey);
    if (!column) {
      column = createDemandBarColumn(slot);
    }

    const previousOrders = Number(column.dataset.orders || 0);
    const previousUtilization = Number(column.dataset.utilization || 0);
    const nextOrders = Number(slot.orders || 0);
    const nextUtilization = Number(slot.utilization_percent || 0);
    const deltaOrders = nextOrders - previousOrders;
    const utilizationChanged = Math.abs(nextUtilization - previousUtilization) >= 0.1;
    const ordersChanged = deltaOrders !== 0;

    const bar = column.querySelector('[data-role="bar"]');
    const value = column.querySelector('[data-role="value"]');
    const label = column.querySelector('[data-role="label"]');
    const delta = column.querySelector('[data-role="delta"]');
    const activity = column.querySelector('[data-role="activity"]');
    if (!bar || !value || !label || !delta || !activity) {
      continue;
    }

    bar.classList.toggle('warn', nextUtilization >= 80);
    bar.style.setProperty('--h', String(Math.max(6, Math.min(slot.utilization_percent, 100))));

    value.textContent = `${slot.orders}/${slot.capacity}`;
    label.textContent = `${slot.slot_label} (${slot.utilization_percent}%)`;

    if (animate && (ordersChanged || utilizationChanged)) {
      if (deltaOrders > 0) {
        delta.textContent = `+${deltaOrders} live`;
      } else if (deltaOrders < 0) {
        delta.textContent = `${deltaOrders} live`;
      } else {
        delta.textContent = 'Updated live';
      }
      delta.classList.remove('hidden');
      triggerDemandBarPulse(column, deltaOrders);
    }

    const livePulse = state.food?.demandLive?.pulsesBySlotId?.[slotKey] || null;
    const previousLiveEvents = Number(column.dataset.liveEvents || 0);
    const nextLiveEvents = Math.max(0, Number(livePulse?.event_count || 0));
    const liveEventsChanged = previousLiveEvents !== nextLiveEvents;
    column.dataset.liveEvents = String(nextLiveEvents);
    column.style.setProperty('--live-intensity', String(Math.max(0, Math.min(100, nextLiveEvents * 18))));
    column.classList.toggle('is-live-hot', nextLiveEvents > 0);
    activity.classList.toggle('is-idle', nextLiveEvents <= 0);
    activity.textContent = nextLiveEvents > 0 ? `${nextLiveEvents} live evt` : 'idle';
    if (animate && liveEventsChanged) {
      triggerDemandLiveBurst(column);
      pulseFoodDemandLiveNode(activity, 'is-live-updated', 900);
    }

    column.dataset.orders = String(nextOrders);
    column.dataset.utilization = String(nextUtilization);
    container.appendChild(column);
  }

  for (const [slotKey, column] of existingColumns.entries()) {
    if (!activeKeys.has(slotKey)) {
      if (column._demandPulseTimer) {
        window.clearTimeout(column._demandPulseTimer);
      }
      if (column._demandLiveBurstTimer) {
        window.clearTimeout(column._demandLiveBurstTimer);
      }
      column.remove();
    }
  }
}

function renderDemandChart(options = {}) {
  const animate = Boolean(options?.animate);
  const foodOnly = Boolean(options?.foodOnly);
  if (!foodOnly) {
    renderDemandChartIn(els.demandChart, { animate: false });
  }
  renderFoodDemandMinimalChart({ animate });
  renderFoodDemandFreshnessIndicator();
}

function renderCapacityChart() {
  if (!els.capacityChart) {
    return;
  }
  els.capacityChart.innerHTML = '';
  const topRows = state.capacity.slice(0, 6);

  if (!topRows.length) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'No capacity utilization rows yet. Assign classrooms to courses.';
    els.capacityChart.appendChild(row);
    return;
  }

  for (const item of topRows) {
    const row = document.createElement('div');
    row.className = 'hbar-row';
    const courseCode = String(item?.course_code || item?.primary_course_code || '--');
    const classroomLabel = String(item?.classroom || item?.classroom_label || '--');
    const utilizationPercent = Number(item?.utilization_percent || 0);

    const meta = document.createElement('div');
    meta.className = 'hbar-meta';
    meta.innerHTML = `<span>${escapeHtml(courseCode)} • ${escapeHtml(classroomLabel)}</span><span>${Math.round(utilizationPercent)}%</span>`;

    const track = document.createElement('div');
    track.className = 'hbar-track';

    const fill = document.createElement('div');
    fill.className = 'hbar-fill';
    fill.style.setProperty('--w', String(Math.max(3, Math.min(utilizationPercent, 100))));

    track.appendChild(fill);
    row.appendChild(meta);
    row.appendChild(track);
    els.capacityChart.appendChild(row);
  }
}

function clampPercent(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return 0;
  }
  return Math.max(0, Math.min(100, numeric));
}

function computeAdministrativeHealthMetrics() {
  const summary = state.admin?.summary || null;
  const hasSummary = Boolean(summary && typeof summary === 'object');
  const enrolled = hasSummary
    ? Math.max(0, Number(summary.active_today || 0))
    : (Array.isArray(state.attendanceSummary) ? state.attendanceSummary.length : 0);
  const absent = hasSummary
    ? Math.max(0, Number(summary.absent_today || 0))
    : (Array.isArray(state.absentees) ? state.absentees.length : 0);
  const present = hasSummary
    ? Math.max(0, Number(summary.present_today || 0))
    : Math.max(0, enrolled - absent);
  const attendanceHealth = hasSummary
    ? clampPercent(Number(summary.attendance_rate_today || 0))
    : (enrolled ? clampPercent((present / enrolled) * 100) : 0);

  const capacityRows = Array.isArray(state.capacity) ? state.capacity : [];
  const fallbackCapacityAverage = capacityRows.length
    ? clampPercent(
      capacityRows.reduce((sum, row) => sum + Number(row.utilization_percent || 0), 0) / capacityRows.length
    )
    : 0;
  const capacityAverage = hasSummary
    ? clampPercent(Number(summary.capacity_utilization_percent || 0))
    : fallbackCapacityAverage;
  const hasCapacitySignal = capacityRows.length > 0 || Number.isFinite(Number(summary?.capacity_utilization_percent));
  const capacityBalance = hasCapacitySignal
    ? clampPercent(100 - (Math.abs(capacityAverage - 72) * 2.2))
    : 0;

  const demandRows = Array.isArray(state.demand) ? state.demand : [];
  const demandPeak = demandRows.length
    ? clampPercent(Math.max(...demandRows.map((slot) => Number(slot.utilization_percent || 0))))
    : 0;
  const demandPressure = demandRows.length ? clampPercent(100 - demandPeak) : 0;

  const workloadRows = Array.isArray(state.resources?.workload) ? state.resources.workload : [];
  const avgStudentsPerFaculty = workloadRows.length
    ? workloadRows.reduce((sum, row) => sum + Number(row.total_enrolled_students || 0), 0) / workloadRows.length
    : 0;
  const fallbackWorkloadIndex = workloadRows.length
    ? clampPercent(100 - Math.max(0, avgStudentsPerFaculty - 40) * 1.1)
    : 0;
  const workloadDistribution = hasSummary
    ? clampPercent(Number(summary.workload_distribution_percent || 0))
    : null;
  const workloadIndex = Number.isFinite(workloadDistribution)
    ? clampPercent(100 - Math.abs(Number(workloadDistribution) - 85) * 1.4)
    : fallbackWorkloadIndex;

  return {
    attendanceHealth,
    capacityBalance,
    demandPressure,
    workloadIndex,
    capacityAverage,
    demandPeak,
  };
}

function renderAdministrativeHealthMetrics(metrics) {
  const rows = [
    { valueEl: els.adminHealthAttendanceValue, fillEl: els.adminHealthAttendanceFill, value: metrics.attendanceHealth },
    { valueEl: els.adminHealthCapacityValue, fillEl: els.adminHealthCapacityFill, value: metrics.capacityBalance },
    { valueEl: els.adminHealthDemandValue, fillEl: els.adminHealthDemandFill, value: metrics.demandPressure },
    { valueEl: els.adminHealthWorkloadValue, fillEl: els.adminHealthWorkloadFill, value: metrics.workloadIndex },
  ];

  for (const row of rows) {
    if (row.valueEl) {
      row.valueEl.textContent = `${Math.round(clampPercent(row.value))}%`;
    }
    if (row.fillEl) {
      const score = clampPercent(row.value);
      row.fillEl.style.setProperty('--w', String(Math.max(4, score)));
      row.fillEl.dataset.state = score >= 75 ? 'good' : (score >= 45 ? 'mid' : 'warn');
    }
  }
}

function pushAdministrativeTelemetry(metrics) {
  const history = Array.isArray(state.admin.telemetryHistory) ? state.admin.telemetryHistory : [];
  history.push({
    at: Date.now(),
    attendance: clampPercent(metrics.attendanceHealth),
    capacity: clampPercent(metrics.capacityAverage),
    demand: clampPercent(metrics.demandPeak),
  });
  state.admin.telemetryHistory = history.slice(-12);
}

function buildTelemetryPath(values, width, height, padding) {
  if (!Array.isArray(values) || !values.length) {
    return '';
  }
  if (values.length === 1) {
    const x = width / 2;
    const y = height - padding - (clampPercent(values[0]) / 100) * (height - padding * 2);
    return `M ${x.toFixed(2)} ${y.toFixed(2)}`;
  }
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;
  const stepX = usableWidth / (values.length - 1);
  return values
    .map((value, index) => {
      const x = padding + stepX * index;
      const y = height - padding - (clampPercent(value) / 100) * usableHeight;
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(' ');
}

function renderAdministrativeTelemetryChart() {
  if (!els.adminTelemetryChart) {
    return;
  }
  const updateTelemetryStat = (valueEl, deltaEl, value, delta) => {
    if (valueEl) {
      valueEl.textContent = `${Math.round(clampPercent(value))}%`;
    }
    if (deltaEl) {
      const rounded = Math.round(delta || 0);
      const sign = rounded > 0 ? '+' : '';
      deltaEl.textContent = `Δ ${sign}${rounded}%`;
      deltaEl.dataset.trend = rounded > 0 ? 'up' : (rounded < 0 ? 'down' : 'flat');
    }
  };

  const rows = Array.isArray(state.admin.telemetryHistory) ? state.admin.telemetryHistory : [];
  els.adminTelemetryChart.innerHTML = '';
  if (rows.length < 2) {
    const empty = document.createElement('div');
    empty.className = 'list-item';
    empty.textContent = 'Telemetry trend starts building after two refresh cycles.';
    els.adminTelemetryChart.appendChild(empty);
    updateTelemetryStat(els.adminTelemetryAttendanceNow, els.adminTelemetryAttendanceDelta, 0, 0);
    updateTelemetryStat(els.adminTelemetryCapacityNow, els.adminTelemetryCapacityDelta, 0, 0);
    updateTelemetryStat(els.adminTelemetryDemandNow, els.adminTelemetryDemandDelta, 0, 0);
    if (els.adminTelemetryStabilityNow) {
      els.adminTelemetryStabilityNow.textContent = '--';
    }
    if (els.adminTelemetryStabilityNote) {
      els.adminTelemetryStabilityNote.textContent = 'Collecting trend points';
    }
    return;
  }

  const width = 620;
  const height = 188;
  const padding = 18;
  const namespace = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(namespace, 'svg');
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('preserveAspectRatio', 'none');
  svg.classList.add('telemetry-svg');

  const guideValues = [25, 50, 75];
  const guideGroup = document.createElementNS(namespace, 'g');
  guideGroup.setAttribute('class', 'telemetry-guides');
  for (const guide of guideValues) {
    const y = height - padding - (guide / 100) * (height - padding * 2);
    const line = document.createElementNS(namespace, 'line');
    line.setAttribute('x1', String(padding));
    line.setAttribute('x2', String(width - padding));
    line.setAttribute('y1', y.toFixed(2));
    line.setAttribute('y2', y.toFixed(2));
    guideGroup.appendChild(line);
  }
  svg.appendChild(guideGroup);

  const series = [
    {
      key: 'attendance',
      className: 'telemetry-line-attendance',
      values: rows.map((entry) => clampPercent(entry.attendance)),
    },
    {
      key: 'capacity',
      className: 'telemetry-line-capacity',
      values: rows.map((entry) => clampPercent(entry.capacity)),
    },
    {
      key: 'demand',
      className: 'telemetry-line-demand',
      values: rows.map((entry) => clampPercent(entry.demand)),
    },
  ];

  for (const lineDef of series) {
    const path = document.createElementNS(namespace, 'path');
    path.setAttribute('d', buildTelemetryPath(lineDef.values, width, height, padding));
    path.setAttribute('class', `telemetry-line ${lineDef.className}`);
    svg.appendChild(path);
  }

  const latest = rows[rows.length - 1];
  const latestX = width - padding;
  const latestMarkers = [
    { className: 'telemetry-dot-attendance', value: latest.attendance },
    { className: 'telemetry-dot-capacity', value: latest.capacity },
    { className: 'telemetry-dot-demand', value: latest.demand },
  ];
  for (const marker of latestMarkers) {
    const y = height - padding - (clampPercent(marker.value) / 100) * (height - padding * 2);
    const dot = document.createElementNS(namespace, 'circle');
    dot.setAttribute('cx', latestX.toFixed(2));
    dot.setAttribute('cy', y.toFixed(2));
    dot.setAttribute('r', '3.8');
    dot.setAttribute('class', `telemetry-dot ${marker.className}`);
    svg.appendChild(dot);
  }

  const previous = rows[rows.length - 2] || latest;
  const attendanceDelta = clampPercent(latest.attendance) - clampPercent(previous.attendance);
  const capacityDelta = clampPercent(latest.capacity) - clampPercent(previous.capacity);
  const demandDelta = clampPercent(latest.demand) - clampPercent(previous.demand);
  updateTelemetryStat(els.adminTelemetryAttendanceNow, els.adminTelemetryAttendanceDelta, latest.attendance, attendanceDelta);
  updateTelemetryStat(els.adminTelemetryCapacityNow, els.adminTelemetryCapacityDelta, latest.capacity, capacityDelta);
  updateTelemetryStat(els.adminTelemetryDemandNow, els.adminTelemetryDemandDelta, latest.demand, demandDelta);

  const recent = rows.slice(-6);
  let movementCount = 0;
  let movementTotal = 0;
  for (let idx = 1; idx < recent.length; idx += 1) {
    movementTotal += Math.abs(clampPercent(recent[idx].attendance) - clampPercent(recent[idx - 1].attendance));
    movementTotal += Math.abs(clampPercent(recent[idx].capacity) - clampPercent(recent[idx - 1].capacity));
    movementTotal += Math.abs(clampPercent(recent[idx].demand) - clampPercent(recent[idx - 1].demand));
    movementCount += 3;
  }
  const avgMovement = movementCount ? (movementTotal / movementCount) : 0;
  const stability = clampPercent(100 - avgMovement * 2.1);
  if (els.adminTelemetryStabilityNow) {
    els.adminTelemetryStabilityNow.textContent = `${Math.round(stability)}%`;
  }
  if (els.adminTelemetryStabilityNote) {
    els.adminTelemetryStabilityNote.textContent = stability >= 75
      ? 'Signal stable'
      : (stability >= 50 ? 'Moderate drift' : 'High volatility');
  }

  els.adminTelemetryChart.appendChild(svg);
}

async function refreshOverview() {
  await refreshAdminLive({
    workDate: els.workDate?.value || todayISO(),
    mode: 'enrollment',
  });
  if (!state.admin?.insights) {
    await refreshAdminInsights({
      workDate: els.workDate?.value || todayISO(),
      mode: 'enrollment',
    });
  } else {
    renderAdminInsights();
  }
}

function adminTimestampLabel(rawValue, fallbackText = '--') {
  const parsed = parseFoodDateTime(rawValue);
  if (!parsed) {
    return fallbackText;
  }
  return parsed.toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

function adminFreshnessLabel(lastUpdatedAtRaw) {
  const parsed = parseFoodDateTime(lastUpdatedAtRaw);
  if (!parsed) {
    return 'Freshness: --';
  }
  const deltaSeconds = Math.max(0, Math.floor((Date.now() - parsed.getTime()) / 1000));
  if (deltaSeconds <= 1) {
    return 'Freshness: just now';
  }
  if (deltaSeconds < 60) {
    return `Freshness: ${deltaSeconds}s ago`;
  }
  const deltaMinutes = Math.floor(deltaSeconds / 60);
  if (deltaMinutes < 60) {
    return `Freshness: ${deltaMinutes}m ago`;
  }
  const deltaHours = Math.floor(deltaMinutes / 60);
  return `Freshness: ${deltaHours}h ago`;
}

function renderAdminLiveIndicator() {
  const summary = state.admin?.summary || null;
  const updatedAtRaw = state.admin?.lastUpdatedAt || summary?.last_updated_at || null;
  const staleAfterSeconds = Math.max(20, Number(state.admin?.staleAfterSeconds || summary?.stale_after_seconds || 60));
  const parsed = parseFoodDateTime(updatedAtRaw);
  const ageMs = parsed ? Math.max(0, Date.now() - parsed.getTime()) : Number.POSITIVE_INFINITY;
  const stale = !Number.isFinite(ageMs) || ageMs > staleAfterSeconds * 1000;

  if (els.adminLiveChip) {
    els.adminLiveChip.textContent = stale ? 'Stale Telemetry' : 'Live Telemetry';
    els.adminLiveChip.classList.toggle('is-stale', stale);
    els.adminLiveChip.classList.toggle('is-fresh', !stale);
    if (parsed) {
      els.adminLiveChip.title = `Last updated ${adminTimestampLabel(updatedAtRaw)}`;
    }
  }
  if (els.adminDataFreshnessNote) {
    const freshness = adminFreshnessLabel(updatedAtRaw);
    const staleSuffix = stale ? ` • stale>${staleAfterSeconds}s` : '';
    els.adminDataFreshnessNote.textContent = `${freshness}${staleSuffix}`;
  }
}

function renderAdminIssues() {
  if (!els.adminIssuesWrap) {
    return;
  }
  els.adminIssuesWrap.innerHTML = '';
  const sourceAlerts = Array.isArray(state.admin?.alerts) ? state.admin.alerts : [];
  const sourceIssues = Array.isArray(state.admin?.summary?.top_issues) ? state.admin.summary.top_issues : [];
  const rows = sourceAlerts.length ? sourceAlerts : sourceIssues;

  if (!rows.length) {
    const row = document.createElement('div');
    row.className = 'list-item good admin-issue-item';
    row.innerHTML = `
      <span class="admin-issue-message">No high-priority issues detected.</span>
      <span class="admin-issue-meta">System healthy • auto-monitoring active</span>
    `;
    els.adminIssuesWrap.appendChild(row);
    return;
  }

  for (const item of rows.slice(0, 12)) {
    const severity = String(item?.severity || 'medium').toLowerCase();
    const typeLabel = asTitleCase(String(item?.issue_type || 'issue').replaceAll('_', ' '));
    const message = String(item?.message || 'Issue detected');
    const context = item?.context && typeof item.context === 'object' ? item.context : null;
    const room = context?.room_label ? ` • ${context.room_label}` : '';
    const weekday = Number.isFinite(Number(context?.weekday)) ? ` • D${Number(context.weekday)}` : '';
    const toneClass = severity === 'high' ? 'warn' : (severity === 'low' ? 'good' : '');
    const row = document.createElement('div');
    row.className = `list-item admin-issue-item ${toneClass}`.trim();
    row.innerHTML = `
      <span class="admin-issue-message">${escapeHtml(message)}</span>
      <span class="admin-issue-meta">${escapeHtml(typeLabel)} • ${escapeHtml(severity.toUpperCase())}${escapeHtml(room)}${escapeHtml(weekday)}</span>
    `;
    els.adminIssuesWrap.appendChild(row);
  }
}

function formatCount(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return '0';
  }
  return Math.round(parsed).toLocaleString('en-IN');
}

function buildAdminInsightBarRows(items, labelKey, valueKey, maxValue = 100) {
  const source = Array.isArray(items) ? items : [];
  if (!source.length) {
    return '<div class="list-item">No baseline data available.</div>';
  }
  return source.map((item) => {
    const label = escapeHtml(String(item?.[labelKey] || '--'));
    const numericValue = Number(item?.[valueKey] || 0);
    const width = clampPercent((numericValue / Math.max(1, Number(maxValue) || 100)) * 100);
    const valueLabel = `${formatCount(numericValue)}${valueKey.includes('percent') ? '%' : ''}`;
    return `
      <div class="admin-insight-bar-row">
        <div class="admin-insight-bar-head">
          <span>${label}</span>
          <strong>${escapeHtml(valueLabel)}</strong>
        </div>
        <div class="admin-insight-bar-track"><span class="admin-insight-bar-fill" style="--w:${width}"></span></div>
      </div>
    `;
  }).join('');
}

function renderAdminInsights() {
  const profileWrap = els.adminProfileWrap;
  const benchmarkWrap = els.adminBenchmarkWrap;
  if (!profileWrap || !benchmarkWrap) {
    return;
  }

  const insights = state.admin?.insights;
  const profile = (insights && typeof insights.profile === 'object') ? insights.profile : null;
  const summary = state.admin?.summary || {};
  if (!profile) {
    profileWrap.innerHTML = '<div class="list-item">Administrative planning profile is loading...</div>';
    benchmarkWrap.innerHTML = '<div class="list-item">Live benchmark overlay is loading...</div>';
    return;
  }

  const activeStudents = profile.active_students || {};
  const discipline = Array.isArray(profile.discipline_distribution) ? profile.discipline_distribution : [];
  const years = Array.isArray(profile.year_distribution) ? profile.year_distribution : [];
  const residency = Array.isArray(profile.residency_split) ? profile.residency_split : [];
  const origin = Array.isArray(profile.origin_split) ? profile.origin_split : [];
  const highlights = Array.isArray(insights?.highlights) ? insights.highlights : [];

  const maxDisciplineShare = Math.max(
    1,
    ...discipline.map((item) => Number(item?.share_percent || 0)),
  );
  const topYear = years[0] || {};
  const hostel = residency.find((row) => String(row?.category || '').toLowerCase().includes('hostel')) || {};
  const international = origin.find((row) => String(row?.category || '').toLowerCase().includes('international')) || {};

  profileWrap.innerHTML = `
    <div class="admin-insight-kpi-row">
      <div class="admin-insight-kpi">
        <span>Modeled Active Students</span>
        <strong>${formatCount(activeStudents.estimated || 0)}</strong>
        <small>Range ${formatCount(activeStudents.min || 0)}-${formatCount(activeStudents.max || 0)}</small>
      </div>
      <div class="admin-insight-kpi">
        <span>Largest Intake Layer</span>
        <strong>${escapeHtml(String(topYear.year || '--'))}</strong>
        <small>${formatCount(topYear.students || 0)} students</small>
      </div>
      <div class="admin-insight-kpi">
        <span>Residential Mix</span>
        <strong>${formatCount(hostel.share_percent || 0)}%</strong>
        <small>${formatCount(hostel.students || 0)} hostelers</small>
      </div>
      <div class="admin-insight-kpi">
        <span>International Mix</span>
        <strong>${formatCount(international.share_percent || 0)}%</strong>
        <small>${formatCount(international.students || 0)} students</small>
      </div>
    </div>
    <div class="admin-insight-block">
      <h4>Discipline Distribution Model</h4>
      ${buildAdminInsightBarRows(discipline.slice(0, 8), 'discipline', 'share_percent', maxDisciplineShare)}
    </div>
    <div class="admin-insight-block">
      <h4>Decision Notes</h4>
      <div class="admin-insight-note-list">
        ${(highlights.length ? highlights.slice(0, 4) : ['No model notes available yet.']).map((line) => (
          `<div class="list-item">${escapeHtml(String(line || ''))}</div>`
        )).join('')}
      </div>
    </div>
  `;

  const utilizationModel = profile.classroom_utilization_model || {};
  const slotModels = Array.isArray(utilizationModel.time_slots) ? utilizationModel.time_slots : [];
  const peakSlot = slotModels.reduce((acc, item) => {
    const util = Number(item?.utilization_percent || 0);
    if (util > Number(acc?.utilization_percent || 0)) {
      return item;
    }
    return acc;
  }, { slot: '--', utilization_percent: 0 });
  const placementRate = Number(profile?.placement_model?.overall?.placement_rate_percent || 0);
  const shuttleDaily = Number(profile?.mobility_model?.daily_shuttle_riders || 0);
  const libraryPeak = Number(profile?.library_model?.peak_late_night_occupancy || 0);

  const liveCapacity = clampPercent(Number(summary?.capacity_utilization_percent || 0));
  const liveAttendance = clampPercent(Number(summary?.attendance_rate_today || 0));
  const liveWorkload = clampPercent(Number(summary?.workload_distribution_percent || 0));
  const peakTarget = clampPercent(Number(peakSlot?.utilization_percent || 0));
  const attendanceTarget = 85;
  const workloadTarget = 85;

  benchmarkWrap.innerHTML = `
    <div class="admin-insight-kpi-row">
      <div class="admin-insight-kpi">
        <span>Capacity vs Peak Target</span>
        <strong>${liveCapacity}%</strong>
        <small>${escapeHtml(String(peakSlot?.slot || '--'))} model target ${peakTarget}%</small>
      </div>
      <div class="admin-insight-kpi">
        <span>Attendance vs Target</span>
        <strong>${liveAttendance}%</strong>
        <small>Target ${attendanceTarget}%</small>
      </div>
      <div class="admin-insight-kpi">
        <span>Workload vs Target</span>
        <strong>${liveWorkload}%</strong>
        <small>Target ${workloadTarget}%</small>
      </div>
      <div class="admin-insight-kpi">
        <span>Placement Baseline</span>
        <strong>${formatCount(placementRate)}%</strong>
        <small>Final-year benchmark model</small>
      </div>
    </div>
    <div class="admin-insight-block">
      <h4>Peak Slot Utilization Model</h4>
      ${buildAdminInsightBarRows(slotModels.slice(0, 9), 'slot', 'utilization_percent', 100)}
    </div>
    <div class="admin-insight-block">
      <h4>Mobility + Library Load Baseline</h4>
      <div class="admin-insight-note-list">
        <div class="list-item">Daily shuttle riders model: ${formatCount(shuttleDaily)} students.</div>
        <div class="list-item">Library daily usage model: ${escapeHtml(String(profile?.library_model?.daily_usage_range || '--'))}.</div>
        <div class="list-item">Library late-night peak model: ${formatCount(libraryPeak)} students.</div>
        <div class="list-item">Exam surge model: +${formatCount(profile?.library_model?.exam_surge_midsem_percent || 0)}% midsems, +${formatCount(profile?.library_model?.exam_surge_endterm_percent || 0)}% endterms.</div>
      </div>
    </div>
  `;
}

async function refreshAdminInsights(options = {}) {
  const workDate = String(options?.workDate || els.workDate?.value || todayISO()).trim() || todayISO();
  const mode = String(options?.mode || 'enrollment').trim() || 'enrollment';
  const payload = await api(`/admin/insights?work_date=${encodeURIComponent(workDate)}&mode=${encodeURIComponent(mode)}`);
  state.admin.insights = payload && typeof payload === 'object' ? payload : null;
  renderAdminInsights();
  return payload;
}

async function refreshAdminRecoveryPlans(options = {}) {
  const includeResolved = Boolean(
    options?.includeResolved
      ?? els.adminRecoveryIncludeResolved?.checked
      ?? state.admin?.recoveryIncludeResolved
  );
  const limit = Math.max(20, Number(options?.limit || 120));
  if (els.adminRecoveryIncludeResolved) {
    els.adminRecoveryIncludeResolved.checked = includeResolved;
  }
  state.admin.recoveryIncludeResolved = includeResolved;
  const payload = await api(
    `/attendance/admin/recovery-plans?include_resolved=${includeResolved ? 'true' : 'false'}&limit=${limit}`
  );
  state.admin.recoveryPlans = Array.isArray(payload?.plans) ? payload.plans : [];
  state.admin.recoveryLastUpdatedAt = payload?.last_updated_at || null;
  renderAdminRecoveryPlans();
  if (!options?.silent) {
    const message = includeResolved
      ? 'Recovery desk refreshed, including recovered plans.'
      : 'Recovery desk refreshed.';
    setAdminRecoveryStatus(message, false, 'success');
  }
  return payload;
}

function applyAdminLivePayload(payload) {
  const summary = (payload && typeof payload.summary === 'object') ? payload.summary : {};
  state.admin.summary = summary;
  state.admin.alerts = Array.isArray(payload?.alerts) ? payload.alerts : [];
  state.admin.lastUpdatedAt = payload?.last_updated_at || summary?.last_updated_at || null;
  state.admin.staleAfterSeconds = Math.max(
    20,
    Number(payload?.stale_after_seconds || summary?.stale_after_seconds || 60)
  );

  state.overview = {
    blocks: Number(summary?.blocks || 0),
    classrooms: Number(summary?.classrooms || 0),
    courses: Number(summary?.courses || 0),
    faculty: Number(summary?.faculty || 0),
    students: Number(summary?.students || 0),
  };
  state.capacity = Array.isArray(payload?.capacity) ? payload.capacity : [];
  state.resources.workload = Array.isArray(payload?.workload) ? payload.workload : [];
  state.resources.mongoStatus = summary?.mongo_status || null;

  updateMetrics();
  renderCapacityChart();
  renderWorkloadChart();
  renderMongoStatus();
  renderAttendanceDonut();
  renderAdminIssues();
  renderAdminLiveIndicator();
  renderAdminInsights();
}

async function refreshAdminLive(options = {}) {
  const workDate = String(options?.workDate || els.workDate?.value || todayISO()).trim() || todayISO();
  const mode = String(options?.mode || 'enrollment').trim() || 'enrollment';
  const payload = await api(`/admin/live?work_date=${encodeURIComponent(workDate)}&mode=${encodeURIComponent(mode)}`);
  applyAdminLivePayload(payload || {});
  return payload;
}

async function recomputeAdminRecoveryScope({ studentId = null, courseId = null, limit = 1000 } = {}) {
  if (!authState.user || authState.user.role !== 'admin') {
    throw new Error('Only admin can recompute attendance recovery scope.');
  }
  const payload = {
    limit: Math.max(1, Number(limit || 1000)),
  };
  if (Number(studentId) > 0) {
    payload.student_id = Number(studentId);
  }
  if (Number(courseId) > 0) {
    payload.course_id = Number(courseId);
  }
  setAdminRecoveryStatus('Recomputing attendance recovery scope...', false, 'loading');
  const result = await api('/attendance/recovery/recompute', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  await Promise.all([
    refreshAdminRecoveryPlans({
      includeResolved: state.admin?.recoveryIncludeResolved,
      silent: true,
    }),
    refreshAdminLive({
      workDate: els.workDate?.value || todayISO(),
      mode: 'enrollment',
    }),
  ]);
  const healthMetrics = computeAdministrativeHealthMetrics();
  renderAdministrativeHealthMetrics(healthMetrics);
  pushAdministrativeTelemetry(healthMetrics);
  renderAdministrativeTelemetryChart();
  renderAdminLiveIndicator();
  renderAdminIssues();
  setAdminRecoveryStatus(
    `Recomputed ${Number(result?.evaluated || 0)} enrollment pair(s) and touched ${Number(result?.plans_touched || 0)} plan(s).`,
    false,
    'success',
  );
  return result;
}

async function openRecoveryPlanInRms(planId) {
  const plans = Array.isArray(state.admin?.recoveryPlans) ? state.admin.recoveryPlans : [];
  const plan = plans.find((item) => Number(item?.id || 0) === Number(planId || 0));
  if (!plan) {
    throw new Error('Recovery plan is no longer available.');
  }
  if (els.rmsQueryCategory) {
    els.rmsQueryCategory.value = 'Attendance';
  }
  if (els.rmsQueryStatus) {
    els.rmsQueryStatus.value = 'pending';
  }
  state.rms.selectedCategory = 'Attendance';
  state.rms.selectedStatus = 'pending';
  setActiveModule('rms');
  await refreshRmsModule({ silent: true });

  const registrationNumber = normalizedRegistrationInput(plan.registration_number || '');
  if (registrationNumber) {
    if (els.rmsSearchRegistration) {
      els.rmsSearchRegistration.value = registrationNumber;
    }
    if (els.rmsAttendanceRegistration) {
      els.rmsAttendanceRegistration.value = registrationNumber;
    }
    try {
      await searchRmsStudentByRegistration({ silent: true });
    } catch (_) {
      // Keep RMS navigation resilient if student preload fails.
    }
    try {
      await searchRmsAttendanceStudentContext({ silent: true });
    } catch (_) {
      // Attendance context is optional for the RMS landing flow.
    }
  }
  setRmsStatus(
    `Opened RMS recovery desk for ${String(plan.student_name || 'student')} in ${String(plan.course_code || 'attendance')}.`,
    false,
  );
}

async function refreshAttendanceData() {
  const courseId = Number(els.courseId.value);
  const date = els.workDate.value;

  if (!courseId || Number.isNaN(courseId)) {
    return;
  }

  state.attendanceSummary = await api(`/attendance/summary?course_id=${courseId}`);

  if (authState.user?.role === 'student') {
    state.absentees = [];
  } else {
    state.absentees = await api(`/attendance/absentees?course_id=${courseId}&attendance_date=${date}`);
  }

  renderAbsentees();
  renderAttendanceDonut();
}

async function refreshDemand(orderDate = '', options = {}) {
  const date = String(orderDate || els.workDate?.value || todayISO());
  const previousDemand = Array.isArray(state.demand) ? state.demand : [];
  const nextDemand = await api(`/food/demand?order_date=${date}`);
  const changed = hasFoodDemandChanged(previousDemand, nextDemand);
  state.demand = Array.isArray(nextDemand) ? nextDemand : [];
  renderDemandChart({
    animate: Boolean(options?.animate ?? changed),
    foodOnly: Boolean(options?.foodOnly),
  });
  markFoodDemandFreshness({ changed });
}

async function refreshFoodDemandLiveSignal(orderDate = '', options = {}) {
  const date = String(orderDate || els.foodOrderDate?.value || state.food.orderDate || todayISO()).trim() || todayISO();
  const payload = await api(`/food/demand/live?order_date=${date}&window_minutes=2`);
  const normalized = normalizeFoodDemandLivePayload(payload);
  const previousDigest = String(state.food.demandLive?.digest || '').trim();
  const hasChanged = Boolean(previousDigest) && previousDigest !== normalized.digest;
  state.food.demandLive = {
    ...state.food.demandLive,
    ...normalized,
  };
  if (hasChanged) {
    state.food.demandLive.pulseUntilMs = Date.now() + 1500;
  }
  const shouldAnimate = Boolean(options?.animate ?? hasChanged);
  renderFoodDemandLiveSignal({ animate: shouldAnimate });
  renderDemandChart({ animate: shouldAnimate, foodOnly: true });
}

function stopFoodDemandLiveTicker() {
  if (foodDemandLiveTimer) {
    window.clearInterval(foodDemandLiveTimer);
    foodDemandLiveTimer = null;
  }
  foodDemandLiveBusy = false;
}

function shouldRunFoodDemandLiveTicker() {
  if (!authState.user) {
    return false;
  }
  if (document.body.classList.contains('auth-open')) {
    return false;
  }
  return getSanitizedModuleKey(state.ui.activeModule) === 'food';
}

async function refreshFoodDemandLiveTick() {
  if (!shouldRunFoodDemandLiveTicker() || foodDemandLiveBusy) {
    return;
  }
  foodDemandLiveBusy = true;
  try {
    const orderDate = String(els.foodOrderDate?.value || state.food.orderDate || todayISO()).trim() || todayISO();
    state.food.orderDate = orderDate;
    await Promise.all([
      refreshDemand(orderDate, { animate: true, foodOnly: true }),
      refreshFoodDemandLiveSignal(orderDate, { animate: true }).catch(() => null),
      (async () => {
        const peaks = await api('/food/peak-times?lookback_days=14');
        state.peakTimes = Array.isArray(peaks) ? peaks : [];
        renderFoodPeakTimes();
      })(),
    ]);
  } catch (_) {
    // Keep UI stable on transient failures; next tick retries.
  } finally {
    foodDemandLiveBusy = false;
  }
}

function syncFoodDemandLiveTicker() {
  stopFoodDemandLiveTicker();
}

async function refreshCapacity() {
  const workDate = String(els.workDate?.value || todayISO()).trim() || todayISO();
  state.capacity = await api(`/admin/capacity?work_date=${encodeURIComponent(workDate)}&mode=enrollment`);
  renderCapacityChart();
}

function setFoodStatus(message, isError = false, state = 'neutral') {
  if (!els.foodStatusMsg) {
    return;
  }
  setUiStateMessage(els.foodStatusMsg, message, {
    state: isError ? 'error' : state,
  });
}

function setFoodLocationStatus(message, tone = 'warn') {
  if (!els.foodLocationStatus) {
    return;
  }
  const stateByTone = {
    ok: 'success',
    warn: 'loading',
    error: 'error',
  };
  setUiStateMessage(els.foodLocationStatus, message, {
    state: stateByTone[String(tone || '').trim()] || 'neutral',
  });
  els.foodLocationStatus.dataset.tone = tone;
}

function setFoodAdminStatus(message, isError = false, state = 'neutral') {
  if (!els.foodAdminStatusMsg) {
    return;
  }
  setUiStateMessage(els.foodAdminStatusMsg, message, {
    state: isError ? 'error' : state,
  });
}

function normalizeFoodKey(value) {
  return String(value || '')
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function shopAliasKey(name, block) {
  return `${normalizeFoodKey(name)}|${normalizeFoodKey(block)}`;
}

function resolveShopCover(name, block) {
  const byAlias = FOOD_SHOP_COVER_BY_ALIAS.get(shopAliasKey(name, block));
  if (byAlias) {
    return byAlias;
  }
  return FOOD_SHOP_COVER_BY_NAME.get(normalizeFoodKey(name)) || '';
}

function resolveShopFallbackCover(name, block) {
  const byAlias = FOOD_SHOP_FALLBACK_BY_ALIAS.get(shopAliasKey(name, block));
  if (byAlias) {
    return byAlias;
  }
  return FOOD_SHOP_FALLBACK_BY_NAME.get(normalizeFoodKey(name)) || FOOD_COVER_FALLBACK_URL || '';
}

function deriveFoodShopGroup(blockValue) {
  const block = normalizeFoodKey(blockValue);
  if (block.includes('unimall') || block.includes('block 17') || block.includes('17')) {
    return 'unimall17';
  }
  if (block.includes('bh 1') || block.includes('bh-1')) {
    return 'bh1';
  }
  if (block.includes('bh 2') || block.includes('bh-2') || block.includes('bh 6') || block.includes('bh-6')) {
    return 'bh2to6';
  }
  if (block.includes('block 41') || block.includes('block-41')) {
    return 'block41';
  }
  if (block.includes('block 34') || block.includes('block-34')) {
    return 'block34';
  }
  return 'bh2to6';
}

function hydrateApiShops(rawShops) {
  if (!Array.isArray(rawShops) || !rawShops.length) {
    return FOOD_SHOP_DIRECTORY.map((shop) => ({
      id: String(shop.id),
      apiShopId: null,
      name: shop.name,
      block: shop.block,
      group: shop.group,
      cover: shop.cover || '',
      fallbackCover: shop.fallbackCover || FOOD_COVER_FALLBACK_URL,
      isPopular: FOOD_POPULAR_SPOT_IDS.includes(shop.id),
      rating: 4.0,
      averagePrepMinutes: 18,
    }));
  }
  const popularNameSet = new Set(['oven express', 'kitchen ette', 'nk food court']);
  return rawShops.map((shop) => {
    const name = String(shop?.name || '').trim();
    const block = String(shop?.block || '').trim();
    const normalizedName = normalizeFoodKey(name);
    const fallbackCover = resolveShopFallbackCover(name, block);
    return {
      id: String(shop.id),
      apiShopId: Number(shop.id),
      name,
      block,
      group: deriveFoodShopGroup(block),
      cover: resolveShopCover(name, block) || fallbackCover,
      fallbackCover,
      isPopular: Boolean(shop?.is_popular) || popularNameSet.has(normalizedName),
      rating: Number(shop?.rating || 0),
      averagePrepMinutes: Number(shop?.average_prep_minutes || 18),
    };
  });
}

function hydrateApiSlots(rawSlots) {
  if (!Array.isArray(rawSlots) || !rawSlots.length) {
    return FOOD_SLOT_FALLBACK.map((slot) => ({ ...slot }));
  }
  const normalized = rawSlots
    .map((slot, index) => {
      const startRaw = String(slot?.start_time || '').trim();
      const endRaw = String(slot?.end_time || '').trim();
      const slotStart = toMinutes(startRaw);
      const slotEnd = toMinutes(endRaw);
      if (!startRaw || !endRaw || !Number.isFinite(slotStart) || !Number.isFinite(slotEnd) || slotEnd <= slotStart) {
        return null;
      }
      const fallbackId = index + 1;
      const parsedId = Number(slot?.id);
      const id = Number.isFinite(parsedId) && parsedId > 0 ? parsedId : fallbackId;
      const label = String(slot?.label || '').trim() || `${formatTime24(startRaw)} - ${formatTime24(endRaw)}`;
      const maxOrders = Number(slot?.max_orders || 0);
      return {
        id,
        label,
        start_time: startRaw,
        end_time: endRaw,
        max_orders: Number.isFinite(maxOrders) && maxOrders > 0 ? maxOrders : 250,
      };
    })
    .filter(Boolean);
  if (!normalized.length) {
    return FOOD_SLOT_FALLBACK.map((slot) => ({ ...slot }));
  }
  return normalized.sort((left, right) => toMinutes(left.start_time) - toMinutes(right.start_time));
}

async function loadShopMenuItems(shopId, { force = false } = {}) {
  const key = String(shopId || '').trim();
  if (!key) {
    return [];
  }
  if (!force && Array.isArray(state.food.menuByShop[key])) {
    return state.food.menuByShop[key];
  }
  const shop = getShopById(key);
  if (!shop?.apiShopId) {
    state.food.menuByShop[key] = [];
    return [];
  }
  const rows = await api(`/food/shops/${shop.apiShopId}/menu-items?active_only=${isFoodDemoEnabled() ? 'false' : 'true'}`);
  const items = Array.isArray(rows) ? rows.map((item) => ({
    id: Number(item.id),
    name: String(item.name || `Item #${item.id}`),
    description: String(item.description || '').trim(),
    basePrice: Number(item.base_price || 0),
    isVeg: Boolean(item.is_veg),
    spicyLevel: Number(item.spicy_level || 0),
    variants: Array.isArray(item.variants) ? item.variants : [],
    addons: Array.isArray(item.addons) ? item.addons : [],
    soldOut: Boolean(item.sold_out),
    stockQuantity: Number.isFinite(Number(item.stock_quantity)) ? Number(item.stock_quantity) : null,
    availableFrom: item.available_from || null,
    availableTo: item.available_to || null,
    prepOverrideMinutes: Number.isFinite(Number(item.prep_time_override_minutes)) ? Number(item.prep_time_override_minutes) : null,
  })) : [];
  state.food.menuByShop[key] = items;
  return items;
}

function getShopById(shopId) {
  const key = String(shopId || '').trim();
  return state.food.shops.find((shop) => String(shop.id) === key) || null;
}

function resolveShopMenuItems(shopId) {
  const key = String(shopId || '').trim();
  if (Array.isArray(state.food.menuByShop[key]) && state.food.menuByShop[key].length) {
    return state.food.menuByShop[key];
  }
  return state.food.items.map((item) => ({
    id: Number(item.id),
    name: String(item.name || `Item #${item.id}`),
    description: '',
    basePrice: Number(item.price || 0),
    isVeg: true,
    spicyLevel: 0,
    variants: [],
    addons: [],
    soldOut: false,
    stockQuantity: null,
    availableFrom: null,
    availableTo: null,
    prepOverrideMinutes: null,
  }));
}

function resolveLegacyFoodItemId(menuItem) {
  const byName = state.food.items.find((item) => normalizeFoodKey(item.name) === normalizeFoodKey(menuItem?.name));
  return byName ? Number(byName.id) : null;
}

async function openFoodShopModal(shopId) {
  const orderGate = getFoodRuntimeOrderGate();
  if (!orderGate.canBrowseShops) {
    setFoodStatus(orderGate.message, true);
    showFoodPopup('Food Hall Closed', orderGate.message, { isError: true, autoHideMs: 2600 });
    return;
  }
  const shop = getShopById(shopId);
  if (!shop || !els.foodShopModal || !els.foodShopMenuList) {
    return;
  }
  state.food.selectedShopId = String(shop.id);
  renderFoodShops();
  let menuItems = [];
  try {
    menuItems = await loadShopMenuItems(shop.id);
  } catch (error) {
    setFoodStatus(error.message || 'Failed to load shop menu items.', true);
  }
  if (!menuItems.length) {
    menuItems = resolveShopMenuItems(shop.id);
  }
  if (els.foodShopModalTitle) {
    els.foodShopModalTitle.textContent = `${shop.name} Menu`;
  }
  if (els.foodShopModalSubtitle) {
    const prep = Number.isFinite(shop.averagePrepMinutes) ? `${Math.max(1, Math.round(shop.averagePrepMinutes))} min avg prep` : 'Live menu';
    els.foodShopModalSubtitle.textContent = `${shop.block} • ${prep}`;
  }
  els.foodShopMenuList.innerHTML = '';
  if (!menuItems.length) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'No active menu items for this shop yet.';
    els.foodShopMenuList.appendChild(row);
  } else {
    for (const menuItem of menuItems) {
      const row = document.createElement('div');
      row.className = 'list-item food-shop-menu-row';
      const label = document.createElement('div');
      const itemOptions = [];
      const metaBits = [];
      if (menuItem.isVeg) {
        metaBits.push('Veg');
      } else {
        metaBits.push('Non-veg');
      }
      if (Number(menuItem.spicyLevel || 0) > 0) {
        metaBits.push(`Spicy ${menuItem.spicyLevel}/5`);
      }
      if (Number.isFinite(menuItem.stockQuantity)) {
        metaBits.push(`Stock ${menuItem.stockQuantity}`);
      }
      if (menuItem.availableFrom && menuItem.availableTo) {
        metaBits.push(`Window ${formatTime(menuItem.availableFrom)}-${formatTime(menuItem.availableTo)}`);
      }
      if (Number.isFinite(Number(menuItem.prepOverrideMinutes)) && Number(menuItem.prepOverrideMinutes) > 0) {
        metaBits.push(`Prep ${Math.max(1, Math.round(Number(menuItem.prepOverrideMinutes)))} min`);
      }
      if (Array.isArray(menuItem.variants) && menuItem.variants.length) {
        metaBits.push(`${menuItem.variants.length} variant(s)`);
        for (const variant of menuItem.variants) {
          const rawOptions = Array.isArray(variant?.options) ? variant.options : [];
          const options = rawOptions.map((option) => String(option || '').trim()).filter(Boolean);
          if (!options.length) {
            continue;
          }
          itemOptions.push({
            label: String(variant?.label || variant?.name || 'Option'),
            options,
          });
        }
      }
      if (Array.isArray(menuItem.addons) && menuItem.addons.length) {
        metaBits.push(`${menuItem.addons.length} add-on(s)`);
      }
      label.innerHTML = `
        <strong>${escapeHtml(menuItem.name)}</strong>
        <small>${formatMoney(menuItem.basePrice)}</small>
        ${menuItem.description ? `<small>${escapeHtml(menuItem.description)}</small>` : ''}
        ${metaBits.length ? `<small>${escapeHtml(metaBits.join(' • '))}</small>` : ''}
      `;
      const optionSelectRows = [];
      if (itemOptions.length) {
        const optionsWrap = document.createElement('div');
        optionsWrap.className = 'food-menu-options';
        for (const optionDef of itemOptions) {
          const optionLabel = document.createElement('label');
          optionLabel.className = 'field food-menu-option-field';
          const title = document.createElement('span');
          title.textContent = optionDef.label;
          const select = document.createElement('select');
          for (const optionText of optionDef.options) {
            const option = document.createElement('option');
            option.value = optionText;
            option.textContent = optionText;
            select.appendChild(option);
          }
          optionLabel.append(title, select);
          optionsWrap.appendChild(optionLabel);
          optionSelectRows.push({ label: optionDef.label, select });
        }
        label.appendChild(optionsWrap);
      }

      const buildItemNote = () => optionSelectRows
        .map((entry) => {
          const selected = String(entry.select?.value || '').trim();
          if (!selected) {
            return '';
          }
          return `${entry.label}: ${selected}`;
        })
        .filter(Boolean)
        .join(' | ');

      const addOneBtn = document.createElement('button');
      addOneBtn.className = 'btn btn-secondary';
      addOneBtn.type = 'button';
      addOneBtn.textContent = 'Add';
      addOneBtn.disabled = !isFoodDemoEnabled() && (Boolean(menuItem.soldOut) || Number(menuItem.stockQuantity) === 0);
      addOneBtn.addEventListener('click', () => {
        void addMenuItemToCart(shop.id, menuItem, 1, buildItemNote()).catch((error) => {
          setFoodStatus(error.message || 'Failed to update cart.', true);
        });
      });
      const addTwoBtn = document.createElement('button');
      addTwoBtn.className = 'btn';
      addTwoBtn.type = 'button';
      addTwoBtn.textContent = 'Add x2';
      addTwoBtn.disabled = !isFoodDemoEnabled() && (Boolean(menuItem.soldOut) || Number(menuItem.stockQuantity) === 0);
      addTwoBtn.addEventListener('click', () => {
        void addMenuItemToCart(shop.id, menuItem, 2, buildItemNote()).catch((error) => {
          setFoodStatus(error.message || 'Failed to update cart.', true);
        });
      });
      if (!isFoodDemoEnabled() && (menuItem.soldOut || Number(menuItem.stockQuantity) === 0)) {
        const soldOutBadge = document.createElement('span');
        soldOutBadge.className = 'shop-popular';
        soldOutBadge.textContent = 'Sold Out';
        label.appendChild(soldOutBadge);
      }
      row.append(label, addOneBtn, addTwoBtn);
      els.foodShopMenuList.appendChild(row);
    }
  }
  els.foodShopModal.classList.remove('hidden');
}

function closeFoodShopModal() {
  if (!els.foodShopModal) {
    return;
  }
  els.foodShopModal.classList.add('hidden');
  state.food.selectedShopId = '';
  renderFoodShops();
}

function setFoodCartModalTab(tab) {
  const nextTab = tab === 'review' ? 'review' : 'cart';
  const isCartTab = nextTab === 'cart';
  const reviewActive = !isCartTab;
  const payActive = Boolean(reviewActive && state.food.checkoutPreviewOpen);
  state.food.cartModalTab = nextTab;
  if (els.foodCartTabCartBtn) {
    els.foodCartTabCartBtn.classList.toggle('is-active', isCartTab);
    els.foodCartTabCartBtn.setAttribute('aria-selected', String(isCartTab));
    els.foodCartTabCartBtn.setAttribute('tabindex', isCartTab ? '0' : '-1');
  }
  if (els.foodCartTabReviewBtn) {
    els.foodCartTabReviewBtn.classList.toggle('is-active', !isCartTab);
    els.foodCartTabReviewBtn.setAttribute('aria-selected', String(!isCartTab));
    els.foodCartTabReviewBtn.setAttribute('tabindex', isCartTab ? '-1' : '0');
  }
  setHidden(els.foodCartTabCartPane, !isCartTab);
  setHidden(els.foodCartTabReviewPane, isCartTab);
  if (els.foodCartStepCart) {
    els.foodCartStepCart.classList.toggle('is-active', isCartTab);
  }
  if (els.foodCartStepReview) {
    els.foodCartStepReview.classList.toggle('is-active', reviewActive);
  }
  if (els.foodCartStepPay) {
    els.foodCartStepPay.classList.toggle('is-active', payActive);
  }
}

function openFoodCartModal() {
  if (!els.foodCartModal) {
    return;
  }
  if (authState.user?.role === 'student') {
    void refreshFoodCartFromServer({ silent: true });
  }
  if (!state.food.cart.items.length) {
    state.food.checkoutPreviewOpen = false;
  }
  ensureFoodDeliveryPointOptions();
  renderFoodCheckoutPreview();
  setFoodCartModalTab(state.food.checkoutPreviewOpen ? 'review' : 'cart');
  syncFoodOrderActionState();
  els.foodCartModal.classList.remove('hidden');
}

function closeFoodCartModal() {
  if (!els.foodCartModal) {
    return;
  }
  setFoodCheckoutPreviewOpen(false);
  setFoodCartModalTab('cart');
  els.foodCartModal.classList.add('hidden');
}

function renderFoodShops() {
  if (!els.foodShopGrid) {
    return;
  }
  els.foodShopGrid.innerHTML = '';
  const popularShops = state.food.shops.filter((shop) => Boolean(shop.isPopular));
  const orderGate = getFoodRuntimeOrderGate();
  const shopsClosed = !orderGate.canBrowseShops;

  for (const group of FOOD_SHOP_GROUPS) {
    const isPopular = group.key === 'popular';
    const shops = isPopular
      ? popularShops
      : state.food.shops.filter((shop) => shop.group === group.key);

    if (!shops.length) {
      continue;
    }

    const section = document.createElement('section');
    section.className = 'food-shop-section';
    section.dataset.group = group.key;

    const head = document.createElement('div');
    head.className = 'food-shop-section-head';
    head.innerHTML = `
      <h4>${escapeHtml(group.title)}</h4>
      <small>${escapeHtml(group.subtitle)}</small>
    `;

    const grid = document.createElement('div');
    grid.className = 'food-shop-cards';

    for (const shop of shops) {
      const card = document.createElement('button');
      card.type = 'button';
      card.className = 'food-shop-card';
      if (shopsClosed) {
        card.classList.add('is-closed');
        card.disabled = true;
        card.setAttribute('aria-disabled', 'true');
      }
      if (String(state.food.cart.shopId) === String(shop.id) || String(state.food.selectedShopId) === String(shop.id)) {
        card.classList.add('is-selected');
      }
      const ratingValue = Number(shop?.rating || 0);
      const ratingLabel = Number.isFinite(ratingValue) ? ratingValue.toFixed(1) : '0.0';
      const fallbackCoverUrl = String(shop?.fallbackCover || '').trim() || FOOD_COVER_FALLBACK_URL;
      const coverUrl = String(shop?.cover || '').trim() || fallbackCoverUrl;
      card.innerHTML = `
        <div class="food-shop-cover-wrap">
          <img
            class="food-shop-cover"
            src="${escapeHtml(coverUrl)}"
            alt="${escapeHtml(shop.name)} cover"
            loading="lazy"
            referrerpolicy="no-referrer"
            data-fallback-src="${escapeHtml(fallbackCoverUrl)}"
          >
          ${shopsClosed ? '<span class="food-shop-closed-badge">Closed</span>' : ''}
        </div>
        <div class="food-shop-card-body">
          <h4>${escapeHtml(shop.name)}</h4>
          <div class="food-shop-card-meta">
            <small>${escapeHtml(shop.block)}</small>
            <span class="shop-rating-live" title="Live vendor rating from delivered orders">★ ${escapeHtml(ratingLabel)}</span>
          </div>
          ${shopsClosed ? `<small class="food-shop-hours-note">Open daily ${FOOD_SERVICE_HOURS_LABEL}</small>` : ''}
          ${shop.isPopular ? '<span class="shop-popular">Popular</span>' : ''}
        </div>
      `;
      const coverImage = card.querySelector('.food-shop-cover');
      if (coverImage instanceof HTMLImageElement) {
        coverImage.addEventListener('error', () => {
          const fallback = String(coverImage.dataset.fallbackSrc || FOOD_COVER_FALLBACK_URL || '').trim();
          if (!fallback || coverImage.src.endsWith(fallback)) {
            return;
          }
          coverImage.src = fallback;
        }, { once: true });
      }
      if (!shopsClosed) {
        card.addEventListener('click', () => {
          void openFoodShopModal(shop.id);
        });
      }
      grid.appendChild(card);
    }

    section.append(head, grid);
    els.foodShopGrid.appendChild(section);
  }
}

function buildFoodCartKey(menuItemId, itemNote = '') {
  return `${Number(menuItemId || 0)}::${normalizeFoodKey(itemNote)}`;
}

function hashFoodCheckoutSeed(seed = '') {
  let hash = 2166136261;
  const normalizedSeed = String(seed || '');
  for (let index = 0; index < normalizedSeed.length; index += 1) {
    hash ^= normalizedSeed.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, '0');
}

function buildFoodCheckoutIdempotencyKey({
  studentId,
  orderDate,
  slotId,
  shopId,
  deliveryPoint,
  cartItems,
  cartUpdatedAt,
}) {
  const normalizedItems = (Array.isArray(cartItems) ? cartItems : [])
    .map((entry) => ({
      menuItemId: Number(entry?.menuItemId || 0),
      quantity: Math.max(1, Number(entry?.quantity || 1)),
      itemNote: String(entry?.itemNote || '').trim().toLowerCase(),
    }))
    .filter((entry) => entry.menuItemId > 0)
    .sort((left, right) => {
      if (left.menuItemId !== right.menuItemId) {
        return left.menuItemId - right.menuItemId;
      }
      if (left.itemNote !== right.itemNote) {
        return left.itemNote.localeCompare(right.itemNote);
      }
      return left.quantity - right.quantity;
    })
    .map((entry) => `${entry.menuItemId}:${entry.quantity}:${entry.itemNote}`)
    .join('|');
  const seed = [
    Number(studentId || 0),
    String(orderDate || '').trim(),
    Number(slotId || 0),
    Number(shopId || 0),
    String(deliveryPoint || '').trim().toLowerCase(),
    String(cartUpdatedAt || '').trim(),
    normalizedItems,
  ].join('|');
  const compactDate = String(orderDate || '').replaceAll('-', '') || 'date';
  return `foodchk-${Number(studentId || 0)}-${compactDate}-${Number(slotId || 0)}-${hashFoodCheckoutSeed(seed)}`.slice(0, 100);
}

function applyFoodCartPayload(cartPayload, { syncSelectedShop = true } = {}) {
  const raw = (cartPayload && typeof cartPayload === 'object') ? cartPayload : {};
  const parsedShopId = Number(raw.shop_id || 0);
  state.food.cart.shopId = parsedShopId > 0 ? String(parsedShopId) : '';
  state.food.cartUpdatedAt = String(raw.updated_at || '').trim();

  const nextItems = [];
  const rawItems = Array.isArray(raw.items) ? raw.items : [];
  for (const row of rawItems) {
    const menuItemId = Number(row?.menu_item_id || 0);
    if (!menuItemId) {
      continue;
    }
    const quantity = Number(row?.quantity || 0);
    if (!Number.isFinite(quantity) || quantity <= 0) {
      continue;
    }
    const note = String(row?.item_note || '').trim();
    const itemShopId = Number(row?.shop_id || parsedShopId || 0);
    const cartKey = String(row?.cart_key || buildFoodCartKey(menuItemId, note)).trim() || buildFoodCartKey(menuItemId, note);
    const foodItemIdRaw = Number(row?.food_item_id);
    nextItems.push({
      cartKey,
      shopId: itemShopId > 0 ? String(itemShopId) : state.food.cart.shopId,
      menuItemId,
      foodItemId: Number.isFinite(foodItemIdRaw) && foodItemIdRaw > 0 ? foodItemIdRaw : null,
      name: String(row?.name || `Item #${menuItemId}`),
      price: Math.max(0, Number(row?.price || 0)),
      quantity: Math.max(1, Math.round(quantity)),
      itemNote: note,
    });
  }
  state.food.cart.items = nextItems;
  state.food.checkoutPreviewOpen = Boolean(raw.checkout_preview_open) && state.food.cart.items.length > 0;
  state.food.checkoutDeliveryPoint = String(raw.checkout_delivery_point || '').trim();

  if (!state.food.cart.items.length) {
    state.food.cart.shopId = '';
    setFoodCartModalTab('cart');
    state.food.checkoutPreviewOpen = false;
    state.food.checkoutDeliveryPoint = '';
  }
  if (state.food.cart.items.length && !state.food.checkoutPreviewOpen && state.food.cartModalTab === 'review') {
    setFoodCartModalTab('cart');
  }
  if (state.food.cart.items.length && syncSelectedShop && state.food.cart.shopId) {
    state.food.selectedShopId = String(state.food.cart.shopId);
  }
}

async function refreshFoodCartFromServer({ silent = false, render = true } = {}) {
  if (authState.user?.role !== 'student') {
    return null;
  }
  try {
    const payload = await api('/food/cart');
    applyFoodCartPayload(payload);
    if (render) {
      ensureFoodDeliveryPointOptions();
      renderFoodCart();
      renderFoodShops();
      if (els.foodCartModal && !els.foodCartModal.classList.contains('hidden')) {
        setFoodCartModalTab(state.food.checkoutPreviewOpen ? 'review' : 'cart');
      }
      syncFoodOrderActionState();
    }
    return payload;
  } catch (error) {
    if (!silent) {
      throw error;
    }
    return null;
  }
}

async function persistFoodCartUiState() {
  if (authState.user?.role !== 'student' || !state.food.cart.items.length) {
    return;
  }
  try {
    const payload = await api('/food/cart/state', {
      method: 'PATCH',
      body: JSON.stringify({
        checkout_preview_open: Boolean(state.food.checkoutPreviewOpen),
        checkout_delivery_point: String(state.food.checkoutDeliveryPoint || '').trim() || null,
      }),
    });
    applyFoodCartPayload(payload, { syncSelectedShop: false });
  } catch (_) {
    // Cart UX should remain responsive even if state sync is delayed.
  }
}

function isFoodDemoEnabled() {
  return Boolean(CLIENT_DEMO_FEATURES_ENABLED && state.food.demoEnabled && authState.user?.role === 'student');
}

function foodDemoRequestHeaders(headers = {}) {
  if (!isFoodDemoEnabled()) {
    return headers;
  }
  return {
    ...headers,
    'X-Food-Demo-Mode': 'true',
  };
}

function renderFoodDemoToggle() {
  if (els.foodDemoToggleBtn) {
    const enabled = isFoodDemoEnabled();
    els.foodDemoToggleBtn.dataset.active = enabled ? 'true' : 'false';
    els.foodDemoToggleBtn.setAttribute('aria-pressed', enabled ? 'true' : 'false');
    els.foodDemoToggleBtn.textContent = enabled ? 'Demo Bypass On' : 'Demo Bypass Off';
    els.foodDemoToggleBtn.classList.toggle('btn-primary', enabled);
    els.foodDemoToggleBtn.classList.toggle('btn-secondary', !enabled);
    els.foodDemoToggleBtn.disabled = authState.user?.role !== 'student';
  }
  if (els.foodDemoStatus) {
    const enabled = isFoodDemoEnabled();
    setHidden(els.foodDemoStatus, !enabled);
    els.foodDemoStatus.textContent = enabled
      ? 'Food Hall demo bypass is on. Date, time, location, stock, slot, and single-shop constraints are bypassed temporarily.'
      : 'Food Hall demo bypass is off.';
  }
}

function setFoodDemoEnabled(enabled, { persist = true } = {}) {
  const nextEnabled = Boolean(CLIENT_DEMO_FEATURES_ENABLED && enabled);
  const changed = state.food.demoEnabled !== nextEnabled;
  state.food.demoEnabled = nextEnabled;
  if (persist) {
    try {
      if (state.food.demoEnabled) {
        window.localStorage.setItem(FOOD_DEMO_STORAGE_KEY, 'true');
      } else {
        window.localStorage.removeItem(FOOD_DEMO_STORAGE_KEY);
      }
    } catch (_) {
      // Ignore storage failures in restricted runtimes.
    }
  }
  if (changed) {
    state.food.menuByShop = {};
    void refreshFoodModule({ silentStatus: true }).catch((error) => {
      log(`Food demo refresh delayed: ${error?.message || 'Unknown error'}`);
    });
  }
  renderFoodDemoToggle();
  renderFoodCheckoutPreview();
  renderFoodCart();
  renderFoodShops();
  syncFoodOrderActionState();
}

function restoreFoodDemoEnabled() {
  if (!CLIENT_DEMO_FEATURES_ENABLED) {
    state.food.demoEnabled = false;
    try {
      window.localStorage.removeItem(FOOD_DEMO_STORAGE_KEY);
    } catch (_) {
      // Ignore storage failures in restricted runtimes.
    }
    return;
  }
  try {
    state.food.demoEnabled = window.localStorage.getItem(FOOD_DEMO_STORAGE_KEY) === 'true';
  } catch (_) {
    state.food.demoEnabled = false;
  }
}

function getSelectedFoodSlot() {
  const slotId = Number(els.foodSlotSelect?.value || 0);
  return state.food.slots.find((slot) => Number(slot.id) === slotId) || null;
}

function resolveFoodOrderDateValue() {
  const selected = String(els.foodOrderDate?.value || state.food.orderDate || todayISO()).trim();
  return selected || todayISO();
}

function clampFoodOrderDateToToday({ showNotice = false } = {}) {
  const today = todayISO();
  if (!els.foodOrderDate) {
    state.food.orderDate = today;
    return false;
  }
  els.foodOrderDate.min = today;
  els.foodOrderDate.removeAttribute('max');
  const selected = String(els.foodOrderDate.value || state.food.orderDate || today).trim() || today;
  if (!parseISODateLocal(selected) || selected < today) {
    els.foodOrderDate.value = today;
    state.food.orderDate = today;
    if (showNotice) {
      setFoodStatus('Pickup date cannot be in the past. Reset to today.', true);
    }
    return true;
  }
  els.foodOrderDate.value = selected;
  state.food.orderDate = selected;
  return false;
}

function getFoodRuntimeOrderGate({ slot = null, orderDate = null, now = new Date() } = {}) {
  if (isFoodDemoEnabled()) {
    return {
      dateAllowed: true,
      serviceOpenNow: true,
      slotElapsed: false,
      canBrowseShops: true,
      canOrderNow: true,
      reason: 'demo_bypass',
      message: 'Food Hall demo bypass is active.',
    };
  }
  const selectedDate = String(orderDate || resolveFoodOrderDateValue()).trim() || todayISO();
  const today = todayISO();
  const nowMinutes = (now.getHours() * 60) + now.getMinutes();
  const dateAllowed = selectedDate === today;
  const isToday = selectedDate === today;
  const serviceOpenNow = nowMinutes >= FOOD_SERVICE_START_MINUTES && nowMinutes < FOOD_SERVICE_END_MINUTES;
  const selectedSlot = slot || getSelectedFoodSlot();
  const slotEndMinutes = selectedSlot ? toMinutes(selectedSlot.end_time) : Number.POSITIVE_INFINITY;
  const slotElapsed = Boolean(selectedSlot && isToday && slotEndMinutes <= nowMinutes);

  if (!dateAllowed) {
    return {
      dateAllowed,
      serviceOpenNow,
      slotElapsed,
      canBrowseShops: false,
      canOrderNow: false,
      reason: 'date_mismatch',
      message: `Orders are allowed only for today (${today}).`,
    };
  }
  if (!serviceOpenNow) {
    return {
      dateAllowed,
      serviceOpenNow,
      slotElapsed: false,
      canBrowseShops: false,
      canOrderNow: false,
      reason: 'service_closed',
      message: `Food Hall is closed now. Ordering is open from ${FOOD_SERVICE_HOURS_LABEL}.`,
    };
  }
  if (slotElapsed) {
    return {
      dateAllowed,
      serviceOpenNow,
      slotElapsed,
      canBrowseShops: true,
      canOrderNow: false,
      reason: 'slot_elapsed',
      message: 'Selected slot has already ended. Choose an upcoming slot.',
    };
  }
  return {
    dateAllowed,
    serviceOpenNow,
    slotElapsed: false,
    canBrowseShops: true,
    canOrderNow: true,
    reason: 'open',
    message: '',
  };
}

function applyFoodRealtimeAvailability({ showStatusOnTransition = false } = {}) {
  if (!authState.user || authState.user.role !== 'student') {
    return;
  }
  if (getSanitizedModuleKey(state.ui.activeModule) !== 'food') {
    return;
  }
  const slot = getSelectedFoodSlot();
  const gate = getFoodRuntimeOrderGate({ slot });
  const signature = [
    gate.dateAllowed ? '1' : '0',
    gate.serviceOpenNow ? '1' : '0',
    gate.slotElapsed ? '1' : '0',
    gate.reason,
    String(slot?.id || 0),
  ].join('|');

  if (state.food.realtimeAvailabilitySignature === signature) {
    return;
  }

  const previousServiceOpen = state.food.realtimeServiceOpen;
  state.food.realtimeAvailabilitySignature = signature;
  state.food.realtimeServiceOpen = gate.serviceOpenNow;
  renderFoodSlotOptions();
  renderFoodShops();
  renderFoodCheckoutPreview();
  syncFoodOrderActionState();

  if (showStatusOnTransition && previousServiceOpen !== null && previousServiceOpen !== gate.serviceOpenNow) {
    if (gate.serviceOpenNow) {
      setFoodStatus('Food Hall is open now. You can place orders for today.', false);
    } else {
      setFoodStatus(gate.message, true);
    }
  }
}

function ensureFoodDeliveryPointOptions() {
  if (!els.foodDeliveryBlockSelect) {
    return;
  }
  const previous = String(state.food.checkoutDeliveryPoint || els.foodDeliveryBlockSelect.value || '').trim();
  els.foodDeliveryBlockSelect.innerHTML = '';

  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = 'Select delivery block';
  els.foodDeliveryBlockSelect.appendChild(placeholder);

  for (const [code, label] of FOOD_DELIVERY_POINTS) {
    const option = document.createElement('option');
    option.value = `${code} - ${label}`;
    option.textContent = `${code}  ${label}`;
    els.foodDeliveryBlockSelect.appendChild(option);
  }

  if (previous && Array.from(els.foodDeliveryBlockSelect.options).some((option) => option.value === previous)) {
    els.foodDeliveryBlockSelect.value = previous;
    state.food.checkoutDeliveryPoint = previous;
  } else {
    els.foodDeliveryBlockSelect.value = '';
    state.food.checkoutDeliveryPoint = '';
  }
}

function buildFoodCheckoutPricing(subtotalAmount) {
  const subtotal = Math.max(0, Number(subtotalAmount || 0));
  if (subtotal <= 0) {
    return {
      subtotal: 0,
      deliveryFee: 0,
      platformFee: 0,
      total: 0,
    };
  }
  const deliveryFee = FOOD_DELIVERY_FEE_INR;
  const platformFee = FOOD_PLATFORM_FEE_INR;
  return {
    subtotal,
    deliveryFee,
    platformFee,
    total: subtotal + deliveryFee + platformFee,
  };
}

function renderFoodCheckoutPreview() {
  const hasItems = Array.isArray(state.food.cart.items) && state.food.cart.items.length > 0;
  if (!hasItems) {
    state.food.checkoutPreviewOpen = false;
    state.food.checkoutDeliveryPoint = '';
  }

  const totalQty = state.food.cart.items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
  const subtotal = state.food.cart.items.reduce((sum, item) => sum + (Number(item.price || 0) * Number(item.quantity || 0)), 0);
  const pricing = buildFoodCheckoutPricing(subtotal);
  if (els.foodReviewSummaryStrip) {
    if (!hasItems) {
      els.foodReviewSummaryStrip.textContent = 'Order summary will appear here once items are added.';
    } else {
      els.foodReviewSummaryStrip.textContent = `${totalQty} item(s) • Subtotal ${formatMoney(pricing.subtotal)} • Estimated total ${formatMoney(pricing.total)}`;
    }
  }

  if (els.foodCheckoutPreview) {
    setHidden(els.foodCheckoutPreview, !(state.food.checkoutPreviewOpen && hasItems));
  }

  if (els.foodCheckoutItems) {
    els.foodCheckoutItems.innerHTML = '';
    if (state.food.checkoutPreviewOpen && hasItems) {
      for (const item of state.food.cart.items) {
        const row = document.createElement('div');
        row.className = 'list-item food-checkout-item-row';
        row.innerHTML = `
          <span>${escapeHtml(item.name)} • ${formatMoney(item.price)}</span>
          <strong>x${Number(item.quantity || 0)}</strong>
        `;
        els.foodCheckoutItems.appendChild(row);
      }
    }
  }

  if (els.foodCheckoutFeeBreakdown) {
    els.foodCheckoutFeeBreakdown.innerHTML = '';
  }

  if (!els.foodCheckoutSummary) {
    return;
  }

  if (!(state.food.checkoutPreviewOpen && hasItems)) {
    els.foodCheckoutSummary.textContent = 'Select delivery block to continue payment.';
    return;
  }

  const slot = getSelectedFoodSlot();
  const orderGate = getFoodRuntimeOrderGate({ slot });
  const slotText = slot
    ? `${slot.label} (${formatTime(slot.start_time)} - ${formatTime(slot.end_time)})`
    : 'No slot selected';
  const delivery = String(state.food.checkoutDeliveryPoint || '').trim();
  const locationOk = state.food.location.verified && state.food.location.allowed && isFoodLocationFresh();
  const locationText = isFoodDemoEnabled()
    ? 'Demo bypass active'
    : (locationOk ? 'Campus location verified' : 'Location not verified yet');
  if (els.foodCheckoutFeeBreakdown) {
    els.foodCheckoutFeeBreakdown.innerHTML = `
      <div class="food-checkout-fee-row"><span>Items subtotal</span><strong>${formatMoney(pricing.subtotal)}</strong></div>
      <div class="food-checkout-fee-row"><span>Delivery fee</span><strong>${formatMoney(pricing.deliveryFee)}</strong></div>
      <div class="food-checkout-fee-row"><span>Platform fee</span><strong>${formatMoney(pricing.platformFee)}</strong></div>
      <div class="food-checkout-fee-row is-total"><span>Grand total</span><strong>${formatMoney(pricing.total)}</strong></div>
    `;
  }
  if (!orderGate.canOrderNow) {
    els.foodCheckoutSummary.textContent = `${orderGate.message} • ${totalQty} item(s) • Grand total ${formatMoney(pricing.total)} • Slot: ${slotText}`;
    return;
  }
  els.foodCheckoutSummary.textContent = `${totalQty} item(s) • Grand total ${formatMoney(pricing.total)} • Slot: ${slotText} • Delivery: ${delivery || 'Not selected'} • ${locationText}`;
}

function setFoodCheckoutPreviewOpen(open) {
  state.food.checkoutPreviewOpen = Boolean(open) && state.food.cart.items.length > 0;
  if (!state.food.checkoutPreviewOpen) {
    state.food.checkoutDeliveryPoint = '';
    if (els.foodDeliveryBlockSelect) {
      els.foodDeliveryBlockSelect.value = '';
    }
    setFoodCartModalTab('cart');
  } else {
    setFoodCartModalTab('review');
  }
  renderFoodCheckoutPreview();
  syncFoodOrderActionState();
  void persistFoodCartUiState();
}

function openFoodCheckoutPreview() {
  const canOrder = authState.user?.role === 'student' && Number(authState.user?.student_id || 0);
  if (!canOrder) {
    throw new Error('Food pre-order is available only for student accounts.');
  }
  if (!state.food.cart.items.length) {
    throw new Error('Add menu items before checkout.');
  }
  if (!Number(els.foodSlotSelect?.value || 0) && !(isFoodDemoEnabled() && Number(state.food.slots?.[0]?.id || 0))) {
    throw new Error('Select break slot before checkout.');
  }
  const selectedSlot = getSelectedFoodSlot();
  if (!selectedSlot && !isFoodDemoEnabled()) {
    throw new Error('Selected break slot is unavailable. Refresh and retry.');
  }
  const orderGate = getFoodRuntimeOrderGate({ slot: selectedSlot });
  if (!orderGate.canOrderNow) {
    throw new Error(orderGate.message);
  }
  ensureFoodDeliveryPointOptions();
  setFoodCheckoutPreviewOpen(true);
}

async function addMenuItemToCart(shopId, menuItem, quantity = 1, itemNote = '') {
  const orderGate = getFoodRuntimeOrderGate();
  if (!orderGate.canBrowseShops) {
    showFoodPopup('Food Hall Closed', orderGate.message, { isError: true, autoHideMs: 2600 });
    throw new Error(orderGate.message);
  }
  const nextQty = Math.max(1, Number(quantity || 1));
  const shop = getShopById(shopId);
  const resolvedShopId = Number(shop?.apiShopId || shop?.id || 0);
  if (!resolvedShopId) {
    throw new Error('Unable to resolve selected shop for cart.');
  }
  const activeShopId = state.food.cart.shopId;
  const normalizedShopId = String(resolvedShopId);
  const cleanNote = String(itemNote || '').trim();
  if (!isFoodDemoEnabled() && activeShopId && String(activeShopId) !== normalizedShopId) {
    const message = 'Orders are accepted only from a single shop at a time. Clear or checkout the current cart first.';
    showFoodPopup('Single Shop Rule', message, { isError: true, autoHideMs: 2600 });
    throw new Error(message);
  }
  const menuItemId = Number(menuItem.id);
  const addedLabel = cleanNote ? `${menuItem.name} (${cleanNote})` : menuItem.name;
  const payload = await api('/food/cart/items', {
    method: 'POST',
    headers: foodDemoRequestHeaders(),
    body: JSON.stringify({
      shop_id: resolvedShopId,
      menu_item_id: menuItemId,
      food_item_id: resolveLegacyFoodItemId(menuItem),
      name: menuItem.name,
      price: Number(menuItem.basePrice || menuItem.price || 0),
      quantity_delta: nextQty,
      item_note: cleanNote || null,
    }),
  });
  applyFoodCartPayload(payload);
  renderFoodCart();
  renderFoodShops();
  syncFoodOrderActionState();
  showFoodPopup('Cart Updated', `${addedLabel} x${nextQty} added to the cart.`, { autoHideMs: 1500 });
}

async function updateCartItemQty(cartKey, delta) {
  const key = String(cartKey || '');
  const item = state.food.cart.items.find((entry) => String(entry.cartKey) === key);
  if (!item) {
    return;
  }
  const previousQty = Number(item.quantity || 0);
  const changedQty = Math.max(1, Math.abs(Number(delta || 0)));
  if (Number(delta || 0) > 0) {
    const orderGate = getFoodRuntimeOrderGate();
    if (!orderGate.canBrowseShops) {
      throw new Error(orderGate.message);
    }
  }
  const resolvedShopId = Number(item.shopId || state.food.cart.shopId || 0);
  if (!resolvedShopId) {
    throw new Error('Unable to resolve cart shop for update.');
  }
  const payload = await api('/food/cart/items', {
    method: 'POST',
    headers: foodDemoRequestHeaders(),
    body: JSON.stringify({
      shop_id: resolvedShopId,
      menu_item_id: Number(item.menuItemId || 0),
      food_item_id: Number.isFinite(Number(item.foodItemId)) ? Number(item.foodItemId) : null,
      name: item.name,
      price: Number(item.price || 0),
      quantity_delta: Number(delta || 0),
      item_note: String(item.itemNote || '').trim() || null,
    }),
  });
  applyFoodCartPayload(payload, { syncSelectedShop: false });
  if (!state.food.cart.items.length && els.foodDeliveryBlockSelect) {
    els.foodDeliveryBlockSelect.value = '';
  }
  renderFoodCart();
  renderFoodShops();
  syncFoodOrderActionState();
  if (delta > 0) {
    showFoodPopup('Cart Updated', `${item.name} x${changedQty} added to the cart.`, { autoHideMs: 1300 });
  } else if (delta < 0) {
    const removedQty = Math.min(previousQty, changedQty);
    showFoodPopup('Cart Updated', `${item.name} x${removedQty} removed from the cart.`, { autoHideMs: 1300 });
  }
}

async function clearFoodCart({ silent = false } = {}) {
  if (authState.user?.role === 'student') {
    try {
      const payload = await api('/food/cart', { method: 'DELETE' });
      applyFoodCartPayload(payload, { syncSelectedShop: false });
    } catch (error) {
      if (!silent) {
        throw error;
      }
      applyFoodCartPayload({ items: [], shop_id: null, checkout_preview_open: false, checkout_delivery_point: null }, { syncSelectedShop: false });
    }
  } else {
    applyFoodCartPayload({ items: [], shop_id: null, checkout_preview_open: false, checkout_delivery_point: null }, { syncSelectedShop: false });
  }
  state.food.selectedShopId = '';
  if (els.foodDeliveryBlockSelect) {
    els.foodDeliveryBlockSelect.value = '';
  }
  setFoodCartModalTab('cart');
  renderFoodCart();
  renderFoodShops();
  syncFoodOrderActionState();
}

function renderFoodCart() {
  const cartItems = state.food.cart.items;
  const shop = getShopById(state.food.cart.shopId);
  const totalQty = cartItems.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
  const totalPrice = cartItems.reduce((sum, item) => sum + (Number(item.price || 0) * Number(item.quantity || 0)), 0);

  if (els.foodOpenCartBtn) {
    const label = cartItems.length ? `Open Cart (${totalQty})` : 'Open Cart';
    els.foodOpenCartBtn.textContent = label;
    els.foodOpenCartBtn.classList.toggle('has-items', cartItems.length > 0);
    if (cartItems.length > 0) {
      els.foodOpenCartBtn.setAttribute('data-cart-count', String(totalQty));
    } else {
      els.foodOpenCartBtn.removeAttribute('data-cart-count');
    }
  }

  if (els.foodCartSummary) {
    if (!cartItems.length) {
      els.foodCartSummary.textContent = 'No items in cart.';
    } else {
      els.foodCartSummary.textContent = `${shop?.name || 'Selected Shop'} (${shop?.block || '--'}) • ${totalQty} item(s) • ${formatMoney(totalPrice)}`;
    }
  }

  if (!els.foodCartList) {
    renderFoodCheckoutPreview();
    return;
  }
  els.foodCartList.innerHTML = '';
  if (!cartItems.length) {
    const row = buildEmptyStateRow({
      title: 'Your cart is empty.',
      description: 'Add items from one shop and proceed to the review step.',
      iconLabel: 'CART',
      ctaLabel: 'Browse Shops',
      ctaClassName: 'btn btn-primary',
      onCta: () => {
        closeFoodCartModal();
        if (els.foodShopGrid) {
          els.foodShopGrid.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      },
    });
    els.foodCartList.appendChild(row);
    renderFoodCheckoutPreview();
    return;
  }

  const orderGate = getFoodRuntimeOrderGate();
  const canIncrementCart = orderGate.canBrowseShops;
  for (const item of cartItems) {
    const row = document.createElement('div');
    row.className = 'list-item food-cart-item';
    row.innerHTML = `
      <span>${escapeHtml(item.name)} • ${formatMoney(item.price)}</span>
      <strong>x${Number(item.quantity || 0)}</strong>
    `;
    const actions = document.createElement('div');
    actions.className = 'food-cart-actions';
    const plusBtn = document.createElement('button');
    plusBtn.className = 'btn';
    plusBtn.type = 'button';
    plusBtn.textContent = '+';
    plusBtn.disabled = !canIncrementCart;
    if (!canIncrementCart) {
      plusBtn.title = orderGate.message;
    }
    plusBtn.addEventListener('click', () => {
      void updateCartItemQty(item.cartKey, 1).catch((error) => {
        setFoodStatus(error.message || 'Unable to update cart.', true);
      });
    });
    const minusBtn = document.createElement('button');
    minusBtn.className = 'btn';
    minusBtn.type = 'button';
    minusBtn.textContent = '-';
    minusBtn.addEventListener('click', () => {
      void updateCartItemQty(item.cartKey, -1).catch((error) => {
        setFoodStatus(error.message || 'Unable to update cart.', true);
      });
    });
    actions.append(plusBtn, minusBtn);
    row.appendChild(actions);
    els.foodCartList.appendChild(row);
  }
  renderFoodCheckoutPreview();
}

function displayFoodOrderStatus(order) {
  const raw = String(order?.status || '').toLowerCase();
  const shopName = String(order?.shop_name || 'shop');
  const prefix = FOOD_ORDER_STATUS_LABELS[raw] || asTitleCase(raw);
  if (raw === 'placed') {
    return `${prefix} ${shopName}`;
  }
  return prefix;
}

function setFoodAiOutput(message, isError = false) {
  if (!els.foodAiOutput) {
    return;
  }
  setUiStateMessage(els.foodAiOutput, message, {
    state: isError ? 'error' : 'neutral',
  });
}

async function renderFoodAiQuickChips() {
  if (!els.foodAiQuickChips) {
    return;
  }
  await ensureFoodCatalogLoaded({ preloadOnly: false });
  els.foodAiQuickChips.innerHTML = '';
  for (const craving of FOOD_AI_QUICK_CRAVINGS) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'btn btn-ghost food-ai-chip';
    chip.textContent = craving;
    chip.addEventListener('click', async () => {
      if (els.foodAiCravingInput) {
        els.foodAiCravingInput.value = craving;
      }
      try {
        await askChotuFoodAssistant(craving);
      } catch (error) {
        setFoodAiOutput(error.message || 'Unable to get suggestions right now.', true);
      }
    });
    els.foodAiQuickChips.appendChild(chip);
  }
}

async function buildChotuCatalogText() {
  await ensureFoodCatalogLoaded({ preloadOnly: true });
  const sourceShops = state.food.shops.length ? state.food.shops : FOOD_SHOP_DIRECTORY;
  const byGroup = new Map(FOOD_SHOP_GROUPS.map((group) => [group.key, []]));
  for (const shop of sourceShops) {
    const groupKey = String(shop.group || '').trim();
    if (byGroup.has(groupKey)) {
      byGroup.get(groupKey).push(shop);
    }
  }

  const lines = [];
  lines.push('Allowed LPU shops and blocks:');
  for (const group of FOOD_SHOP_GROUPS) {
    if (group.key === 'popular') {
      continue;
    }
    const rows = byGroup.get(group.key) || [];
    if (!rows.length) {
      continue;
    }
    const label = `${group.title}: ${rows.map((shop) => `${shop.name} (${shop.block})`).join(', ')}`;
    lines.push(label);
  }
  const popularRows = FOOD_POPULAR_SPOT_IDS
    .map((id) => sourceShops.find((shop) => shop.id === id))
    .filter(Boolean);
  if (popularRows.length) {
    lines.push(`Popular spots: ${popularRows.map((shop) => `${shop.name} (${shop.block})`).join(', ')}`);
  }
  return lines.join('\n');
}

async function askChotuFoodAssistant(cravingText = '') {
  const craving = String(cravingText || els.foodAiCravingInput?.value || '').trim();
  if (!craving) {
    throw new Error('Enter your craving first so Chotu can suggest outlets.');
  }
  await ensureFoodCatalogLoaded({ preloadOnly: true });
  const sourceShops = state.food.shops.length ? state.food.shops : FOOD_SHOP_DIRECTORY;
  if (!sourceShops.length) {
    throw new Error('Shop directory is still loading. Please retry in a moment.');
  }

  if (els.foodAiSuggestBtn) {
    els.foodAiSuggestBtn.disabled = true;
    els.foodAiSuggestBtn.textContent = 'Chotu Thinking...';
  }
  setFoodAiOutput('Chotu is analyzing your craving and matching the best outlets...');

  try {
    const puter = await getPuterClient();
    const prompt = [
      'You are Chotu, a friendly and practical food assistant for LPU Smart Campus Food Hall.',
      'User craving:',
      craving,
      await buildChotuCatalogText(),
      'Rules:',
      '- Suggest ONLY from the listed outlets.',
      '- Keep answer concise and readable.',
      '- Output format:',
      'Top Picks:',
      '1) Outlet name (Block) - why it matches',
      '2) ...',
      '3) ...',
      'Best budget option: Outlet name (Block) - one-line reason',
      'Fastest pickup option: Outlet name (Block) - one-line reason',
      'Top-rated popular pick: Outlet name (Block) - one-line reason',
      'Tone: helpful, campus-friendly.',
      'Max 150 words.',
    ].join('\n');

    const stream = await puter.chat(prompt, {
      model: AI_MODEL,
      stream: true,
    });
    if (els.foodAiOutput) {
      els.foodAiOutput.textContent = '';
    }
    for await (const part of stream) {
      if (part?.text && els.foodAiOutput) {
        els.foodAiOutput.textContent += part.text;
      }
    }
    log(`Chotu suggested outlets for craving: ${craving}`);
  } catch (error) {
    setFoodAiOutput(error.message || 'Chotu is unavailable right now. Please retry.', true);
    throw error;
  } finally {
    if (els.foodAiSuggestBtn) {
      els.foodAiSuggestBtn.disabled = false;
      els.foodAiSuggestBtn.textContent = 'Ask Chotu';
    }
  }
}

function renderFoodOrderStatusTimeline() {
  if (!els.foodOrderStatusTimeline) {
    return;
  }
  els.foodOrderStatusTimeline.innerHTML = '';
  const historyRows = Array.isArray(state.food.orderHistory) ? state.food.orderHistory : [];
  const orders = historyRows.length ? historyRows : (Array.isArray(state.food.orders) ? state.food.orders : []);
  const liveRows = orders
    .filter((order) => FOOD_CART_TIMELINE_STATUSES.has(String(order?.status || '').toLowerCase()))
    .sort((left, right) => foodOrderTimestampMs(right) - foodOrderTimestampMs(left));
  if (!liveRows.length) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'No live cart updates right now.';
    els.foodOrderStatusTimeline.appendChild(row);
    return;
  }
  for (const order of liveRows.slice(0, 8)) {
    const item = state.food.items.find((entry) => entry.id === order.food_item_id);
    const row = document.createElement('div');
    row.className = 'list-item food-order-stage';
    row.innerHTML = `
      <span>${escapeHtml(item?.name || `Item #${order.food_item_id}`)} • ${escapeHtml(order.shop_name || '--')}</span>
      <span>${escapeHtml(displayFoodOrderStatus(order))}</span>
    `;
    els.foodOrderStatusTimeline.appendChild(row);
  }
}

function renderFoodAdminOrderOptions() {
  if (!els.foodAdminOrderSelect) {
    return;
  }
  const previous = Number(els.foodAdminOrderSelect.value || 0);
  els.foodAdminOrderSelect.innerHTML = '';
  const rows = Array.isArray(state.food.orders) ? state.food.orders : [];
  if (!rows.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'No orders available';
    els.foodAdminOrderSelect.appendChild(option);
    els.foodAdminOrderSelect.disabled = true;
    return;
  }
  for (const order of rows) {
    const option = document.createElement('option');
    option.value = String(order.id);
    option.textContent = `#${order.id} • ${order.shop_name || 'Shop'} • ${asTitleCase(order.status)}`;
    els.foodAdminOrderSelect.appendChild(option);
  }
  els.foodAdminOrderSelect.disabled = false;
  if (previous && rows.some((row) => row.id === previous)) {
    els.foodAdminOrderSelect.value = String(previous);
  }
}

async function updateFoodOrderStatus() {
  if (!els.foodAdminOrderSelect || !els.foodAdminStatusSelect) {
    return;
  }
  const orderId = Number(els.foodAdminOrderSelect.value || 0);
  const status = String(els.foodAdminStatusSelect.value || '').trim();
  if (!orderId || !status) {
    throw new Error('Select order and status before updating.');
  }
  await api(`/food/orders/${orderId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
  setFoodAdminStatus('Live order status updated.');
  await refreshFoodModule();
}

function setRemedialFacultyStatus(message, isError = false, state = 'neutral') {
  if (!els.remedialFacultyStatus) {
    return;
  }
  setUiStateMessage(els.remedialFacultyStatus, message, {
    state: isError ? 'error' : state,
  });
}

function setRemedialStudentStatus(message, isError = false, state = 'neutral') {
  if (!els.remedialStudentStatus) {
    return;
  }
  setUiStateMessage(els.remedialStudentStatus, message, {
    state: isError ? 'error' : state,
  });
}

function setFacultyMessageStatus(message, isError = false, state = 'neutral') {
  if (!els.facultyMessageStatus) {
    return;
  }
  setUiStateMessage(els.facultyMessageStatus, message, {
    state: isError ? 'error' : state,
  });
}

function setDirectEmailStatus(message, isError = false, state = 'neutral') {
  if (!els.directEmailStatus) {
    return;
  }
  setUiStateMessage(els.directEmailStatus, message, {
    state: isError ? 'error' : state,
  });
}

function geolocationErrorText(error) {
  const code = Number(error?.code || 0);
  if (code === 1) {
    return 'Location access denied. Allow location for this site (lock icon in address bar), then retry.';
  }
  if (code === 2) {
    return 'Unable to detect current location. Check GPS/network and retry.';
  }
  if (code === 3) {
    return 'Location request timed out. Retry in an open area.';
  }
  return 'Location verification failed. Retry after enabling device location.';
}

function isFoodModuleActive() {
  return getSanitizedModuleKey(state.ui.activeModule) === 'food';
}

function canMonitorFoodLocation() {
  return Boolean(authState.user && authState.user.role === 'student' && isFoodModuleActive());
}

function stopFoodLocationMonitoring() {
  const watchId = state.food.location.watchId;
  if (watchId !== null && navigator.geolocation) {
    try {
      navigator.geolocation.clearWatch(watchId);
    } catch (_) {
      // Ignore clear failures from stale watcher ids.
    }
  }
  state.food.location.watchId = null;
  state.food.location.monitoring = false;
  state.food.location.monitorBusy = false;
  updateFoodLocationActionState();
}

function isFoodLocationFresh() {
  const stamp = Number(state.food.location.lastVerifiedAtMs || 0);
  if (!stamp) {
    return false;
  }
  return (Date.now() - stamp) <= FOOD_LOCATION_MAX_STALE_MS;
}

function formatLocationStatusMessage(baseMessage, { withAccuracy = true, source = 'manual' } = {}) {
  const chunks = [String(baseMessage || '').trim()].filter(Boolean);
  if (state.food.location.monitoring && source !== 'manual') {
    chunks.push('GPS monitoring active');
  }
  if (state.food.location.verified && !isFoodLocationFresh()) {
    chunks.push('GPS refresh required');
  }
  if (withAccuracy && Number.isFinite(state.food.location.accuracyM)) {
    chunks.push(`Accuracy ±${Math.round(state.food.location.accuracyM)}m`);
  }
  return chunks.join(' • ');
}

async function verifyFoodLocationCoordinates(latitude, longitude, accuracyM, { silent = false, source = 'manual' } = {}) {
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    throw new Error('Invalid location coordinates from device.');
  }
  const result = await api('/food/location/verify', {
    method: 'POST',
    body: JSON.stringify({
      latitude,
      longitude,
      accuracy_m: Number.isFinite(accuracyM) ? accuracyM : null,
    }),
  });
  state.food.location.latitude = latitude;
  state.food.location.longitude = longitude;
  state.food.location.accuracyM = Number.isFinite(accuracyM) ? accuracyM : null;
  state.food.location.lastVerifiedAtMs = Date.now();
  state.food.location.allowed = Boolean(result?.allowed);
  state.food.location.verified = true;
  state.food.location.message = String(result?.message || 'Location verified.');
  if (!silent || state.food.location.monitoring) {
    const statusMessage = formatLocationStatusMessage(state.food.location.message, { source });
    setFoodLocationStatus(statusMessage, state.food.location.allowed ? 'ok' : 'error');
  }
  syncFoodOrderActionState();
  return Boolean(result?.allowed);
}

function startFoodLocationMonitoring() {
  if (!canMonitorFoodLocation()) {
    stopFoodLocationMonitoring();
    return;
  }
  if (!navigator.geolocation) {
    stopFoodLocationMonitoring();
    return;
  }
  if (state.food.location.watchId !== null) {
    state.food.location.monitoring = true;
    updateFoodLocationActionState();
    return;
  }

  const watchId = navigator.geolocation.watchPosition(
    (geo) => {
      if (!canMonitorFoodLocation()) {
        stopFoodLocationMonitoring();
        return;
      }
      if (state.food.location.monitorBusy || state.food.location.checking) {
        return;
      }
      state.food.location.monitorBusy = true;
      const latitude = Number(geo?.coords?.latitude);
      const longitude = Number(geo?.coords?.longitude);
      const accuracyM = Number(geo?.coords?.accuracy || 0);
      void verifyFoodLocationCoordinates(latitude, longitude, accuracyM, { silent: true, source: 'monitor' })
        .catch((error) => {
          const message = error?.code ? geolocationErrorText(error) : (error?.message || 'GPS monitoring update failed.');
          state.food.location.allowed = false;
          state.food.location.verified = false;
          state.food.location.lastVerifiedAtMs = 0;
          state.food.location.message = message;
          setFoodLocationStatus(message, 'error');
          syncFoodOrderActionState();
        })
        .finally(() => {
          state.food.location.monitorBusy = false;
        });
    },
    (error) => {
      const message = geolocationErrorText(error);
      state.food.location.allowed = false;
      state.food.location.verified = false;
      state.food.location.lastVerifiedAtMs = 0;
      state.food.location.message = message;
      setFoodLocationStatus(message, 'error');
      syncFoodOrderActionState();
      stopFoodLocationMonitoring();
    },
    {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 7000,
    }
  );

  state.food.location.watchId = watchId;
  state.food.location.monitoring = true;
  updateFoodLocationActionState();
}

function syncFoodLocationMonitoringByModule() {
  if (!canMonitorFoodLocation() || !state.food.location.verified) {
    stopFoodLocationMonitoring();
    return;
  }
  startFoodLocationMonitoring();
}

function updateFoodLocationActionState() {
  const checking = Boolean(state.food.location.checking);
  const monitoring = Boolean(state.food.location.monitoring);
  const fresh = isFoodLocationFresh();
  if (els.foodEnableLocationBtn) {
    els.foodEnableLocationBtn.disabled = checking;
    if (checking) {
      els.foodEnableLocationBtn.textContent = 'Checking...';
    } else if (monitoring) {
      els.foodEnableLocationBtn.textContent = 'GPS Monitoring On';
    } else if (state.food.location.verified && !fresh) {
      els.foodEnableLocationBtn.textContent = 'Refresh GPS Lock';
    } else if (state.food.location.verified) {
      els.foodEnableLocationBtn.textContent = 'Location Enabled';
    } else {
      els.foodEnableLocationBtn.textContent = 'Enable Location Access';
    }
  }
}

function requestCurrentPosition(options = {}) {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Location API unavailable in this browser.'));
      return;
    }
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 20000,
      ...options,
    });
  });
}

async function getGeoPermissionState() {
  try {
    if (!navigator.permissions || typeof navigator.permissions.query !== 'function') {
      return 'unknown';
    }
    const permission = await navigator.permissions.query({ name: 'geolocation' });
    return String(permission?.state || 'unknown');
  } catch (_) {
    return 'unknown';
  }
}

async function requestCurrentPositionReliable(forcePrompt = false) {
  const primaryOptions = {
    enableHighAccuracy: true,
    timeout: 14000,
    maximumAge: forcePrompt ? 0 : 15000,
  };
  try {
    return await requestCurrentPosition(primaryOptions);
  } catch (error) {
    if (Number(error?.code || 0) !== 3) {
      throw error;
    }
    return requestCurrentPosition({
      enableHighAccuracy: false,
      timeout: 9000,
      maximumAge: 30000,
    });
  }
}

async function verifyFoodLocationGate({ forcePrompt = false, silent = false } = {}) {
  if (!authState.user || authState.user.role !== 'student') {
    return true;
  }
  if (state.food.location.checking) {
    return Boolean(state.food.location.allowed);
  }
  if (!forcePrompt && state.food.location.verified && state.food.location.allowed && isFoodLocationFresh()) {
    startFoodLocationMonitoring();
    return true;
  }
  if (!navigator.geolocation) {
    state.food.location.allowed = false;
    state.food.location.verified = false;
    state.food.location.lastVerifiedAtMs = 0;
    state.food.location.message = 'Location API unavailable in this browser.';
    setFoodLocationStatus(state.food.location.message, 'error');
    syncFoodOrderActionState();
    return false;
  }
  if (!window.isSecureContext) {
    state.food.location.allowed = false;
    state.food.location.verified = false;
    state.food.location.lastVerifiedAtMs = 0;
    state.food.location.message = 'Location requires a secure context (HTTPS or localhost).';
    setFoodLocationStatus(state.food.location.message, 'error');
    syncFoodOrderActionState();
    return false;
  }
  state.food.location.checking = true;
  if (forcePrompt) {
    state.food.location.requestedOnce = true;
  }
  let permissionState = 'unknown';
  if (!forcePrompt) {
    permissionState = await getGeoPermissionState();
  }
  if (permissionState === 'denied' && !forcePrompt) {
    state.food.location.allowed = false;
    state.food.location.verified = false;
    state.food.location.lastVerifiedAtMs = 0;
    state.food.location.message = 'Location permission appears blocked. Allow location for this site and tap "Enable Location Access" again.';
    setFoodLocationStatus(state.food.location.message, 'error');
    syncFoodOrderActionState();
    state.food.location.checking = false;
    updateFoodLocationActionState();
    return false;
  }
  updateFoodLocationActionState();
  if (!silent) {
    setFoodLocationStatus('Checking campus location…', 'warn');
  }

  try {
    const geo = await requestCurrentPositionReliable(forcePrompt);
    const latitude = Number(geo?.coords?.latitude);
    const longitude = Number(geo?.coords?.longitude);
    const accuracyM = Number(geo?.coords?.accuracy || 0);
    const allowed = await verifyFoodLocationCoordinates(latitude, longitude, accuracyM, { silent, source: 'manual' });
    if (allowed) {
      startFoodLocationMonitoring();
      if (!silent) {
        setFoodLocationStatus(
          formatLocationStatusMessage(state.food.location.message, { source: 'monitor' }),
          state.food.location.allowed ? 'ok' : 'error'
        );
      }
    } else {
      stopFoodLocationMonitoring();
    }
    return allowed;
  } catch (error) {
    let permissionStateAfterError = permissionState;
    if (forcePrompt || permissionStateAfterError === 'unknown') {
      permissionStateAfterError = await getGeoPermissionState();
    }
    const deniedByBrowser = Number(error?.code || 0) === 1;
    const blockedBySettings = permissionStateAfterError === 'denied';
    const message = blockedBySettings
      ? 'Location permission is blocked in browser settings. Allow location for this site, then retry.'
      : (deniedByBrowser
        ? 'Location request was denied. Tap "Enable Location Access" and allow GPS in the browser popup.'
        : (error?.code ? geolocationErrorText(error) : (error?.message || 'Location check failed.')));
    state.food.location.allowed = false;
    state.food.location.verified = false;
    state.food.location.lastVerifiedAtMs = 0;
    state.food.location.message = message;
    setFoodLocationStatus(message, 'error');
    stopFoodLocationMonitoring();
    syncFoodOrderActionState();
    return false;
  } finally {
    state.food.location.checking = false;
    updateFoodLocationActionState();
  }
}

function asTitleCase(rawText) {
  const text = String(rawText || '').trim();
  if (!text) {
    return '--';
  }
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
}

function formatMoney(value) {
  const amount = Number(value || 0);
  if (!Number.isFinite(amount)) {
    return 'INR 0.00';
  }
  return `INR ${amount.toFixed(2)}`;
}

function renderFoodItemOptions() {
  if (!els.foodItemSelect) {
    return;
  }
  const previous = Number(els.foodItemSelect.value);
  els.foodItemSelect.innerHTML = '';
  if (!state.food.items.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'No active items';
    els.foodItemSelect.appendChild(option);
    els.foodItemSelect.disabled = true;
    return;
  }

  for (const item of state.food.items) {
    const option = document.createElement('option');
    option.value = String(item.id);
    option.textContent = `${item.name} (${formatMoney(item.price)})`;
    els.foodItemSelect.appendChild(option);
  }
  els.foodItemSelect.disabled = false;
  if (previous && state.food.items.some((item) => item.id === previous)) {
    els.foodItemSelect.value = String(previous);
  }
}

function dayIndexFromISODate(dateIso) {
  const dateObj = parseISODateLocal(dateIso);
  if (!dateObj || Number.isNaN(dateObj.getTime())) {
    return null;
  }
  return (dateObj.getDay() + 6) % 7;
}

function buildFoodSlotHintsForDate(orderDate, timetableRows) {
  const rows = Array.isArray(timetableRows) ? timetableRows : [];
  if (!rows.length) {
    return {};
  }
  const orderDateText = String(orderDate || '').trim();
  const dayIndex = dayIndexFromISODate(orderDateText);
  const sameDayRows = rows.filter((row) => {
    const classDate = String(row.class_date || '').trim();
    if (classDate && classDate === orderDateText) {
      return true;
    }
    if (!classDate && Number.isInteger(dayIndex)) {
      return Number(row.weekday) === dayIndex;
    }
    return false;
  });
  if (!sameDayRows.length) {
    return {};
  }

  const classIntervals = sameDayRows
    .map((row) => ({
      start: toMinutes(row.start_time),
      end: toMinutes(row.end_time),
    }))
    .filter((row) => Number.isFinite(row.start) && Number.isFinite(row.end) && row.end > row.start)
    .sort((a, b) => a.start - b.start);

  const breakIntervals = [];
  for (let index = 0; index < classIntervals.length - 1; index += 1) {
    const left = classIntervals[index];
    const right = classIntervals[index + 1];
    if ((right.start - left.end) >= 20) {
      breakIntervals.push({ start: left.end, end: right.start });
    }
  }

  const firstStart = classIntervals[0]?.start ?? null;
  const lastEnd = classIntervals[classIntervals.length - 1]?.end ?? null;

  const hints = {};
  for (const slot of state.food.slots) {
    const slotStart = toMinutes(slot.start_time);
    const slotEnd = toMinutes(slot.end_time);
    const classOverlap = sameDayRows.some((row) => {
      const classStart = toMinutes(row.start_time);
      const classEnd = toMinutes(row.end_time);
      return slotStart < classEnd && classStart < slotEnd;
    });
    if (classOverlap) {
      hints[String(slot.id)] = { kind: 'busy', label: 'Class ongoing' };
      continue;
    }

    const overlapBreakWindow = breakIntervals.some((range) => slotStart < range.end && range.start < slotEnd);
    if (overlapBreakWindow) {
      hints[String(slot.id)] = { kind: 'recommended', label: 'Your break hour ★' };
      continue;
    }

    // Keep non-class, in-day slots as soft suggestions so users get useful defaults.
    if (
      Number.isFinite(firstStart)
      && Number.isFinite(lastEnd)
      && slotStart >= (firstStart - 60)
      && slotEnd <= (lastEnd + 60)
    ) {
      hints[String(slot.id)] = { kind: 'recommended', label: 'Possible break slot' };
    }
  }
  return hints;
}

async function refreshFoodSlotHints(orderDate) {
  const dateText = String(orderDate || '').trim();
  if (authState.user?.role !== 'student' || !dateText) {
    state.food.slotHintsById = {};
    state.food.slotHintsDate = '';
    return;
  }

  const weekStart = weekStartISO(dateText);
  const cached = state.student.timetableCache[weekStart];
  let rows = Array.isArray(cached?.classes) ? cached.classes : null;

  if (!rows) {
    try {
      const payload = await fetchStudentTimetableWeek(weekStart, { forceNetwork: true });
      rows = Array.isArray(payload.classes) ? payload.classes : [];
    } catch (_) {
      rows = [];
    }
  }

  state.food.slotHintsById = buildFoodSlotHintsForDate(dateText, rows);
  state.food.slotHintsDate = dateText;
}

function renderFoodSlotOptions() {
  if (!els.foodSlotSelect) {
    return;
  }
  const previous = Number(els.foodSlotSelect.value);
  const now = new Date();
  const nowMinutes = (now.getHours() * 60) + now.getMinutes();
  const selectedDate = resolveFoodOrderDateValue();
  const isTodaySelected = selectedDate === todayISO();
  const demoEnabled = isFoodDemoEnabled();
  const selectableSlotIds = [];
  els.foodSlotSelect.innerHTML = '';
  if (!state.food.slots.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'No available slots';
    els.foodSlotSelect.appendChild(option);
    els.foodSlotSelect.disabled = true;
    return;
  }

  for (const slot of state.food.slots) {
    const hint = state.food.slotHintsById?.[String(slot.id)] || null;
    const option = document.createElement('option');
    option.value = String(slot.id);
    const baseLabel = `${slot.label} (${formatTime(slot.start_time)} - ${formatTime(slot.end_time)})`;
    const slotEndMinutes = toMinutes(slot.end_time);
    const slotElapsed = !demoEnabled && isTodaySelected && Number.isFinite(slotEndMinutes) && slotEndMinutes <= nowMinutes;
    if (slotElapsed) {
      option.disabled = true;
      option.textContent = `${baseLabel} • Closed`;
    } else {
      const suffix = hint?.label || (demoEnabled ? 'Demo override' : '');
      option.textContent = suffix ? `${baseLabel} • ${suffix}` : baseLabel;
      selectableSlotIds.push(slot.id);
    }
    els.foodSlotSelect.appendChild(option);
  }
  if (!selectableSlotIds.length) {
    els.foodSlotSelect.disabled = true;
    if (els.foodSlotSelect.options.length) {
      els.foodSlotSelect.value = String(els.foodSlotSelect.options[0].value || '');
    }
    els.foodSlotSelect.dataset.hint = 'none';
    return;
  }
  els.foodSlotSelect.disabled = false;
  if (previous && selectableSlotIds.includes(previous)) {
    els.foodSlotSelect.value = String(previous);
  } else {
    const recommended = state.food.slots.find(
      (slot) => selectableSlotIds.includes(slot.id) && state.food.slotHintsById?.[String(slot.id)]?.kind === 'recommended',
    );
    if (recommended) {
      els.foodSlotSelect.value = String(recommended.id);
    } else {
      els.foodSlotSelect.value = String(selectableSlotIds[0]);
    }
  }
  const selectedHint = state.food.slotHintsById?.[String(els.foodSlotSelect.value || '')] || null;
  els.foodSlotSelect.dataset.hint = selectedHint?.kind || 'none';
}

function isFoodOrderFinal(order) {
  const status = String(order?.status || '').trim().toLowerCase();
  return FOOD_FINAL_ORDER_STATUSES.has(status);
}

function parseFoodDateTime(rawValue) {
  if (!rawValue) {
    return null;
  }
  if (rawValue instanceof Date) {
    return Number.isNaN(rawValue.getTime()) ? null : rawValue;
  }
  if (typeof rawValue === 'number') {
    const fromEpoch = new Date(rawValue);
    return Number.isNaN(fromEpoch.getTime()) ? null : fromEpoch;
  }
  const textValue = String(rawValue).trim();
  if (!textValue) {
    return null;
  }
  const normalized = textValue.replace(' ', 'T');
  const naivePattern = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?)?$/;
  const naiveMatch = normalized.match(naivePattern);
  if (naiveMatch) {
    const year = Number(naiveMatch[1]);
    const month = Number(naiveMatch[2]);
    const day = Number(naiveMatch[3]);
    const hour = Number(naiveMatch[4] || 0);
    const minute = Number(naiveMatch[5] || 0);
    const second = Number(naiveMatch[6] || 0);
    const milliRaw = String(naiveMatch[7] || '0').slice(0, 3);
    const millisecond = Number(milliRaw.padEnd(3, '0'));
    // Server stores food-order timestamps as UTC-naive strings.
    // Treating naive values as UTC preserves correct real-world local display.
    const utcDate = new Date(Date.UTC(year, month - 1, day, hour, minute, second, millisecond));
    return Number.isNaN(utcDate.getTime()) ? null : utcDate;
  }
  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function foodOrderTimestampMs(order) {
  const primary = order?.last_status_updated_at || order?.updated_at || order?.created_at || null;
  const parsed = parseFoodDateTime(primary);
  return parsed ? parsed.getTime() : 0;
}

function foodTimestampLabel(rawValue, fallbackText = '--') {
  const parsed = parseFoodDateTime(rawValue);
  if (!parsed) {
    return fallbackText;
  }
  return parsed.toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

function foodFreshnessLabel(syncedAtMs) {
  const ts = Number(syncedAtMs || 0);
  if (!Number.isFinite(ts) || ts <= 0) {
    return 'Updated --';
  }
  const deltaSeconds = Math.max(0, Math.floor((Date.now() - ts) / 1000));
  if (deltaSeconds <= 1) {
    return 'Updated just now';
  }
  if (deltaSeconds < 60) {
    return `Updated ${deltaSeconds}s ago`;
  }
  const deltaMinutes = Math.floor(deltaSeconds / 60);
  if (deltaMinutes < 60) {
    return `Updated ${deltaMinutes}m ago`;
  }
  const deltaHours = Math.floor(deltaMinutes / 60);
  return `Updated ${deltaHours}h ago`;
}

function renderFoodFreshnessIndicators() {
  const label = foodFreshnessLabel(state.food.lastOrdersSyncAtMs);
  if (els.foodOrdersPanelFreshness) {
    els.foodOrdersPanelFreshness.textContent = label;
  }
  if (els.foodPaymentRecoveryFreshness) {
    els.foodPaymentRecoveryFreshness.textContent = label;
  }
  if (els.foodOrdersListFreshness) {
    els.foodOrdersListFreshness.textContent = label;
  }
  const pulseActive = Number(state.food.syncPulseUntilMs || 0) > Date.now();
  if (els.foodOrdersPanel) {
    els.foodOrdersPanel.classList.toggle('is-sync-pulse', pulseActive);
  }
}

function triggerFoodOrdersSyncPulse(durationMs = 1250) {
  if (!els.foodOrdersPanel) {
    return;
  }
  els.foodOrdersPanel.classList.remove('is-sync-pulse');
  // Restart CSS animation in a predictable way.
  els.foodOrdersPanel.offsetWidth;
  els.foodOrdersPanel.classList.add('is-sync-pulse');
  if (foodOrdersPulseTimer) {
    window.clearTimeout(foodOrdersPulseTimer);
    foodOrdersPulseTimer = null;
  }
  foodOrdersPulseTimer = window.setTimeout(() => {
    if (els.foodOrdersPanel) {
      els.foodOrdersPanel.classList.remove('is-sync-pulse');
    }
    foodOrdersPulseTimer = null;
  }, Math.max(600, Number(durationMs || 0)));
}

function markFoodOrdersFreshness({ changed = false } = {}) {
  const nowMs = Date.now();
  state.food.lastOrdersSyncAtMs = nowMs;
  if (changed) {
    state.food.lastOrdersChangeAtMs = nowMs;
    state.food.syncPulseUntilMs = nowMs + 2 * 1000;
    triggerFoodOrdersSyncPulse();
  }
  renderFoodFreshnessIndicators();
}

function buildFoodOrdersFreshnessDigest(rows = [], paymentRecovery = []) {
  const orderPart = (Array.isArray(rows) ? rows : [])
    .map((row) => ([
      Number(row?.id || 0),
      String(row?.status || '').trim().toLowerCase(),
      String(row?.payment_status || '').trim().toLowerCase(),
      String(row?.last_status_updated_at || row?.updated_at || row?.created_at || ''),
      Number(row?.rating_stars || 0),
      String(row?.rating_locked_at || ''),
    ].join(':')))
    .sort()
    .join('|');

  const recoveryPart = (Array.isArray(paymentRecovery) ? paymentRecovery : [])
    .map((row) => ([
      String(row?.payment_reference || ''),
      Number(row?.pending_order_count || 0),
      String(row?.status || '').trim().toLowerCase(),
      String(row?.updated_at || ''),
    ].join(':')))
    .sort()
    .join('|');

  return `${orderPart}||${recoveryPart}`;
}

function buildFoodLiveFeedSnapshot(order) {
  return {
    status: String(order?.status || '').trim().toLowerCase(),
    paymentStatus: String(order?.payment_status || 'pending').trim().toLowerCase(),
  };
}

function syncFoodOrderLiveFeedNotifications(rows) {
  if (authState.user?.role !== 'student') {
    state.food.liveFeedByOrderId.clear();
    state.food.liveFeedInitialized = false;
    return;
  }
  const sourceRows = Array.isArray(rows) ? rows : [];
  const byId = new Map();
  for (const row of sourceRows) {
    const id = Number(row?.id || 0);
    if (!id) {
      continue;
    }
    const existing = byId.get(id);
    if (!existing || foodOrderTimestampMs(row) >= foodOrderTimestampMs(existing)) {
      byId.set(id, row);
    }
  }

  if (!state.food.liveFeedInitialized) {
    state.food.liveFeedByOrderId.clear();
    for (const [id, row] of byId.entries()) {
      state.food.liveFeedByOrderId.set(id, buildFoodLiveFeedSnapshot(row));
    }
    state.food.liveFeedInitialized = true;
    return;
  }

  const changes = [];
  for (const [id, row] of byId.entries()) {
    const nextSnapshot = buildFoodLiveFeedSnapshot(row);
    const previousSnapshot = state.food.liveFeedByOrderId.get(id);
    if (!previousSnapshot) {
      const ageMs = Date.now() - foodOrderTimestampMs(row);
      if (ageMs >= 0 && ageMs <= 3 * 60 * 1000) {
        const shopName = String(row?.shop_name || 'selected shop').trim();
        changes.push({
          isError: false,
          title: 'Order Created',
          message: `Order #${id} placed with ${shopName}.`,
        });
      }
      state.food.liveFeedByOrderId.set(id, nextSnapshot);
      continue;
    }
    if (previousSnapshot.status !== nextSnapshot.status) {
      const statusLabel = asTitleCase((nextSnapshot.status || 'placed').replaceAll('_', ' '));
      changes.push({
        isError: FOOD_WARN_ORDER_STATUSES.has(nextSnapshot.status),
        title: 'Order Status Update',
        message: `Order #${id} is now ${statusLabel}.`,
      });
    } else if (previousSnapshot.paymentStatus !== nextSnapshot.paymentStatus) {
      const paymentLabel = asTitleCase(nextSnapshot.paymentStatus || 'pending');
      changes.push({
        isError: FOOD_PAYMENT_FAILURE_STATES.has(nextSnapshot.paymentStatus),
        title: 'Payment Status Update',
        message: `Order #${id} payment is ${paymentLabel}.`,
      });
    }
    state.food.liveFeedByOrderId.set(id, nextSnapshot);
  }

  for (const key of Array.from(state.food.liveFeedByOrderId.keys())) {
    if (!byId.has(key)) {
      state.food.liveFeedByOrderId.delete(key);
    }
  }

  if (!changes.length) {
    return;
  }
  const [first] = changes;
  const moreCount = Math.max(0, changes.length - 1);
  const mergedMessage = moreCount > 0
    ? `${first.message} (+${moreCount} more live update${moreCount > 1 ? 's' : ''})`
    : first.message;
  showFoodPopup(first.title, mergedMessage, { isError: first.isError, autoHideMs: 4200 });
}

function syncFoodOrderInState(updatedOrder) {
  if (!updatedOrder || !Number(updatedOrder.id)) {
    return;
  }
  const orderId = Number(updatedOrder.id);
  for (const bucket of [state.food.orders, state.food.orderHistory]) {
    if (!Array.isArray(bucket) || !bucket.length) {
      continue;
    }
    const index = bucket.findIndex((row) => Number(row?.id || 0) === orderId);
    if (index >= 0) {
      bucket[index] = updatedOrder;
    }
  }
}

function mergeFoodOrdersIntoState(orderRows, { assumeVerifiedPayment = false } = {}) {
  const normalizedRows = (Array.isArray(orderRows) ? orderRows : [])
    .map((row) => {
      const id = Number(row?.id || 0);
      if (!id) {
        return null;
      }
      const nextRow = { ...row, id };
      if (assumeVerifiedPayment) {
        const currentStatus = String(nextRow.status || '').trim().toLowerCase();
        nextRow.payment_status = 'paid';
        nextRow.payment_provider = String(nextRow.payment_provider || 'razorpay');
        if (currentStatus === 'placed') {
          nextRow.status = 'verified';
        }
        const verifiedAt = nextRow.verified_at || new Date().toISOString();
        nextRow.verified_at = verifiedAt;
        nextRow.last_status_updated_at = nextRow.last_status_updated_at || verifiedAt;
      }
      return nextRow;
    })
    .filter(Boolean);
  if (!normalizedRows.length) {
    return;
  }

  const mergeBucket = (rows) => {
    const byId = new Map();
    for (const row of Array.isArray(rows) ? rows : []) {
      const id = Number(row?.id || 0);
      if (!id || byId.has(id)) {
        continue;
      }
      byId.set(id, row);
    }
    for (const row of normalizedRows) {
      const id = Number(row.id || 0);
      byId.set(id, { ...(byId.get(id) || {}), ...row });
    }
    return Array.from(byId.values()).sort((left, right) => {
      const delta = foodOrderTimestampMs(right) - foodOrderTimestampMs(left);
      if (delta !== 0) {
        return delta;
      }
      return Number(right?.id || 0) - Number(left?.id || 0);
    });
  };

  state.food.orders = mergeBucket(state.food.orders);
  state.food.orderHistory = mergeBucket(state.food.orderHistory);
  state.food.ordersTab = 'current';

  const digestRows = state.food.orderHistory.length ? state.food.orderHistory : state.food.orders;
  state.food.freshnessDigest = buildFoodOrdersFreshnessDigest(digestRows, state.food.paymentRecovery);
  markFoodOrdersFreshness({ changed: true });
  syncFoodOrderLiveFeedNotifications(digestRows);
}

async function updateFoodOrderRating(orderId, stars, { confirmFinal = false } = {}) {
  const id = Number(orderId || 0);
  if (!id || authState.user?.role !== 'student') {
    return;
  }
  const boundedStars = Math.max(1, Math.min(5, Number(stars || 0)));
  state.food.ratingBusyOrderIds.add(id);
  renderFoodOrders();
  try {
    const updated = await api(`/food/orders/${id}/rating`, {
      method: 'PATCH',
      body: JSON.stringify({ stars: boundedStars, confirm_final: Boolean(confirmFinal) }),
    });
    syncFoodOrderInState(updated);
    try {
      const shops = await api(`/food/shops?active_only=${isFoodDemoEnabled() ? 'false' : 'true'}`);
      state.food.shops = hydrateApiShops(shops);
      renderFoodShops();
    } catch (_) {
      // Ratings should still save even if shop-list refresh is delayed.
    }
    renderFoodOrderStatusTimeline();
    setFoodStatus(`Rated order #${id} with ${boundedStars} star${boundedStars > 1 ? 's' : ''}. Rating is now locked.`, false);
  } catch (error) {
    setFoodStatus(error.message || 'Unable to update rating right now.', true);
  } finally {
    state.food.ratingBusyOrderIds.delete(id);
    renderFoodOrders();
  }
}

async function confirmFoodOrderDeliveryBatch(orderIds, { labelPrefix = 'Order' } = {}) {
  const normalizedIds = Array.from(new Set((Array.isArray(orderIds) ? orderIds : [])
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value) && value > 0)));
  if (!normalizedIds.length || authState.user?.role !== 'student') {
    return;
  }
  if (normalizedIds.some((id) => state.food.deliveryConfirmBusyOrderIds.has(id))) {
    return;
  }
  for (const id of normalizedIds) {
    state.food.deliveryConfirmBusyOrderIds.add(id);
  }
  renderFoodOrders();
  try {
    const settled = await Promise.allSettled(
      normalizedIds.map((id) => api(`/food/orders/${id}/confirm-delivery`, { method: 'POST' })),
    );
    const successful = [];
    let firstError = '';
    for (const result of settled) {
      if (result.status === 'fulfilled') {
        const updatedOrder = result.value;
        successful.push(updatedOrder);
        syncFoodOrderInState(updatedOrder);
      } else if (!firstError) {
        firstError = result.reason?.message || 'Unable to confirm delivery right now.';
      }
    }
    if (successful.length) {
      state.food.ordersTab = 'previous';
      const rowLabel = successful.length === 1
        ? `${labelPrefix} marked as delivered.`
        : `${labelPrefix} marked delivered for ${successful.length} item(s).`;
      showFoodPopup('Delivery Confirmed', `${rowLabel} Please rate to lock your feedback.`, { autoHideMs: 3600 });
      setFoodStatus(`${rowLabel}`, false);
      await refreshFoodModule();
    }
    if (firstError && successful.length !== normalizedIds.length) {
      setFoodStatus(firstError, true);
    }
  } catch (error) {
    setFoodStatus(error.message || 'Unable to confirm delivery right now.', true);
  } finally {
    for (const id of normalizedIds) {
      state.food.deliveryConfirmBusyOrderIds.delete(id);
    }
    renderFoodOrders();
  }
}

async function confirmFoodOrderDelivered(orderId) {
  const id = Number(orderId || 0);
  if (!id) {
    return;
  }
  await confirmFoodOrderDeliveryBatch([id], { labelPrefix: `Order #${id}` });
}

function updateFoodOrdersTabUi() {
  const currentTab = state.food.ordersTab === 'previous' ? 'previous' : 'current';
  if (els.foodOrdersTabCurrent) {
    els.foodOrdersTabCurrent.classList.toggle('is-active', currentTab === 'current');
    els.foodOrdersTabCurrent.setAttribute('aria-selected', currentTab === 'current' ? 'true' : 'false');
  }
  if (els.foodOrdersTabPrevious) {
    els.foodOrdersTabPrevious.classList.toggle('is-active', currentTab === 'previous');
    els.foodOrdersTabPrevious.setAttribute('aria-selected', currentTab === 'previous' ? 'true' : 'false');
  }
}

function resolveRecoveryShopName(orderIds) {
  const wanted = new Set((Array.isArray(orderIds) ? orderIds : []).map((id) => Number(id)).filter((id) => id > 0));
  if (!wanted.size) {
    return 'selected shop';
  }
  const historyRows = Array.isArray(state.food.orderHistory) ? state.food.orderHistory : [];
  const match = historyRows.find((row) => wanted.has(Number(row?.id || 0)));
  return String(match?.shop_name || '').trim() || 'selected shop';
}

async function retryFoodPaymentRecovery(recoveryRow) {
  const paymentRef = String(recoveryRow?.payment_reference || '').trim();
  if (!paymentRef || state.food.recoveryBusyRefs.has(paymentRef)) {
    return;
  }
  const orderIds = (Array.isArray(recoveryRow?.order_ids) ? recoveryRow.order_ids : [])
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value) && value > 0);
  if (!orderIds.length) {
    setFoodStatus('Recovery item has no valid order ids.', true);
    return;
  }
  state.food.recoveryBusyRefs.add(paymentRef);
  renderFoodOrders();
  try {
    const shopName = resolveRecoveryShopName(orderIds);
    const result = await runFoodPaymentFlow({
      orderIds,
      shopName,
      onLiveStatus: ({ status, message }) => {
        showFoodPaymentLivePopup(status, message, shopName);
      },
    });
    if (result.status === 'paid') {
      const knownRows = (state.food.orderHistory.length ? state.food.orderHistory : state.food.orders)
        .filter((row) => orderIds.includes(Number(row?.id || 0)));
      mergeFoodOrdersIntoState(knownRows, { assumeVerifiedPayment: true });
      renderFoodOrders();
      renderFoodOrderStatusTimeline();
      setFoodStatus(`Payment recovered successfully for ${shopName}.`, false);
      void refreshFoodModule({ forceFreshOrders: true, silentStatus: true }).catch((error) => {
        log(`Fresh food order refresh delayed: ${error?.message || 'Unknown error'}`);
      });
    } else if (result.status === 'dismissed') {
      setFoodStatus('Payment window closed. Recovery remains available.', true);
      await refreshFoodModule();
    } else {
      setFoodStatus(result.message || 'Payment retry failed. Please retry.', true);
      await refreshFoodModule();
    }
  } catch (error) {
    setFoodStatus(error.message || 'Unable to retry payment right now.', true);
  } finally {
    state.food.recoveryBusyRefs.delete(paymentRef);
    renderFoodOrders();
  }
}

function renderFoodPaymentRecovery() {
  if (!els.foodPaymentRecoveryList) {
    return;
  }
  els.foodPaymentRecoveryList.innerHTML = '';
  if (authState.user?.role !== 'student') {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'Payment recovery panel is available for student accounts.';
    els.foodPaymentRecoveryList.appendChild(row);
    return;
  }

  const recoveryRows = Array.isArray(state.food.paymentRecovery) ? state.food.paymentRecovery : [];
  if (!recoveryRows.length) {
    const row = document.createElement('div');
    row.className = 'list-item good';
    row.textContent = 'No pending payment recovery actions.';
    els.foodPaymentRecoveryList.appendChild(row);
    return;
  }

  for (const recovery of recoveryRows) {
    const paymentRef = String(recovery?.payment_reference || '').trim();
    const busy = state.food.recoveryBusyRefs.has(paymentRef);
    const orderCount = (Array.isArray(recovery?.order_ids) ? recovery.order_ids.length : 0);
    const row = document.createElement('div');
    row.className = 'list-item food-recovery-row warn';
    const info = document.createElement('div');
    info.className = 'food-recovery-copy';
    info.innerHTML = `
      <strong>${escapeHtml(formatMoney(recovery?.amount || 0))} • ${escapeHtml(asTitleCase(recovery?.status || 'failed'))}</strong>
      <small>Ref ${escapeHtml(paymentRef || '--')} • ${orderCount} order(s) • ${escapeHtml(foodTimestampLabel(recovery?.updated_at, 'time unavailable'))}</small>
      ${recovery?.failed_reason ? `<small>${escapeHtml(String(recovery.failed_reason))}</small>` : ''}
    `;
    const actionBtn = document.createElement('button');
    actionBtn.type = 'button';
    actionBtn.className = 'btn btn-primary';
    actionBtn.textContent = busy ? 'Retrying...' : 'Retry Payment';
    actionBtn.disabled = busy || !paymentRef;
    actionBtn.addEventListener('click', () => {
      void retryFoodPaymentRecovery(recovery);
    });
    row.append(info, actionBtn);
    els.foodPaymentRecoveryList.appendChild(row);
  }
}

function deriveFoodOrderGroupKey(order) {
  const paymentRef = String(order?.payment_reference || '').trim();
  if (paymentRef) {
    return `payment:${paymentRef}`;
  }
  const rawIdempotencyKey = String(order?.idempotency_key || '').trim();
  if (rawIdempotencyKey) {
    return `idempotency:${rawIdempotencyKey.replace(/:\d+$/, '')}`;
  }
  const createdMs = foodOrderTimestampMs(order);
  const minuteBucket = createdMs > 0 ? Math.floor(createdMs / 60000) : 0;
  const shopPart = Number(order?.shop_id || 0) > 0
    ? String(Number(order.shop_id))
    : String(order?.shop_name || '').trim().toLowerCase();
  return [
    'fallback',
    Number(order?.student_id || 0),
    String(order?.order_date || ''),
    Number(order?.slot_id || 0),
    shopPart || 'shop',
    minuteBucket,
  ].join(':');
}

function buildFoodOrderGroups(rows) {
  const groupsByKey = new Map();
  const sourceRows = Array.isArray(rows) ? rows : [];
  for (const row of sourceRows) {
    const key = deriveFoodOrderGroupKey(row);
    if (!groupsByKey.has(key)) {
      groupsByKey.set(key, []);
    }
    groupsByKey.get(key).push(row);
  }
  const groups = [];
  for (const [key, groupRows] of groupsByKey.entries()) {
    const items = groupRows.slice().sort((left, right) => {
      const delta = foodOrderTimestampMs(right) - foodOrderTimestampMs(left);
      if (delta !== 0) {
        return delta;
      }
      return Number(right?.id || 0) - Number(left?.id || 0);
    });
    const latest = items[0] || null;
    const statuses = Array.from(
      new Set(items.map((line) => String(line?.status || '').trim().toLowerCase()).filter(Boolean)),
    );
    const paymentStatuses = Array.from(
      new Set(items.map((line) => String(line?.payment_status || 'pending').trim().toLowerCase()).filter(Boolean)),
    );
    const totalPrice = items.reduce((sum, line) => {
      const amount = Number(line?.total_price || 0);
      return sum + (Number.isFinite(amount) ? amount : 0);
    }, 0);
    groups.push({
      key,
      items,
      latest,
      statuses,
      paymentStatuses,
      totalPrice,
      isFinal: items.length > 0 && items.every((line) => isFoodOrderFinal(line)),
      timestampMs: foodOrderTimestampMs(latest),
    });
  }
  groups.sort((left, right) => {
    const delta = Number(right.timestampMs || 0) - Number(left.timestampMs || 0);
    if (delta !== 0) {
      return delta;
    }
    return Number(right?.latest?.id || 0) - Number(left?.latest?.id || 0);
  });
  return groups;
}

function resolveFoodOrderGroupStatus(group) {
  const statuses = Array.isArray(group?.statuses) ? group.statuses : [];
  const primary = String(group?.latest?.status || statuses[0] || 'placed').trim().toLowerCase() || 'placed';
  const mixed = statuses.length > 1;
  let label = asTitleCase(primary.replaceAll('_', ' '));
  if (mixed) {
    label = `${label} (Mixed)`;
  }
  return { value: primary, label, mixed };
}

function resolveFoodStatusTone(statusValue, paymentStatus = 'pending') {
  const normalizedStatus = String(statusValue || '').trim().toLowerCase();
  const normalizedPayment = String(paymentStatus || '').trim().toLowerCase();
  if (FOOD_FAILED_TONE_STATUSES.has(normalizedStatus) || FOOD_PAYMENT_FAILURE_STATES.has(normalizedPayment)) {
    return 'failed';
  }
  if (FOOD_DELIVERED_TONE_STATUSES.has(normalizedStatus)) {
    return 'delivered';
  }
  if (FOOD_VERIFIED_TONE_STATUSES.has(normalizedStatus)) {
    return 'verified';
  }
  return '';
}

function resolveFoodGroupTone(group, primaryStatus) {
  const statuses = Array.isArray(group?.statuses) ? group.statuses : [];
  const paymentStatuses = Array.isArray(group?.paymentStatuses) ? group.paymentStatuses : [];
  if (statuses.some((value) => FOOD_FAILED_TONE_STATUSES.has(String(value || '').toLowerCase()))) {
    return 'failed';
  }
  if (paymentStatuses.some((value) => FOOD_PAYMENT_FAILURE_STATES.has(String(value || '').toLowerCase()))) {
    return 'failed';
  }
  if (statuses.some((value) => FOOD_DELIVERED_TONE_STATUSES.has(String(value || '').toLowerCase()))) {
    return 'delivered';
  }
  if (String(primaryStatus || '').toLowerCase() === 'verified') {
    return 'verified';
  }
  return '';
}

function renderFoodOrders() {
  renderFoodFreshnessIndicators();
  if (!els.foodOrdersList) {
    renderFoodPaymentRecovery();
    return;
  }
  updateFoodOrdersTabUi();
  renderFoodPaymentRecovery();
  els.foodOrdersList.innerHTML = '';
  const allRows = Array.isArray(state.food.orderHistory) && state.food.orderHistory.length
    ? state.food.orderHistory
    : (Array.isArray(state.food.orders) ? state.food.orders : []);
  const orderById = new Map();
  for (const row of allRows) {
    const id = Number(row?.id || 0);
    if (!id || orderById.has(id)) {
      continue;
    }
    orderById.set(id, row);
  }
  const allGroups = buildFoodOrderGroups(Array.from(orderById.values()));
  const validGroupKeys = new Set(allGroups.map((group) => group.key));
  for (const key of Array.from(state.food.expandedOrderGroups)) {
    if (!validGroupKeys.has(key)) {
      state.food.expandedOrderGroups.delete(key);
    }
  }
  const currentOrders = allGroups.filter((group) => !group.isFinal);
  const previousOrders = allGroups.filter((group) => group.isFinal);
  const activeTab = state.food.ordersTab === 'previous' ? 'previous' : 'current';
  const selectedRows = activeTab === 'previous' ? previousOrders : currentOrders;

  if (!selectedRows.length) {
    const canOpenCart = authState.user?.role === 'student';
    const row = buildEmptyStateRow({
      title: activeTab === 'previous'
        ? 'No previous orders yet.'
        : 'No active orders right now.',
      description: activeTab === 'previous'
        ? 'Delivered, cancelled, and completed orders will appear here.'
        : 'Place an order to start live tracking and payment status updates.',
      iconLabel: activeTab === 'previous' ? 'HISTORY' : 'TRACK',
      ctaLabel: canOpenCart ? 'Open Cart' : '',
      ctaClassName: 'btn btn-primary',
      onCta: () => {
        if (canOpenCart) {
          openFoodCartModal();
        }
      },
    });
    els.foodOrdersList.appendChild(row);
    return;
  }

  const itemById = Object.fromEntries(state.food.items.map((item) => [item.id, item]));
  const slotById = Object.fromEntries(state.food.slots.map((slot) => [slot.id, slot]));

  for (const [groupIndex, group] of selectedRows.entries()) {
    const order = group.latest || {};
    const { value: statusValue, label: statusLabel, mixed: statusMixed } = resolveFoodOrderGroupStatus(group);
    const row = document.createElement('article');
    row.className = 'list-item food-order-card';
    const groupTone = resolveFoodGroupTone(group, statusValue);
    if (groupTone) {
      row.classList.add(`tone-${groupTone}`);
    }

    const slot = slotById[order.slot_id];
    const slotText = slot
      ? `${slot.label} (${formatTime(slot.start_time)} - ${formatTime(slot.end_time)})`
      : `Slot #${order.slot_id}`;
    const parsedOrderDate = parseISODateLocal(order?.order_date || '');
    const orderDateText = parsedOrderDate ? parsedOrderDate.toLocaleDateString('en-GB') : '--';
    const lastUpdate = foodTimestampLabel(order?.last_status_updated_at || order?.created_at, '--');
    const paymentStatus = group.paymentStatuses.length === 1
      ? asTitleCase(group.paymentStatuses[0])
      : 'Mixed';
    const progressValue = Math.max(0, Math.min(100, Number(FOOD_ORDER_PROGRESS_POINTS[statusValue] ?? 16)));
    const expanded = state.food.expandedOrderGroups.has(group.key);
    const createdLabel = foodTimestampLabel(
      order?.created_at || order?.last_status_updated_at || order?.updated_at,
      '--',
    );
    const lineRows = group.items.slice().sort((left, right) => Number(left?.id || 0) - Number(right?.id || 0));
    const itemCount = lineRows.length;
    const confirmableLineIds = lineRows
      .map((line) => {
        const id = Number(line?.id || 0);
        if (!id) {
          return 0;
        }
        const lineStatus = String(line?.status || '').trim().toLowerCase();
        const linePaymentStatus = String(line?.payment_status || 'pending').trim().toLowerCase();
        if (!FOOD_MANUAL_DELIVERY_CONFIRM_STATUSES.has(lineStatus)) {
          return 0;
        }
        if (!['paid', 'captured'].includes(linePaymentStatus)) {
          return 0;
        }
        return id;
      })
      .filter((id) => id > 0);
    const canConfirmGroupDelivery = Boolean(authState.user?.role === 'student' && confirmableLineIds.length > 0);
    const groupConfirmBusy = canConfirmGroupDelivery
      && confirmableLineIds.some((id) => state.food.deliveryConfirmBusyOrderIds.has(id));

    const toggleBtn = document.createElement('button');
    toggleBtn.type = 'button';
    toggleBtn.className = 'food-order-card-toggle';
    toggleBtn.setAttribute('aria-expanded', String(expanded));
    toggleBtn.innerHTML = `
      <div class="food-order-card-head">
        <div class="food-order-card-title">
          <strong>Order #${groupIndex + 1}</strong>
          <small>${escapeHtml(createdLabel)}</small>
        </div>
        <span class="food-order-badge">${escapeHtml(statusLabel)}</span>
      </div>
      <div class="food-order-card-meta">${escapeHtml(orderDateText)} • ${escapeHtml(slotText)} • ${itemCount} item(s) • Subtotal ${formatMoney(group.totalPrice)} • Payment ${escapeHtml(paymentStatus)}</div>
      <div class="food-order-tracker">
        <div class="food-order-progress-bar">
          <span class="food-order-progress-fill" style="--food-order-progress:${progressValue}%"></span>
        </div>
        <small>${escapeHtml(displayFoodOrderStatus(order))} • updated ${escapeHtml(lastUpdate)}${statusMixed ? ' • mixed item statuses' : ''}</small>
      </div>
      <div class="food-order-card-foot">
        <small>Tap to view item details</small>
        <span class="food-order-card-chevron" aria-hidden="true">›</span>
      </div>
    `;

    const groupActions = document.createElement('div');
    groupActions.className = 'food-order-group-actions';
    if (!canConfirmGroupDelivery) {
      setHidden(groupActions, true);
    } else {
      const groupConfirmBtn = document.createElement('button');
      groupConfirmBtn.type = 'button';
      groupConfirmBtn.className = 'btn btn-secondary food-delivery-confirm-btn food-delivery-confirm-btn-group';
      groupConfirmBtn.textContent = groupConfirmBusy
        ? 'Updating...'
        : `Got Delivery (${confirmableLineIds.length} item${confirmableLineIds.length > 1 ? 's' : ''})`;
      groupConfirmBtn.disabled = groupConfirmBusy;
      groupConfirmBtn.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        void confirmFoodOrderDeliveryBatch(confirmableLineIds, { labelPrefix: `Order #${groupIndex + 1}` });
      });
      groupActions.appendChild(groupConfirmBtn);
    }

    const details = document.createElement('div');
    details.className = 'food-order-card-details';
    details.classList.toggle('is-collapsed', !expanded);
    details.setAttribute('aria-hidden', String(!expanded));

    const itemsWrap = document.createElement('div');
    itemsWrap.className = 'food-order-items-list';
    for (const line of lineRows) {
      const lineStatusValue = String(line?.status || '').trim().toLowerCase();
      const linePaymentStatusValue = String(line?.payment_status || 'pending').trim().toLowerCase();
      const lineStatusLabel = asTitleCase((lineStatusValue || 'placed').replaceAll('_', ' '));
      const lineItem = itemById[line.food_item_id];
      const lineUpdatedAt = foodTimestampLabel(line?.last_status_updated_at || line?.created_at, '--');
      const lineIdText = Number(line?.id || 0) > 0 ? `#${Number(line.id)}` : '--';
      const lineTone = resolveFoodStatusTone(lineStatusValue, linePaymentStatusValue);
      const lineRow = document.createElement('div');
      lineRow.className = 'food-order-item-row';
      if (lineTone) {
        lineRow.classList.add(`tone-${lineTone}`);
      }
      lineRow.innerHTML = `
        <div class="food-order-item-head">
          <strong>${escapeHtml(lineItem?.name || `Item #${line.food_item_id}`)} • x${Number(line?.quantity || 1)}</strong>
          <div class="food-order-item-actions">
            <span class="food-order-item-badge">${escapeHtml(lineStatusLabel)}</span>
          </div>
        </div>
        <small class="food-order-item-meta">Line ${lineIdText} • ${formatMoney(line?.total_price || 0)} • Payment ${escapeHtml(asTitleCase(line?.payment_status || 'pending'))}</small>
        <small class="food-order-item-meta">${escapeHtml(displayFoodOrderStatus(line))} • updated ${escapeHtml(lineUpdatedAt)}</small>
      `;

      if (authState.user?.role === 'student' && lineStatusValue === 'delivered') {
        const ratingRow = document.createElement('div');
        ratingRow.className = 'food-rating-row';
        const selectedStars = Math.max(0, Math.min(5, Number(line?.rating_stars || 0)));
        const lockedAt = String(line?.rating_locked_at || '').trim();
        const isLocked = Boolean(lockedAt);
        const lockedLabel = isLocked ? foodTimestampLabel(lockedAt, '--') : '';
        const isBusy = state.food.ratingBusyOrderIds.has(Number(line.id));
        const label = document.createElement('small');
        if (isBusy) {
          label.textContent = 'Saving rating...';
        } else if (isLocked) {
          label.textContent = `Rating locked on ${lockedLabel}`;
        } else {
          label.textContent = 'Rate this delivered item (final submit):';
        }
        ratingRow.appendChild(label);

        const starsWrap = document.createElement('div');
        starsWrap.className = 'food-rating-stars';
        for (let starValue = 1; starValue <= 5; starValue += 1) {
          const starBtn = document.createElement('button');
          starBtn.type = 'button';
          starBtn.className = 'food-rating-star';
          starBtn.textContent = '★';
          starBtn.setAttribute('aria-label', `Rate ${starValue} star${starValue > 1 ? 's' : ''}`);
          if (starValue <= selectedStars) {
            starBtn.classList.add('is-selected');
          }
          starBtn.disabled = isBusy || isLocked;
          starBtn.addEventListener('click', () => {
            if (isLocked || isBusy) {
              return;
            }
            const confirmed = window.confirm(
              `Submit ${starValue} star${starValue > 1 ? 's' : ''} for this delivered order? This cannot be changed later.`,
            );
            if (!confirmed) {
              return;
            }
            void updateFoodOrderRating(Number(line.id), starValue, { confirmFinal: true });
          });
          starsWrap.appendChild(starBtn);
        }
        ratingRow.appendChild(starsWrap);
        lineRow.appendChild(ratingRow);
      }
      itemsWrap.appendChild(lineRow);
    }
    details.appendChild(itemsWrap);

    toggleBtn.addEventListener('click', () => {
      const nextExpanded = toggleBtn.getAttribute('aria-expanded') !== 'true';
      toggleBtn.setAttribute('aria-expanded', String(nextExpanded));
      details.classList.toggle('is-collapsed', !nextExpanded);
      details.setAttribute('aria-hidden', String(!nextExpanded));
      if (nextExpanded) {
        state.food.expandedOrderGroups.add(group.key);
      } else {
        state.food.expandedOrderGroups.delete(group.key);
      }
    });

    row.append(toggleBtn, groupActions, details);
    els.foodOrdersList.appendChild(row);
  }
}

function renderFoodPeakTimes() {
  if (!els.foodPeakList) {
    return;
  }
  els.foodPeakList.innerHTML = '';
  if (!state.peakTimes.length) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'No peak forecast data yet.';
    els.foodPeakList.appendChild(row);
    return;
  }

  for (const peak of state.peakTimes) {
    const row = document.createElement('div');
    row.className = 'list-item';
    if (peak.predicted_rush_level === 'high') {
      row.classList.add('warn');
    } else if (peak.predicted_rush_level === 'low') {
      row.classList.add('good');
    }
    row.innerHTML = `
      <span>${escapeHtml(peak.slot_label)}</span>
      <span>${escapeHtml(asTitleCase(peak.predicted_rush_level))} • avg ${Number(peak.average_orders || 0).toFixed(1)} orders</span>
    `;
    els.foodPeakList.appendChild(row);
  }
}

function syncFoodOrderActionState() {
  const canOrder = authState.user?.role === 'student' && Number(authState.user?.student_id);
  const hasCartItems = Array.isArray(state.food.cart.items) && state.food.cart.items.length > 0;
  const selectedSlot = getSelectedFoodSlot();
  const hasSlot = Boolean(Number(els.foodSlotSelect?.value || 0) || (isFoodDemoEnabled() ? Number(state.food.slots?.[0]?.id || 0) : 0));
  const orderGate = getFoodRuntimeOrderGate({ slot: selectedSlot });
  const canReview = Boolean(canOrder && hasCartItems && hasSlot && orderGate.canOrderNow);
  const hasDeliveryPoint = isFoodDemoEnabled()
    || Boolean(String(state.food.checkoutDeliveryPoint || els.foodDeliveryBlockSelect?.value || '').trim());
  const locationFresh = isFoodLocationFresh();
  const locationOk = isFoodDemoEnabled() || (state.food.location.verified && state.food.location.allowed && locationFresh);
  const canCheckout = Boolean(canReview && state.food.checkoutPreviewOpen && hasDeliveryPoint);
  let actionBlockMessage = '';
  if (canOrder && hasCartItems && hasSlot && !orderGate.canOrderNow) {
    actionBlockMessage = orderGate.message;
  }
  if (!canReview && state.food.cartModalTab === 'review') {
    setFoodCartModalTab('cart');
  }
  if (els.foodCartCheckoutBtn) {
    els.foodCartCheckoutBtn.textContent = 'Review Cart';
    els.foodCartCheckoutBtn.disabled = !canReview;
    if (actionBlockMessage) {
      els.foodCartCheckoutBtn.title = actionBlockMessage;
    } else {
      els.foodCartCheckoutBtn.removeAttribute('title');
    }
  }
  if (els.foodCartTabReviewBtn) {
    els.foodCartTabReviewBtn.textContent = 'Review & Pay';
    els.foodCartTabReviewBtn.disabled = !canReview;
    if (actionBlockMessage) {
      els.foodCartTabReviewBtn.title = actionBlockMessage;
    } else {
      els.foodCartTabReviewBtn.removeAttribute('title');
    }
  }
  if (els.foodCartPayBtn) {
    const reviewTabActive = state.food.cartModalTab === 'review';
    setHidden(els.foodCartPayBtn, !(reviewTabActive && state.food.checkoutPreviewOpen));
    if (els.foodCartPayBtn.dataset.processing !== 'true') {
      els.foodCartPayBtn.textContent = isFoodDemoEnabled() ? 'Place Demo Order' : 'Pay & Place Order';
    }
    els.foodCartPayBtn.disabled = !canCheckout;
    if (!canCheckout && actionBlockMessage) {
      els.foodCartPayBtn.title = actionBlockMessage;
    } else if (!canCheckout && !hasDeliveryPoint && hasCartItems && hasSlot) {
      els.foodCartPayBtn.title = 'Select delivery block before payment.';
    } else {
      els.foodCartPayBtn.removeAttribute('title');
    }
  }
  if (els.foodCartPayBtn && canCheckout && !locationOk) {
    els.foodCartPayBtn.dataset.requiresLocation = 'true';
  } else if (els.foodCartPayBtn) {
    delete els.foodCartPayBtn.dataset.requiresLocation;
  }
}

function buildFoodLoadWarningMessage(failures) {
  if (!Array.isArray(failures) || !failures.length) {
    return '';
  }
  const labels = Array.from(new Set(
    failures
      .map((entry) => String(entry?.label || '').trim())
      .filter(Boolean)
  ));
  if (!labels.length) {
    return 'Some Food Hall data could not load. Showing available data.';
  }
  const shortList = labels.slice(0, 3);
  const suffix = labels.length > shortList.length ? ', ...' : '';
  return `Some Food Hall data could not load (${shortList.join(', ')}${suffix}). Showing available data.`;
}

function buildFoodOrdersApiPath({ orderDate = '', limit = 200, forceFresh = false } = {}) {
  const params = new URLSearchParams();
  if (String(orderDate || '').trim()) {
    params.set('order_date', String(orderDate || '').trim());
  }
  if (Number(limit || 0) > 0) {
    params.set('limit', String(Number(limit)));
  }
  if (forceFresh) {
    params.set('fresh', '1');
  }
  return `/food/orders?${params.toString()}`;
}

async function loadFoodSnapshot({ orderDate, shouldLoadCart, forceFreshOrders = false }) {
  const failures = [];
  const loadWithFallback = async (label, loader, fallbackValue) => {
    try {
      return await loader();
    } catch (error) {
      if (Number(error?.status || 0) === 401) {
        throw error;
      }
      failures.push({ label, error });
      return typeof fallbackValue === 'function' ? fallbackValue() : fallbackValue;
    }
  };

  const [items, slots, ordersForDate, orderHistory, peaks, shops, cartPayload, paymentRecovery] = await Promise.all([
    loadWithFallback('items', () => api('/food/items'), []),
    loadWithFallback('slots', () => api('/food/slots'), []),
    loadWithFallback(
      'orders',
      () => api(buildFoodOrdersApiPath({ orderDate, limit: 180, forceFresh: forceFreshOrders })),
      [],
    ),
    loadWithFallback(
      'order history',
      () => api(buildFoodOrdersApiPath({ limit: 200, forceFresh: forceFreshOrders })),
      [],
    ),
    loadWithFallback('peak times', () => api('/food/peak-times?lookback_days=14'), []),
    loadWithFallback('shops', () => api(`/food/shops?active_only=${isFoodDemoEnabled() ? 'false' : 'true'}`), []),
    shouldLoadCart
      ? loadWithFallback('cart', () => api('/food/cart'), null)
      : Promise.resolve(null),
    shouldLoadCart
      ? loadWithFallback('payment recovery', () => api('/food/payments/recovery'), [])
      : Promise.resolve([]),
  ]);

  return {
    items,
    slots,
    ordersForDate,
    orderHistory,
    peaks,
    shops,
    cartPayload,
    paymentRecovery,
    failures,
  };
}

async function refreshFoodModule({ forceFreshOrders = false, silentStatus = false } = {}) {
  if (!authState.user) {
    return;
  }
  await ensureFoodCatalogLoaded({ preloadOnly: false });
  if (!silentStatus) {
    setFoodStatus('Refreshing Food Hall data...', false, 'loading');
  }

  if (els.foodOrderDate) {
    const currentDate = todayISO();
    const selectedValue = String(els.foodOrderDate.value || '').trim();
    const normalized = selectedValue && parseISODateLocal(selectedValue) ? selectedValue : '';
    let nextDate = normalized || String(state.food.orderDate || '').trim() || currentDate;
    if (authState.user.role === 'student') {
      els.foodOrderDate.min = currentDate;
      els.foodOrderDate.removeAttribute('max');
      if (!parseISODateLocal(nextDate) || nextDate < currentDate) {
        nextDate = currentDate;
      }
    } else {
      els.foodOrderDate.removeAttribute('min');
      els.foodOrderDate.removeAttribute('max');
    }
    els.foodOrderDate.value = nextDate;
    state.food.orderDate = nextDate;
  }
  const orderDate = String(els.foodOrderDate?.value || state.food.orderDate || todayISO()).trim() || todayISO();
  state.food.orderDate = orderDate;

  const shouldLoadCart = authState.user.role === 'student';
  let snapshot = await loadFoodSnapshot({ orderDate, shouldLoadCart, forceFreshOrders });
  let {
    items,
    slots,
    ordersForDate,
    orderHistory,
    peaks,
    shops,
    cartPayload,
    paymentRecovery,
  } = snapshot;
  let loadFailures = Array.isArray(snapshot.failures) ? [...snapshot.failures] : [];

  if ((!Array.isArray(shops) || !shops.length || !Array.isArray(slots) || !slots.length) && authState.user) {
    try {
      await api('/food/bootstrap/ensure', { method: 'POST' });
      snapshot = await loadFoodSnapshot({ orderDate, shouldLoadCart, forceFreshOrders });
      ({
        items,
        slots,
        ordersForDate,
        orderHistory,
        peaks,
        shops,
        cartPayload,
        paymentRecovery,
      } = snapshot);
      if (Array.isArray(snapshot.failures) && snapshot.failures.length) {
        loadFailures = loadFailures.concat(snapshot.failures);
      }
    } catch (error) {
      if (Number(error?.status || 0) === 401) {
        throw error;
      }
      loadFailures.push({ label: 'bootstrap', error });
      // Keep existing response handling; status banner below will surface configuration issues.
    }
  }
  const foodLoadWarning = buildFoodLoadWarningMessage(loadFailures);
  for (const failure of loadFailures) {
    const label = String(failure?.label || 'food').trim() || 'food';
    const message = String(failure?.error?.message || 'Unknown error').trim() || 'Unknown error';
    log(`Food data fallback (${label}): ${message}`);
  }

  const digestRows = Array.isArray(orderHistory) && orderHistory.length
    ? orderHistory
    : (Array.isArray(ordersForDate) ? ordersForDate : []);
  const nextFreshnessDigest = buildFoodOrdersFreshnessDigest(digestRows, paymentRecovery);
  const previousFreshnessDigest = String(state.food.freshnessDigest || '').trim();
  const hasOrderDataChanged = Boolean(previousFreshnessDigest) && previousFreshnessDigest !== nextFreshnessDigest;
  state.food.freshnessDigest = nextFreshnessDigest;
  markFoodOrdersFreshness({ changed: hasOrderDataChanged });

  state.food.items = Array.isArray(items) ? items : [];
  state.food.slots = hydrateApiSlots(slots);
  state.food.orders = Array.isArray(ordersForDate) ? ordersForDate : [];
  state.food.orderHistory = Array.isArray(orderHistory) ? orderHistory : [];
  state.food.paymentRecovery = Array.isArray(paymentRecovery) ? paymentRecovery : [];
  syncFoodOrderLiveFeedNotifications(
    state.food.orderHistory.length ? state.food.orderHistory : state.food.orders,
  );
  state.peakTimes = Array.isArray(peaks) ? peaks : [];
  state.food.shops = hydrateApiShops(shops);
  if (shouldLoadCart) {
    applyFoodCartPayload(cartPayload || {});
  } else if (authState.user.role !== 'student') {
    applyFoodCartPayload({});
  }
  if (!state.food.menuByShop || typeof state.food.menuByShop !== 'object') {
    state.food.menuByShop = {};
  }
  const validShopIds = new Set(state.food.shops.map((shop) => String(shop.id)));
  for (const shopId of Object.keys(state.food.menuByShop)) {
    if (!validShopIds.has(shopId)) {
      delete state.food.menuByShop[shopId];
    }
  }
  const selectedShopKey = String(state.food.cart.shopId || '');
  if (selectedShopKey && !state.food.shops.some((shop) => String(shop.id) === selectedShopKey)) {
    await clearFoodCart({ silent: true });
  }
  if (!state.food.cart.items.length) {
    setFoodCartModalTab('cart');
    state.food.checkoutPreviewOpen = false;
  }

  await refreshFoodSlotHints(orderDate);

  renderFoodItemOptions();
  renderFoodSlotOptions();
  ensureFoodDeliveryPointOptions();
  renderFoodOrders();
  renderFoodPeakTimes();
  renderFoodShops();
  await renderFoodAiQuickChips();
  renderFoodCart();
  renderFoodOrderStatusTimeline();
  renderFoodAdminOrderOptions();
  syncFoodOrderActionState();
  applyFoodRealtimeAvailability();
  updateFoodLocationActionState();

  if (els.workDate && !els.workDate.value) {
    els.workDate.value = orderDate;
  }
  try {
    await Promise.all([
      refreshDemand(orderDate),
      refreshFoodDemandLiveSignal(orderDate, { animate: false }).catch(() => null),
    ]);
  } catch (error) {
    log(`Food demand feed degraded: ${error?.message || 'Unknown error'}`);
  }

  if (authState.user.role === 'student' && (!state.food.shops.length || !state.food.slots.length)) {
    if (foodLoadWarning) {
      if (!silentStatus) {
        setFoodStatus(foodLoadWarning, true);
      }
    } else {
      if (!silentStatus) {
        setFoodStatus('Shops or pickup slots are not configured yet. Please contact faculty/admin.', true);
      }
    }
    return;
  }

  if (authState.user.role !== 'student') {
    stopFoodLocationMonitoring();
    if (foodLoadWarning) {
      if (!silentStatus) {
        setFoodStatus(foodLoadWarning, true);
      }
    } else if (authState.user.role === 'owner') {
      if (!silentStatus) {
        setFoodStatus('Owner panel refreshed. You can manage orders for your assigned shop only.');
      }
    } else {
      if (!silentStatus) {
        setFoodStatus('Food module refreshed. You can monitor demand and manage setup.');
      }
    }
    setFoodLocationStatus('Location gate is enforced for student checkouts.', 'warn');
  } else {
    if (!state.food.location.autoPromptAttempted && !state.food.location.verified) {
      state.food.location.autoPromptAttempted = true;
      await verifyFoodLocationGate({ forcePrompt: true, silent: true }).catch(() => false);
    }
    const permissionState = await getGeoPermissionState();
    if (permissionState === 'denied' && !state.food.location.verified) {
      stopFoodLocationMonitoring();
      if (state.food.location.requestedOnce) {
        setFoodLocationStatus('Location permission is blocked in browser settings. Allow location for this site, then retry.', 'error');
      } else {
        setFoodLocationStatus('Tap "Enable Location Access" to allow GPS and order inside LPU campus.', 'warn');
      }
    } else if (!state.food.location.requestedOnce) {
      stopFoodLocationMonitoring();
      setFoodLocationStatus('Tap "Enable Location Access" to allow GPS and order inside LPU campus.', 'warn');
    } else if (state.food.location.verified && isFoodLocationFresh()) {
      startFoodLocationMonitoring();
      setFoodLocationStatus(formatLocationStatusMessage(state.food.location.message, { source: 'monitor' }), state.food.location.allowed ? 'ok' : 'error');
    } else if (state.food.location.verified && !isFoodLocationFresh()) {
      setFoodLocationStatus('Location lock expired. Tap "Enable Location Access" again to refresh GPS lock.', 'warn');
      stopFoodLocationMonitoring();
    } else {
      setFoodLocationStatus('Location access is required. Delivery is allowed only inside LPU campus.', 'warn');
    }
    if (foodLoadWarning) {
      if (!silentStatus) {
        setFoodStatus(foodLoadWarning, true);
      }
    } else {
      const orderGate = getFoodRuntimeOrderGate({ slot: getSelectedFoodSlot(), orderDate });
      if (!orderGate.canBrowseShops || !orderGate.canOrderNow) {
        if (!silentStatus) {
          setFoodStatus(orderGate.message, true);
        }
      } else {
        if (!silentStatus) {
          setFoodStatus('Select one shop, add items, then open cart to checkout. Orders are accepted from one shop at a time.');
        }
      }
    }
  }
}

async function recordFoodPaymentFailure(intent, failurePayload = {}) {
  const razorpayOrderId = String(
    failurePayload.razorpay_order_id
      || intent?.provider_order_id
      || intent?.payment_reference
      || '',
  ).trim();
  if (!razorpayOrderId) {
    return;
  }
  await api('/food/payments/failure', {
    method: 'POST',
    body: JSON.stringify({
      razorpay_order_id: razorpayOrderId,
      razorpay_payment_id: String(failurePayload.razorpay_payment_id || '').trim() || null,
      error_code: String(failurePayload.error_code || '').trim() || null,
      error_description: String(failurePayload.error_description || '').trim() || null,
      error_source: String(failurePayload.error_source || '').trim() || null,
      error_step: String(failurePayload.error_step || '').trim() || null,
      error_reason: String(failurePayload.error_reason || '').trim() || null,
    }),
  }).catch(() => {});
}

function showFoodPaymentLivePopup(status, message = '', shopName = '') {
  const normalizedStatus = String(status || '').trim().toLowerCase();
  const resolvedShop = String(shopName || 'selected shop').trim();
  if (normalizedStatus === 'initiated') {
    showFoodPopup('Payment Started', `Opening secure checkout for ${resolvedShop}.`, { autoHideMs: 1800 });
    return;
  }
  if (normalizedStatus === 'paid') {
    showFoodPopup('Payment Successful', `Payment completed for ${resolvedShop}.`, { autoHideMs: 3400 });
    return;
  }
  if (normalizedStatus === 'dismissed') {
    showFoodPopup(
      'Payment Pending',
      message || 'Payment window closed before completion. You can retry from Payment Recovery.',
      { isError: true, autoHideMs: 4200 },
    );
    return;
  }
  showFoodPopup(
    'Payment Failed',
    message || 'Payment was not completed. Please retry.',
    { isError: true, autoHideMs: 4200 },
  );
}

async function runFoodPaymentFlow({ orderIds, shopName, onLiveStatus = null }) {
  const normalizedIds = (Array.isArray(orderIds) ? orderIds : [])
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value) && value > 0);
  if (!normalizedIds.length) {
    throw new Error('No valid order ids available for payment.');
  }
  const emitLiveStatus = (status, message = '') => {
    if (typeof onLiveStatus === 'function') {
      try {
        onLiveStatus({ status, message });
      } catch (_) {
        // Non-blocking callback for UI hints only.
      }
    }
  };

  if (isFoodDemoEnabled()) {
    let intent = null;
    try {
      intent = await api('/food/payments/intent', {
        method: 'POST',
        body: JSON.stringify({ order_ids: normalizedIds, provider: 'sandbox' }),
      });
    } catch (error) {
      throw new Error(resolveFoodPaymentError(error, 'Unable to initialize demo payment. Please retry.'));
    }
    const paymentReference = String(intent?.payment_reference || '').trim();
    if (!paymentReference) {
      throw new Error('Demo payment reference was not created.');
    }
    emitLiveStatus('initiated', 'Demo payment initialized.');
    try {
      await api('/food/payments/demo-complete', {
        method: 'POST',
        headers: foodDemoRequestHeaders(),
        body: JSON.stringify({ payment_reference: paymentReference }),
      });
    } catch (error) {
      throw new Error(resolveFoodPaymentError(error, 'Unable to complete demo payment. Please retry.'));
    }
    emitLiveStatus('paid', 'Demo payment confirmed.');
    return { status: 'paid' };
  }

  let config = null;
  try {
    config = await api('/food/payments/config');
  } catch (error) {
    throw new Error(resolveFoodPaymentError(error, 'Unable to load payment configuration.'));
  }
  if (!config?.key_id) {
    throw new Error('Payments are not configured on server. Razorpay key is missing.');
  }

  let sdkLoadError = null;
  const sdkLoadPromise = ensureRazorpayCheckoutSdk().catch((error) => {
    sdkLoadError = error;
    return null;
  });

  let intent = null;
  try {
    intent = await api('/food/payments/intent', {
      method: 'POST',
      body: JSON.stringify({ order_ids: normalizedIds, provider: 'razorpay' }),
    });
  } catch (error) {
    throw new Error(resolveFoodPaymentError(error, 'Unable to initialize payment. Please retry.'));
  }
  emitLiveStatus('initiated', 'Checkout initialized successfully.');

  const providerOrderId = String(intent?.provider_order_id || '').trim();
  if (!providerOrderId) {
    throw new Error('Payment gateway order was not created. Check Razorpay server keys/config and retry.');
  }
  const amountInSubunits = Math.round(Number(intent?.amount || 0) * 100);
  if (!Number.isFinite(amountInSubunits) || amountInSubunits <= 0) {
    throw new Error('Invalid payment amount received from server. Please retry checkout.');
  }

  await sdkLoadPromise;
  if (sdkLoadError || !window.Razorpay) {
    throw new Error(sdkLoadError?.message || 'Razorpay checkout failed to load. Check internet and retry.');
  }

  let checkoutResult = null;
  try {
    checkoutResult = await new Promise((resolve, reject) => {
      let settled = false;
      let paymentVerificationInFlight = false;
      const settle = (payload, asError = false) => {
        if (settled) {
          return;
        }
        settled = true;
        if (asError) {
          reject(payload);
          return;
        }
        resolve(payload);
      };

      const options = {
        key: config.key_id,
        amount: amountInSubunits,
        currency: 'INR',
        name: 'LPU Smart Campus Food Hall',
        description: `Order from ${shopName || 'selected shop'}`,
        order_id: providerOrderId,
        prefill: {
          email: authState.user?.email || '',
          name: authState.user?.name || '',
        },
        handler: async (response) => {
          paymentVerificationInFlight = true;
          try {
            await api('/food/payments/verify', {
              method: 'POST',
              body: JSON.stringify({
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_signature: response.razorpay_signature,
              }),
            });
            settle({ status: 'paid' });
          } catch (error) {
            settle(new Error(error?.message || 'Payment verification failed.'), true);
          } finally {
            paymentVerificationInFlight = false;
          }
        },
        modal: {
          ondismiss: () => {
            if (paymentVerificationInFlight) {
              return;
            }
            settle({
              status: 'dismissed',
              failure: {
                razorpay_order_id: providerOrderId,
                error_code: 'checkout_dismissed',
                error_description: 'Checkout was closed before payment completion.',
                error_source: 'checkout-modal',
                error_step: 'payment_window',
                error_reason: 'checkout_dismissed',
              },
              message: 'Payment window closed before completion.',
            });
          },
        },
        theme: { color: '#3399cc' },
      };

      const rzp = new window.Razorpay(options);
      rzp.on('payment.failed', (response) => {
        const err = response?.error || {};
        settle({
          status: 'failed',
          failure: {
            razorpay_order_id: String(err?.metadata?.order_id || intent.provider_order_id || intent.payment_reference || ''),
            razorpay_payment_id: String(err?.metadata?.payment_id || ''),
            error_code: String(err?.code || ''),
            error_description: String(err?.description || ''),
            error_source: String(err?.source || ''),
            error_step: String(err?.step || ''),
            error_reason: String(err?.reason || ''),
          },
          message: String(err?.description || 'Payment failed. Please retry.'),
        });
      });
      try {
        rzp.open();
      } catch (error) {
        settle(new Error(error?.message || 'Unable to open Razorpay checkout.'), true);
      }
    });
  } catch (error) {
    emitLiveStatus('failed', String(error?.message || 'Payment failed.'));
    throw error;
  }

  if (checkoutResult.status === 'paid') {
    emitLiveStatus('paid', 'Payment confirmed.');
    return { status: 'paid' };
  }

  if (String(checkoutResult.status || '').toLowerCase() === 'failed') {
    await recordFoodPaymentFailure(intent, checkoutResult.failure || {});
  }
  const failedResult = {
    status: checkoutResult.status || 'failed',
    message: String(checkoutResult.message || 'Payment was not completed. Please retry.'),
  };
  emitLiveStatus(failedResult.status, failedResult.message);
  return failedResult;
}

async function placeFoodOrder() {
  const studentId = Number(authState.user?.student_id || 0);
  if (authState.user?.role !== 'student' || !studentId) {
    throw new Error('Food pre-order is available only for student accounts.');
  }
  const fallbackSlotId = Number(state.food.slots?.[0]?.id || 0);
  const slotId = Number(els.foodSlotSelect?.value || 0) || (isFoodDemoEnabled() ? fallbackSlotId : 0);
  const orderDate = String(els.foodOrderDate?.value || todayISO()).trim() || todayISO();
  const slot = getSelectedFoodSlot();
  const orderGate = getFoodRuntimeOrderGate({ slot, orderDate });
  const cartItems = Array.isArray(state.food.cart.items) ? state.food.cart.items : [];
  const shop = getShopById(state.food.cart.shopId);

  if (!slotId) {
    throw new Error('Select break slot before checkout.');
  }
  if (!isFoodDemoEnabled() && (!slot || Number(slot.id) !== slotId)) {
    throw new Error('Selected break slot is unavailable. Refresh and retry.');
  }
  if (!orderGate.canOrderNow) {
    throw new Error(orderGate.message);
  }
  if (!cartItems.length || !shop) {
    throw new Error('Add menu items from one shop before checkout.');
  }
  if (!state.food.checkoutPreviewOpen) {
    throw new Error('Open cart and click "Review Checkout" before payment.');
  }
  const deliveryPoint = String(state.food.checkoutDeliveryPoint || els.foodDeliveryBlockSelect?.value || '').trim()
    || (isFoodDemoEnabled() ? 'Demo Delivery Point' : '');
  if (!deliveryPoint) {
    throw new Error('Select delivery block before payment.');
  }
  state.food.checkoutDeliveryPoint = deliveryPoint;

  const checkoutBtn = els.foodCartPayBtn;
  if (checkoutBtn) {
    checkoutBtn.dataset.processing = 'true';
    checkoutBtn.disabled = true;
    checkoutBtn.textContent = 'Processing Payment...';
  }

  try {
    if (!isFoodDemoEnabled()) {
      const locationAllowed = await verifyFoodLocationGate({
        forcePrompt: !state.food.location.verified || !isFoodLocationFresh(),
        silent: false,
      });
      if (!locationAllowed) {
        throw new Error(state.food.location.message || 'Delivery is allowed only inside LPU campus.');
      }
    }

    const checkoutIdempotencyKey = buildFoodCheckoutIdempotencyKey({
      studentId,
      orderDate,
      slotId,
      shopId: Number(shop.apiShopId || shop.id || 0) || 0,
      deliveryPoint,
      cartItems,
      cartUpdatedAt: state.food.cartUpdatedAt,
    });
    let placedOrders = null;
    try {
      placedOrders = await api('/food/orders/checkout', {
        method: 'POST',
        headers: foodDemoRequestHeaders({ 'X-Idempotency-Key': checkoutIdempotencyKey }),
        body: JSON.stringify({
          student_id: studentId,
          shop_id: Number(shop.apiShopId || shop.id || 0) || null,
          slot_id: slotId,
          order_date: orderDate,
          idempotency_key: checkoutIdempotencyKey,
          shop_name: shop.name,
          shop_block: shop.block,
          pickup_point: deliveryPoint,
          location_latitude: isFoodDemoEnabled() ? null : state.food.location.latitude,
          location_longitude: isFoodDemoEnabled() ? null : state.food.location.longitude,
          location_accuracy_m: isFoodDemoEnabled() ? null : state.food.location.accuracyM,
          items: cartItems.map((entry) => ({
            menu_item_id: Number(entry.menuItemId),
            food_item_id: Number.isFinite(Number(entry.foodItemId)) ? Number(entry.foodItemId) : null,
            quantity: Math.max(1, Number(entry.quantity || 1)),
            status_note: entry.itemNote || null,
          })),
        }),
      });
    } catch (error) {
      throw new Error(resolveFoodPaymentError(error, 'Unable to reserve slot and create order items. Please retry.'));
    }
    if (!Array.isArray(placedOrders) || !placedOrders.length) {
      throw new Error('Checkout did not create any orders. Please retry.');
    }

    const orderIds = placedOrders.map((row) => Number(row?.id || 0)).filter((id) => id > 0);
    const paymentResult = await runFoodPaymentFlow({
      orderIds,
      shopName: shop.name,
      onLiveStatus: ({ status, message }) => {
        showFoodPaymentLivePopup(status, message, shop.name);
      },
    });
    if (paymentResult.status === 'paid') {
      mergeFoodOrdersIntoState(placedOrders, { assumeVerifiedPayment: true });
      setFoodStatus(
        isFoodDemoEnabled()
          ? `Demo order completed successfully with ${shop.name}.`
          : `Payment successful. Order confirmed with ${shop.name}.`,
        false,
      );
      log(isFoodDemoEnabled() ? `Food demo order completed (${shop.name})` : `Food order paid (${shop.name})`);
      await clearFoodCart({ silent: true });
      closeFoodCartModal();
      renderFoodOrders();
      renderFoodOrderStatusTimeline();
      void refreshFoodModule({ forceFreshOrders: true, silentStatus: true }).catch((error) => {
        log(`Fresh food order refresh delayed: ${error?.message || 'Unknown error'}`);
      });
    } else if (paymentResult.status === 'dismissed') {
      setFoodStatus('Payment window closed. You can retry from Payment Recovery.', true);
      await refreshFoodModule();
    } else {
      setFoodStatus(`Payment failed: ${paymentResult.message || 'Please retry.'}`, true);
      await refreshFoodModule();
    }
  } finally {
    if (checkoutBtn) {
      delete checkoutBtn.dataset.processing;
      checkoutBtn.textContent = isFoodDemoEnabled() ? 'Place Demo Order' : 'Pay & Place Order';
    }
    syncFoodOrderActionState();
  }
}

async function createFoodItem() {
  const name = String(els.foodNewItemName?.value || '').trim();
  const price = Number(els.foodNewItemPrice?.value || 0);
  if (!name || !Number.isFinite(price) || price <= 0) {
    throw new Error('Provide valid food item name and price.');
  }
  await api('/food/items', {
    method: 'POST',
    body: JSON.stringify({ name, price }),
  });
  if (els.foodNewItemName) {
    els.foodNewItemName.value = '';
  }
  if (els.foodNewItemPrice) {
    els.foodNewItemPrice.value = '';
  }
  setFoodStatus(`Food item "${name}" created.`, false);
  await refreshFoodModule();
}

async function createFoodSlot() {
  const label = String(els.foodNewSlotLabel?.value || '').trim();
  const startTime = String(els.foodNewSlotStart?.value || '').trim();
  const endTime = String(els.foodNewSlotEnd?.value || '').trim();
  const maxOrders = Number(els.foodNewSlotCapacity?.value || 0);
  if (!label || !startTime || !endTime || !Number.isFinite(maxOrders) || maxOrders <= 0) {
    throw new Error('Provide slot label, start/end time, and valid capacity.');
  }
  await api('/food/slots', {
    method: 'POST',
    body: JSON.stringify({
      label,
      start_time: startTime,
      end_time: endTime,
      max_orders: maxOrders,
    }),
  });
  if (els.foodNewSlotLabel) {
    els.foodNewSlotLabel.value = '';
  }
  if (els.foodNewSlotStart) {
    els.foodNewSlotStart.value = '';
  }
  if (els.foodNewSlotEnd) {
    els.foodNewSlotEnd.value = '';
  }
  if (els.foodNewSlotCapacity) {
    els.foodNewSlotCapacity.value = '';
  }
  setFoodStatus(`Break slot "${label}" created.`, false);
  await refreshFoodModule();
}

function renderWorkloadChart() {
  if (!els.workloadChart) {
    return;
  }
  els.workloadChart.innerHTML = '';
  const rows = Array.isArray(state.resources.workload) ? state.resources.workload : [];
  if (!rows.length) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'Workload metrics are visible to faculty/admin roles.';
    els.workloadChart.appendChild(row);
    return;
  }

  for (const item of rows) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.innerHTML = `
      <span>${escapeHtml(item.faculty_name || `Faculty #${item.faculty_id}`)}</span>
      <span>${Number(item.assigned_courses || 0)} courses • ${Number(item.total_enrolled_students || 0)} students</span>
    `;
    els.workloadChart.appendChild(row);
  }
}

function renderMongoStatus() {
  if (!els.mongoSyncStatus) {
    return;
  }
  const status = state.resources.mongoStatus;
  if (!status || !status.connected) {
    els.mongoSyncStatus.textContent = 'Mongo: Offline';
    return;
  }
  const dbName = status.database ? String(status.database) : 'Connected';
  els.mongoSyncStatus.textContent = `Mongo: ${dbName}`;
}

function setRmsStatus(message, isError = false, state = 'neutral') {
  if (!els.rmsStatusMsg) {
    return;
  }
  setUiStateMessage(els.rmsStatusMsg, message, {
    state: isError ? 'error' : state,
  });
}

function setRmsStudentUpdateStatus(message, isError = false, state = 'neutral') {
  if (!els.rmsStudentUpdateMsg) {
    return;
  }
  setUiStateMessage(els.rmsStudentUpdateMsg, message, {
    state: isError ? 'error' : state,
  });
}

function setRmsThreadActionStatus(message, isError = false, state = 'neutral') {
  if (!els.rmsThreadActionMsg) {
    return;
  }
  setUiStateMessage(els.rmsThreadActionMsg, message, {
    state: isError ? 'error' : state,
  });
}

function setRmsAttendanceStatus(message, isError = false, state = 'neutral') {
  if (!els.rmsAttendanceStatusMsg) {
    return;
  }
  setUiStateMessage(els.rmsAttendanceStatusMsg, message, {
    state: isError ? 'error' : state,
  });
}

function formatRmsActionStateLabel(rawState) {
  const stateLabel = String(rawState || '').trim().toLowerCase();
  if (stateLabel === 'approved') {
    return 'Approved';
  }
  if (stateLabel === 'disapproved') {
    return 'Disapproved';
  }
  if (stateLabel === 'scheduled') {
    return 'Scheduled';
  }
  return 'No workflow action';
}

function syncRmsThreadActionForm() {
  const action = String(els.rmsThreadAction?.value || state.rms.threadAction || 'approve').trim().toLowerCase();
  state.rms.threadAction = action === 'schedule' ? 'schedule' : action === 'disapprove' ? 'disapprove' : 'approve';
  const isSchedule = state.rms.threadAction === 'schedule';
  if (els.rmsThreadScheduleWrap) {
    setHidden(els.rmsThreadScheduleWrap, !isSchedule);
  }
}

function renderRmsSelectedThreadSummary(thread = state.rms.selectedThread) {
  if (!els.rmsSelectedThread) {
    return;
  }
  if (!thread || Number(thread.student_id || 0) <= 0 || Number(thread.faculty_id || 0) <= 0) {
    els.rmsSelectedThread.textContent = 'Select a thread from the list to apply workflow action.';
    return;
  }
  const stateLabel = formatRmsActionStateLabel(thread.action_state);
  const studentName = String(thread.student_name || `Student #${Number(thread.student_id || 0)}`);
  const facultyName = String(thread.faculty_name || `Faculty #${Number(thread.faculty_id || 0)}`);
  const category = String(thread.category || 'Other');
  const registration = String(thread.student_registration_number || '').trim() || 'No Reg';
  const section = String(thread.section || '').trim() || 'UNASSIGNED';
  const scheduledFor = thread.scheduled_for ? new Date(thread.scheduled_for).toLocaleString() : '';
  const actionByRole = String(thread.action_by_role || '').trim();
  const actionAt = thread.action_updated_at ? new Date(thread.action_updated_at).toLocaleString() : '';
  const actionNote = String(thread.action_note || '').trim();
  const actionMetaParts = [stateLabel];
  if (scheduledFor) {
    actionMetaParts.push(`Scheduled: ${scheduledFor}`);
  }
  if (actionByRole) {
    actionMetaParts.push(`By: ${actionByRole}`);
  }
  if (actionAt) {
    actionMetaParts.push(`At: ${actionAt}`);
  }
  if (actionNote) {
    actionMetaParts.push(`Note: ${actionNote}`);
  }

  els.rmsSelectedThread.textContent = [
    `Student: ${studentName} (${registration})`,
    `Faculty: ${facultyName}`,
    `Category: ${category}`,
    `Section: ${section}`,
    `Workflow: ${actionMetaParts.join(' | ')}`,
  ].join(' | ');
}

function findRmsThreadInDashboard(selectedThread, dashboard = state.rms.dashboard) {
  if (!selectedThread || !dashboard || !Array.isArray(dashboard.categories)) {
    return null;
  }
  const targetStudentId = Number(selectedThread.student_id || 0);
  const targetFacultyId = Number(selectedThread.faculty_id || 0);
  const targetCategory = String(selectedThread.category || '').trim().toLowerCase();
  if (targetStudentId <= 0 || targetFacultyId <= 0 || !targetCategory) {
    return null;
  }
  for (const bucket of dashboard.categories) {
    const threads = Array.isArray(bucket?.threads) ? bucket.threads : [];
    for (const thread of threads) {
      if (
        Number(thread?.student_id || 0) === targetStudentId
        && Number(thread?.faculty_id || 0) === targetFacultyId
        && String(thread?.category || '').trim().toLowerCase() === targetCategory
      ) {
        return thread;
      }
    }
  }
  return null;
}

function renderRmsStudentSummary(student = state.rms.selectedStudent) {
  if (!els.rmsStudentSummary) {
    return;
  }
  if (!student || Number(student.student_id || 0) <= 0) {
    els.rmsStudentSummary.textContent = 'Search a student to load profile and pending query context.';
    return;
  }
  const registration = String(student.registration_number || '').trim() || 'Not set';
  const section = String(student.section || '').trim() || 'Not set';
  const pending = Number(student.pending_query_count || 0);
  const recent = Number(student.recent_query_count || 0);
  const lastAt = student.last_query_at
    ? new Date(student.last_query_at).toLocaleString()
    : 'No query history';
  els.rmsStudentSummary.textContent = [
    `${String(student.name || `Student #${student.student_id}`)} (${String(student.email || 'no-email')})`,
    `Reg: ${registration}`,
    `Section: ${section}`,
    `Queries: ${recent} total, ${pending} pending`,
    `Last Query: ${lastAt}`,
  ].join(' | ');
}

function renderRmsAttendanceResult(result = state.rms.attendanceUpdate) {
  if (!els.rmsAttendanceResult) {
    return;
  }
  if (!result || Number(result.record_id || 0) <= 0) {
    els.rmsAttendanceResult.innerHTML = '<div class="list-item">No attendance override applied yet.</div>';
    return;
  }
  const updatedStatus = statusLabel(result.updated_status || '--');
  const previousStatus = result.previous_status ? statusLabel(result.previous_status) : 'Not marked';
  const attendanceDate = String(result.attendance_date || '--');
  const note = String(result.note || '').trim();
  const slotLabel = (
    result.class_start_time && result.class_end_time
      ? `${formatTime(result.class_start_time)} - ${formatTime(result.class_end_time)}`
      : '--'
  );
  const meta = [
    `Reg: ${String(result.registration_number || '--')}`,
    `Course: ${String(result.course_code || '--')} (${String(result.course_title || 'Course')})`,
    `Slot: ${slotLabel}`,
    `Date: ${attendanceDate}`,
    `Status: ${updatedStatus} (was ${previousStatus})`,
    `Faculty: ${String(result.faculty_name || `#${Number(result.faculty_id || 0)}`)}`,
    `Source: ${String(result.source || '--')}`,
  ];
  if (Number(result.schedule_id || 0) > 0) {
    meta.push(`Schedule ID: #${Number(result.schedule_id)}`);
  }
  if (String(result.classroom_label || '').trim()) {
    meta.push(`Room: ${String(result.classroom_label).trim()}`);
  }
  if (result.message_sent) {
    meta.push('Student Notified: Yes');
  }
  if (note) {
    meta.push(`Note: ${note}`);
  }
  els.rmsAttendanceResult.innerHTML = `<div class="list-item">${escapeHtml(meta.join(' | '))}</div>`;
}

function renderRmsAttendanceStudentSummary(context = state.rms.attendanceContext) {
  if (!els.rmsAttendanceStudentSummary) {
    return;
  }
  if (!context || typeof context !== 'object' || !context.student) {
    els.rmsAttendanceStudentSummary.textContent = 'Search by registration number to load student day-wise classes.';
    return;
  }
  const student = context.student;
  const subjects = Array.isArray(context.subjects) ? context.subjects : [];
  const slotCount = subjects.reduce((sum, row) => (
    sum + (Array.isArray(row?.slots) ? row.slots.length : 0)
  ), 0);
  const dateLabel = String(context.attendance_date || '').trim() || todayISO();
  const reg = String(student.registration_number || '').trim() || 'Not set';
  const section = String(student.section || '').trim() || 'Not set';
  els.rmsAttendanceStudentSummary.textContent = [
    `${String(student.name || `Student #${Number(student.student_id || 0)}`)} (${String(student.email || 'no-email')})`,
    `Reg: ${reg}`,
    `Section: ${section}`,
    `Subjects: ${subjects.length}`,
    `Slots: ${slotCount}`,
    `Date: ${dateLabel}`,
  ].join(' | ');
}

function resolveRmsAttendanceSelectedSubject(context = state.rms.attendanceContext) {
  const rows = Array.isArray(context?.subjects) ? context.subjects : [];
  if (!rows.length) {
    return null;
  }
  const selectedCourseCode = String(state.rms.attendanceSelectedCourseCode || '').trim().toUpperCase();
  if (!selectedCourseCode) {
    return null;
  }
  return rows.find((row) => String(row?.course_code || '').trim().toUpperCase() === selectedCourseCode) || null;
}

function resolveRmsAttendanceSlotsForSelectedSubject(context = state.rms.attendanceContext) {
  const subject = resolveRmsAttendanceSelectedSubject(context);
  if (!subject || !Array.isArray(subject?.slots)) {
    return [];
  }
  return subject.slots;
}

function resolveRmsAttendanceSelectedSlot(context = state.rms.attendanceContext) {
  const slots = resolveRmsAttendanceSlotsForSelectedSubject(context);
  if (!slots.length) {
    return null;
  }
  const selectedScheduleId = Number(
    state.rms.attendanceSelectedScheduleId
    || els.rmsAttendanceSlotSelect?.value
    || 0,
  );
  if (!selectedScheduleId) {
    return null;
  }
  return slots.find((row) => Number(row?.schedule_id || 0) === selectedScheduleId) || null;
}

function syncRmsAttendanceCurrentStatus() {
  const selectedSlot = resolveRmsAttendanceSelectedSlot();
  const selectedSubject = resolveRmsAttendanceSelectedSubject();
  if (!els.rmsAttendanceCurrentStatus) {
    return;
  }
  if (!selectedSlot && !selectedSubject) {
    els.rmsAttendanceCurrentStatus.value = 'Not marked';
    if (els.rmsAttendanceStatus) {
      els.rmsAttendanceStatus.value = 'present';
    }
    return;
  }
  const statusRaw = String(
    selectedSlot?.current_status
      || selectedSubject?.current_status
      || '',
  ).trim().toLowerCase();
  const statusLabel = String(
    selectedSlot?.current_status_label
      || selectedSubject?.current_status_label
      || '',
  ).trim() || 'Not marked';
  els.rmsAttendanceCurrentStatus.value = statusLabel;
  if (!els.rmsAttendanceStatus) {
    return;
  }
  if (statusRaw === 'present' || statusRaw === 'absent') {
    els.rmsAttendanceStatus.value = statusRaw;
  } else {
    els.rmsAttendanceStatus.value = 'present';
  }
}

function renderRmsAttendanceSlotOptions(context = state.rms.attendanceContext) {
  if (!els.rmsAttendanceSlotSelect) {
    return;
  }
  const subject = resolveRmsAttendanceSelectedSubject(context);
  const slots = Array.isArray(subject?.slots) ? subject.slots : [];
  els.rmsAttendanceSlotSelect.innerHTML = '';

  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = !subject
    ? 'Select subject first'
    : (slots.length ? 'Select time slot' : 'No class slots');
  els.rmsAttendanceSlotSelect.appendChild(placeholder);

  for (const slot of slots) {
    const scheduleId = Number(slot?.schedule_id || 0);
    if (!scheduleId) {
      continue;
    }
    const option = document.createElement('option');
    option.value = String(scheduleId);
    const statusLabel = String(slot?.current_status_label || '').trim();
    const roomLabel = String(slot?.classroom_label || '').trim();
    const labelParts = [
      `${formatTime24(slot?.start_time)}-${formatTime24(slot?.end_time)}`,
    ];
    if (roomLabel) {
      labelParts.push(roomLabel);
    }
    if (statusLabel) {
      labelParts.push(`Current: ${statusLabel}`);
    }
    option.textContent = labelParts.join(' | ');
    els.rmsAttendanceSlotSelect.appendChild(option);
  }

  if (slots.length) {
    const selectedScheduleId = Number(state.rms.attendanceSelectedScheduleId || 0);
    const hasSelected = selectedScheduleId > 0
      && slots.some((row) => Number(row?.schedule_id || 0) === selectedScheduleId);
    const resolvedScheduleId = hasSelected
      ? selectedScheduleId
      : Number(slots[0]?.schedule_id || 0);
    state.rms.attendanceSelectedScheduleId = resolvedScheduleId > 0 ? resolvedScheduleId : null;
    els.rmsAttendanceSlotSelect.value = resolvedScheduleId > 0 ? String(resolvedScheduleId) : '';
  } else {
    state.rms.attendanceSelectedScheduleId = null;
    els.rmsAttendanceSlotSelect.value = '';
  }
}

function renderRmsAttendanceSubjectOptions(context = state.rms.attendanceContext) {
  if (!els.rmsAttendanceSubjectSelect) {
    return;
  }
  const rows = Array.isArray(context?.subjects) ? context.subjects : [];
  const hasStudentContext = Boolean(context && typeof context === 'object' && context.student);
  els.rmsAttendanceSubjectSelect.innerHTML = '';
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = rows.length ? 'Select subject' : (hasStudentContext ? 'No enrolled subjects' : 'Select subject');
  els.rmsAttendanceSubjectSelect.appendChild(placeholder);

  for (const row of rows) {
    const courseCode = String(row?.course_code || '').trim().toUpperCase();
    if (!courseCode) {
      continue;
    }
    const labelParts = [
      courseCode,
      String(row?.course_title || 'Course').trim(),
    ];
    const statusLabel = String(row?.current_status_label || '').trim();
    if (statusLabel) {
      labelParts.push(`Current: ${statusLabel}`);
    }
    const option = document.createElement('option');
    option.value = courseCode;
    option.textContent = labelParts.join(' | ');
    els.rmsAttendanceSubjectSelect.appendChild(option);
  }

  if (rows.length) {
    const selectedCourseCode = String(state.rms.attendanceSelectedCourseCode || '').trim().toUpperCase();
    const optionExists = rows.some(
      (row) => String(row?.course_code || '').trim().toUpperCase() === selectedCourseCode,
    );
    if (selectedCourseCode && optionExists) {
      els.rmsAttendanceSubjectSelect.value = selectedCourseCode;
    } else {
      const firstCode = String(rows[0]?.course_code || '').trim().toUpperCase();
      state.rms.attendanceSelectedCourseCode = firstCode;
      els.rmsAttendanceSubjectSelect.value = firstCode;
    }
  } else {
    state.rms.attendanceSelectedCourseCode = '';
    state.rms.attendanceSelectedScheduleId = null;
    els.rmsAttendanceSubjectSelect.value = '';
  }
  renderRmsAttendanceSlotOptions(context);
  syncRmsAttendanceCurrentStatus();
}

function renderRmsQueryBuckets() {
  if (!els.rmsQueryList) {
    return;
  }
  els.rmsQueryList.innerHTML = '';
  const dashboard = state.rms.dashboard;
  const categories = Array.isArray(dashboard?.categories) ? dashboard.categories : [];

  if (!categories.length) {
    els.rmsQueryList.innerHTML = '<div class="list-item">No RMS queries found for current filters.</div>';
    return;
  }

  for (const bucket of categories) {
    const category = String(bucket?.category || 'Other');
    const total = Number(bucket?.total_threads || 0);
    const pending = Number(bucket?.pending_threads || 0);
    const threads = Array.isArray(bucket?.threads) ? bucket.threads : [];

    const block = document.createElement('section');
    block.className = 'rms-thread-list';

    const title = document.createElement('h4');
    title.className = 'rms-category-title';
    title.textContent = `${category} (${total}) • Pending ${pending}`;
    block.appendChild(title);

    if (!threads.length) {
      const empty = document.createElement('div');
      empty.className = 'list-item';
      empty.textContent = 'No threads in this category.';
      block.appendChild(empty);
      els.rmsQueryList.appendChild(block);
      continue;
    }

    for (const thread of threads) {
      const pendingAction = Boolean(thread?.pending_action);
      const actionState = String(thread?.action_state || 'none').trim().toLowerCase() || 'none';
      const threadStatusTone = pendingAction
        ? 'pending'
        : actionState === 'approved'
          ? 'approved'
          : actionState === 'disapproved'
            ? 'disapproved'
            : actionState === 'scheduled'
              ? 'scheduled'
              : 'resolved';
      const row = document.createElement('div');
      row.className = `rms-thread-row ${pendingAction ? 'pending' : 'resolved'} action-${actionState}`;

      const studentName = String(thread?.student_name || `Student #${Number(thread?.student_id || 0)}`);
      const studentReg = String(thread?.student_registration_number || '').trim();
      const facultyName = String(thread?.faculty_name || `Faculty #${Number(thread?.faculty_id || 0)}`);
      const subject = String(thread?.subject || 'General Query');
      const message = String(thread?.last_message || '').trim() || 'No message body.';
      const section = String(thread?.section || '').trim() || 'UNASSIGNED';
      const threadCategory = String(thread?.category || category || 'Other');
      const unreadFromStudent = Number(thread?.unread_from_student || 0);
      const lastCreatedAt = thread?.last_created_at ? new Date(thread.last_created_at).toLocaleString() : '--';
      const senderRole = String(thread?.last_sender_role || '').trim().toLowerCase() || 'student';
      const actionLabel = formatRmsActionStateLabel(actionState);
      const actionNote = String(thread?.action_note || '').trim();
      const scheduledFor = thread?.scheduled_for ? new Date(thread.scheduled_for).toLocaleString() : '';
      const actionByRole = String(thread?.action_by_role || '').trim();
      const actionUpdatedAt = thread?.action_updated_at ? new Date(thread.action_updated_at).toLocaleString() : '';
      const threadActionMeta = [actionLabel];
      if (scheduledFor) {
        threadActionMeta.push(`Scheduled: ${scheduledFor}`);
      }
      if (actionByRole) {
        threadActionMeta.push(`By: ${actionByRole}`);
      }
      if (actionUpdatedAt) {
        threadActionMeta.push(`At: ${actionUpdatedAt}`);
      }
      if (actionNote) {
        threadActionMeta.push(`Note: ${actionNote}`);
      }
      const selectThreadBtn = `
        <button
          class="btn btn-primary"
          type="button"
          data-rms-select-thread="1"
          data-rms-thread-student-id="${Number(thread?.student_id || 0)}"
          data-rms-thread-faculty-id="${Number(thread?.faculty_id || 0)}"
          data-rms-thread-category="${escapeHtml(threadCategory)}"
        >Select Thread</button>
      `;
      const useRegBtn = studentReg
        ? `<button class="btn btn-ghost" type="button" data-rms-use-reg="${escapeHtml(studentReg)}">Load Student</button>`
        : '';
      const registrationMarkup = studentReg
        ? `<span class="rms-thread-registration">${escapeHtml(studentReg)}</span>`
        : '';
      const unreadBadge = unreadFromStudent > 0
        ? `<span class="rms-thread-badge rms-thread-badge--unread">${unreadFromStudent} unread</span>`
        : '';

      row.innerHTML = `
        <div class="rms-thread-head">
          <div class="rms-thread-identity">
            <div class="rms-thread-title-row">
              <strong>${escapeHtml(studentName)}</strong>
              ${registrationMarkup}
            </div>
            <div class="rms-thread-support">
              <span class="rms-thread-chip rms-thread-chip--subject">${escapeHtml(subject)}</span>
              <span class="rms-thread-chip">Section ${escapeHtml(section)}</span>
              <span class="rms-thread-badge rms-thread-badge--${threadStatusTone}">${escapeHtml(actionLabel)}</span>
              ${unreadBadge}
            </div>
          </div>
          <div class="rms-thread-head-controls">${selectThreadBtn}${useRegBtn}</div>
        </div>
        <div class="rms-thread-message">${escapeHtml(message)}</div>
        <div class="rms-thread-meta-grid">
          <div class="rms-thread-meta">
            <span class="rms-thread-meta-label">Faculty</span>
            <span>${escapeHtml(facultyName)}</span>
          </div>
          <div class="rms-thread-meta">
            <span class="rms-thread-meta-label">Latest activity</span>
            <span>${escapeHtml(`By ${senderRole} at ${lastCreatedAt}`)}</span>
          </div>
          <div class="rms-thread-meta rms-thread-meta--full">
            <span class="rms-thread-meta-label">Workflow</span>
            <span>${escapeHtml(threadActionMeta.join(' | '))}</span>
          </div>
        </div>
      `;
      block.appendChild(row);
    }
    els.rmsQueryList.appendChild(block);
  }
}

function renderRmsDashboard() {
  const dashboard = state.rms.dashboard;
  const totalThreads = Number(dashboard?.total_threads || 0);
  const totalPending = Number(dashboard?.total_pending || 0);
  const categories = Array.isArray(dashboard?.categories) ? dashboard.categories : [];
  const activeCategories = categories.filter((bucket) => Number(bucket?.total_threads || 0) > 0).length;

  if (els.rmsTotalThreads) {
    animateNumber(els.rmsTotalThreads, totalThreads);
  }
  if (els.rmsTotalPending) {
    animateNumber(els.rmsTotalPending, totalPending);
  }
  if (els.rmsActiveCategories) {
    animateNumber(els.rmsActiveCategories, activeCategories);
  }
  renderRmsQueryBuckets();
}

async function refreshRmsModule({ silent = false } = {}) {
  if (!authState.user || (authState.user.role !== 'admin' && authState.user.role !== 'faculty')) {
    return;
  }
  const category = String(els.rmsQueryCategory?.value || state.rms.selectedCategory || 'all').trim() || 'all';
  const status = String(els.rmsQueryStatus?.value || state.rms.selectedStatus || 'all').trim() || 'all';
  state.rms.selectedCategory = category;
  state.rms.selectedStatus = status;

  const payload = await api(
    `/admin/rms/queries?category=${encodeURIComponent(category)}&status=${encodeURIComponent(status)}&limit=300`
  );
  state.rms.dashboard = payload && typeof payload === 'object' ? payload : null;
  if (state.rms.selectedThread) {
    const refreshedThread = findRmsThreadInDashboard(state.rms.selectedThread, state.rms.dashboard);
    state.rms.selectedThread = refreshedThread || null;
  }
  renderRmsDashboard();
  renderRmsSelectedThreadSummary();
  if (!silent) {
    setRmsStatus('RMS query buckets refreshed.');
  }
}

async function searchRmsStudentByRegistration({ silent = false } = {}) {
  if (!authState.user || (authState.user.role !== 'admin' && authState.user.role !== 'faculty')) {
    throw new Error('Only admin or faculty can use RMS student search.');
  }
  const registrationNumber = normalizedRegistrationInput(els.rmsSearchRegistration?.value || '');
  if (!registrationNumber) {
    throw new Error('Enter student registration number.');
  }
  if (els.rmsSearchRegistration) {
    els.rmsSearchRegistration.value = registrationNumber;
  }

  const payload = await api(
    `/admin/rms/students/search?registration_number=${encodeURIComponent(registrationNumber)}`
  );
  state.rms.selectedStudent = payload && typeof payload === 'object' ? payload : null;
  if (els.rmsUpdateRegistration && state.rms.selectedStudent) {
    els.rmsUpdateRegistration.value = String(state.rms.selectedStudent.registration_number || registrationNumber);
  }
  if (els.rmsAttendanceRegistration && state.rms.selectedStudent) {
    els.rmsAttendanceRegistration.value = String(state.rms.selectedStudent.registration_number || registrationNumber);
  }
  state.rms.attendanceContext = null;
  state.rms.attendanceSelectedCourseCode = '';
  state.rms.attendanceSelectedScheduleId = null;
  renderRmsAttendanceStudentSummary(null);
  renderRmsAttendanceSubjectOptions(null);
  if (els.rmsUpdateSection && state.rms.selectedStudent) {
    els.rmsUpdateSection.value = String(state.rms.selectedStudent.section || '').trim().toUpperCase();
  }
  renderRmsStudentSummary();
  syncVisibleVerlynQuickActions();
  if (!silent && state.rms.selectedStudent) {
    setRmsStatus(
      `Loaded ${String(state.rms.selectedStudent.name || '')} for RMS approval actions.`,
      false,
    );
  }
}

async function searchRmsAttendanceStudentContext({ silent = false } = {}) {
  if (!authState.user || (authState.user.role !== 'admin' && authState.user.role !== 'faculty')) {
    throw new Error('Only admin or faculty can use RMS attendance controls.');
  }
  const registrationNumber = normalizedRegistrationInput(els.rmsAttendanceRegistration?.value || '');
  const attendanceDate = String(els.rmsAttendanceDate?.value || '').trim() || todayISO();
  if (!registrationNumber) {
    throw new Error('Enter student registration number before searching subjects.');
  }
  if (els.rmsAttendanceRegistration) {
    els.rmsAttendanceRegistration.value = registrationNumber;
  }
  if (els.rmsAttendanceDate) {
    els.rmsAttendanceDate.value = attendanceDate;
  }

  const payload = await api(
    `/admin/rms/attendance/student-context?registration_number=${encodeURIComponent(registrationNumber)}&attendance_date=${encodeURIComponent(attendanceDate)}`,
  );
  state.rms.attendanceContext = payload && typeof payload === 'object' ? payload : null;
  state.rms.attendanceSelectedScheduleId = null;
  state.rms.selectedStudent = state.rms.attendanceContext?.student || state.rms.selectedStudent;
  if (state.rms.selectedStudent && els.rmsUpdateRegistration) {
    els.rmsUpdateRegistration.value = String(state.rms.selectedStudent.registration_number || registrationNumber);
  }
  if (state.rms.selectedStudent && els.rmsUpdateSection) {
    els.rmsUpdateSection.value = String(state.rms.selectedStudent.section || '').trim().toUpperCase();
  }
  renderRmsStudentSummary();
  renderRmsAttendanceStudentSummary();
  renderRmsAttendanceSubjectOptions();
  syncVisibleVerlynQuickActions();
  const loadedCount = Array.isArray(state.rms.attendanceContext?.subjects) ? state.rms.attendanceContext.subjects.length : 0;
  if (!silent) {
    setRmsAttendanceStatus(
      loadedCount > 0
        ? `Loaded ${loadedCount} subject(s). Select subject and slot, then apply updated status.`
        : String(state.rms.attendanceContext?.message || 'No enrolled subjects found for this registration number.'),
      false,
    );
  }
}

async function applyRmsStudentApprovalUpdate() {
  if (!authState.user || (authState.user.role !== 'admin' && authState.user.role !== 'faculty')) {
    throw new Error('Only admin or faculty can apply RMS approvals.');
  }
  if (!state.rms.selectedStudent || Number(state.rms.selectedStudent.student_id || 0) <= 0) {
    throw new Error('Search and load a student before applying updates.');
  }

  const studentId = Number(state.rms.selectedStudent.student_id);
  const registrationNumber = normalizedRegistrationInput(els.rmsUpdateRegistration?.value || '');
  const section = String(els.rmsUpdateSection?.value || '')
    .trim()
    .toUpperCase()
    .replace(/\s+/g, '');

  const payload = {};
  if (registrationNumber) {
    payload.registration_number = registrationNumber;
  }
  if (section) {
    payload.section = section;
  }
  if (!Object.keys(payload).length) {
    throw new Error('Enter corrected registration number and/or section before applying update.');
  }

  const saved = await api(`/admin/rms/students/${studentId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  state.rms.selectedStudent = saved?.student || state.rms.selectedStudent;
  if (els.rmsSearchRegistration && state.rms.selectedStudent?.registration_number) {
    els.rmsSearchRegistration.value = String(state.rms.selectedStudent.registration_number);
  }
  if (els.rmsUpdateRegistration && state.rms.selectedStudent) {
    els.rmsUpdateRegistration.value = String(state.rms.selectedStudent.registration_number || '');
  }
  if (els.rmsUpdateSection && state.rms.selectedStudent) {
    els.rmsUpdateSection.value = String(state.rms.selectedStudent.section || '');
  }
  renderRmsStudentSummary();
  syncVisibleVerlynQuickActions();
  setRmsStudentUpdateStatus(
    String(saved?.message || 'RMS approval update applied successfully.'),
    false,
  );
  log(`RMS update applied for student ${studentId}.`);
  await refreshRmsModule({ silent: true });
}

async function applyRmsAttendanceStatusUpdate() {
  if (!authState.user || (authState.user.role !== 'admin' && authState.user.role !== 'faculty')) {
    throw new Error('Only admin or faculty can apply RMS attendance updates.');
  }
  const selectedSubject = resolveRmsAttendanceSelectedSubject();
  const registrationNumber = normalizedRegistrationInput(els.rmsAttendanceRegistration?.value || '');
  const courseCode = String(
    els.rmsAttendanceSubjectSelect?.value
      || state.rms.attendanceSelectedCourseCode
      || '',
  )
    .trim()
    .toUpperCase();
  const scheduleId = Number(
    els.rmsAttendanceSlotSelect?.value
      || state.rms.attendanceSelectedScheduleId
      || 0,
  ) || null;
  const attendanceDate = String(els.rmsAttendanceDate?.value || '').trim() || todayISO();
  const status = String(els.rmsAttendanceStatus?.value || '').trim().toLowerCase();
  const note = String(els.rmsAttendanceNote?.value || '').trim();

  if (!registrationNumber) {
    throw new Error('Enter student registration number for attendance update.');
  }
  if (!courseCode) {
    throw new Error('Select subject for attendance update.');
  }
  if (!scheduleId) {
    throw new Error('Select class time slot for attendance update.');
  }
  if (status !== 'present' && status !== 'absent') {
    throw new Error('Select valid attendance status.');
  }

  if (els.rmsAttendanceRegistration) {
    els.rmsAttendanceRegistration.value = registrationNumber;
  }
  if (els.rmsAttendanceSubjectSelect) {
    els.rmsAttendanceSubjectSelect.value = courseCode;
  }
  if (els.rmsAttendanceSlotSelect) {
    els.rmsAttendanceSlotSelect.value = String(scheduleId);
  }
  if (els.rmsAttendanceDate && !els.rmsAttendanceDate.value) {
    els.rmsAttendanceDate.value = attendanceDate;
  }
  state.rms.attendanceSelectedCourseCode = courseCode;
  state.rms.attendanceSelectedScheduleId = scheduleId;

  const payload = {
    registration_number: registrationNumber,
    course_code: courseCode,
    schedule_id: scheduleId,
    attendance_date: attendanceDate,
    status,
  };
  if (note) {
    payload.note = note;
  }

  const saved = await api('/admin/rms/attendance/status', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  state.rms.attendanceUpdate = saved && typeof saved === 'object' ? saved : null;
  renderRmsAttendanceResult();
  try {
    await searchRmsAttendanceStudentContext({ silent: true });
    syncRmsAttendanceCurrentStatus();
  } catch (error) {
    log(error?.message || 'Attendance context refresh failed after status update.');
  }
  const messageBits = [String(saved?.message || 'RMS attendance status updated successfully.')];
  if (saved?.message_sent) {
    messageBits.push('Student message sent.');
  }
  setRmsAttendanceStatus(
    messageBits.join(' '),
    false,
  );
  if (els.rmsAttendanceNote) {
    els.rmsAttendanceNote.value = '';
  }
  const selectedSlot = resolveRmsAttendanceSelectedSlot()
    || (
      Array.isArray(selectedSubject?.slots)
        ? selectedSubject.slots.find((slot) => Number(slot?.schedule_id || 0) === scheduleId)
        : null
    );
  const slotText = selectedSlot?.start_time && selectedSlot?.end_time
    ? `${formatTime24(selectedSlot.start_time)}-${formatTime24(selectedSlot.end_time)}`
    : `schedule #${scheduleId}`;
  log(
    `RMS attendance updated for ${registrationNumber} (${courseCode}, ${slotText}) on ${attendanceDate} as ${status}.`,
  );
}

async function applyRmsQueryWorkflowAction() {
  if (!authState.user || (authState.user.role !== 'admin' && authState.user.role !== 'faculty')) {
    throw new Error('Only admin or faculty can apply RMS workflow actions.');
  }
  const selectedThread = state.rms.selectedThread;
  if (!selectedThread || Number(selectedThread.student_id || 0) <= 0 || Number(selectedThread.faculty_id || 0) <= 0) {
    throw new Error('Select an RMS thread before applying workflow action.');
  }

  const action = String(els.rmsThreadAction?.value || state.rms.threadAction || 'approve').trim().toLowerCase();
  if (action !== 'approve' && action !== 'disapprove' && action !== 'schedule') {
    throw new Error('Select a valid workflow action.');
  }
  state.rms.threadAction = action;

  const note = String(els.rmsThreadNote?.value || '').trim();
  const payload = {
    student_id: Number(selectedThread.student_id),
    faculty_id: Number(selectedThread.faculty_id),
    category: String(selectedThread.category || 'Other'),
    action,
  };
  if (note) {
    payload.note = note;
  }
  if (action === 'schedule') {
    const scheduledRaw = String(els.rmsThreadScheduledFor?.value || '').trim();
    if (!scheduledRaw) {
      throw new Error('Select schedule date/time for schedule action.');
    }
    const scheduledDate = new Date(scheduledRaw);
    if (Number.isNaN(scheduledDate.getTime())) {
      throw new Error('Schedule date/time is invalid.');
    }
    payload.scheduled_for = scheduledDate.toISOString();
  }

  const saved = await api('/admin/rms/queries/action', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

  state.rms.selectedThread = saved?.thread || selectedThread;
  renderRmsSelectedThreadSummary();
  setRmsThreadActionStatus(
    String(saved?.message || 'RMS workflow action applied successfully.'),
    false,
  );
  if (els.rmsThreadNote) {
    els.rmsThreadNote.value = '';
  }
  log(
    `RMS workflow action "${action}" applied for student ${Number(selectedThread.student_id)} and faculty ${Number(selectedThread.faculty_id)}.`,
  );
  await refreshRmsModule({ silent: true });
}

async function refreshAdministrativeModule() {
  if (!authState.user || authState.user.role !== 'admin') {
    return;
  }
  if (els.workDate && !els.workDate.value) {
    els.workDate.value = todayISO();
  }
  const workDate = String(els.workDate?.value || todayISO()).trim() || todayISO();
  await Promise.all([
    refreshAdminLive({ workDate, mode: 'enrollment' }),
    refreshAdminInsights({ workDate, mode: 'enrollment' }),
    refreshAdminRecoveryPlans({ silent: true }),
    refreshAdminIdentityCases({ silent: true }),
    refreshDemand(workDate),
    refreshAttendanceData(),
  ]);
  const healthMetrics = computeAdministrativeHealthMetrics();
  renderAdministrativeHealthMetrics(healthMetrics);
  pushAdministrativeTelemetry(healthMetrics);
  renderAdministrativeTelemetryChart();
  renderAdminLiveIndicator();
  renderAdminIssues();
  await refreshCopilotAuditTimeline({ silent: true, force: true });
}

function setAdminCreateScheduleStatus(message, isError = false, state = 'neutral') {
  if (!els.adminCreateScheduleStatus) {
    return;
  }
  setUiStateMessage(els.adminCreateScheduleStatus, message, {
    state: isError ? 'error' : state,
  });
}

function setAdminTimetableOverrideStatus(message, isError = false, state = 'neutral') {
  if (!els.adminTimetableOverrideStatus) {
    return;
  }
  setUiStateMessage(els.adminTimetableOverrideStatus, message, {
    state: isError ? 'error' : state,
  });
}

function setAdminSectionUpdateStatus(message, isError = false, state = 'neutral') {
  if (!els.adminUpdateStudentSectionStatus) {
    return;
  }
  setUiStateMessage(els.adminUpdateStudentSectionStatus, message, {
    state: isError ? 'error' : state,
  });
}

function setAdminSearchStatus(message, isError = false, state = 'neutral') {
  if (!els.adminSearchStatus) {
    return;
  }
  setUiStateMessage(els.adminSearchStatus, message, {
    state: isError ? 'error' : state,
  });
}

function setAdminGradeStatus(message, isError = false, state = 'neutral') {
  if (!els.adminGradeStatus) {
    return;
  }
  setUiStateMessage(els.adminGradeStatus, message, {
    state: isError ? 'error' : state,
  });
}

function setAdminRecoveryStatus(message, isError = false, state = 'neutral') {
  if (!els.adminRecoveryStatus) {
    return;
  }
  setUiStateMessage(els.adminRecoveryStatus, message, {
    state: isError ? 'error' : state,
  });
}

function setAdminIdentityShieldStatus(message, isError = false, state = 'neutral') {
  if (!els.adminIdentityStatus) {
    return;
  }
  setUiStateMessage(els.adminIdentityStatus, message, {
    state: isError ? 'error' : state,
  });
}

function setAdminCopilotAuditStatus(message, isError = false, state = 'neutral') {
  if (!els.adminCopilotAuditStatus) {
    return;
  }
  setUiStateMessage(els.adminCopilotAuditStatus, message, {
    state: isError ? 'error' : state,
  });
}

function identityCaseStatusBadgeClass(statusValue) {
  const normalized = String(statusValue || '').trim().toLowerCase();
  if (normalized === 'verified') {
    return 'verified';
  }
  if (normalized === 'in_review') {
    return 'pending_review';
  }
  if (normalized === 'flagged' || normalized === 'rejected') {
    return 'rejected';
  }
  return 'pending';
}

function identityRiskTone(riskValue) {
  const normalized = String(riskValue || '').trim().toLowerCase();
  if (normalized === 'critical' || normalized === 'high') {
    return 'bad';
  }
  if (normalized === 'medium') {
    return 'pending';
  }
  return 'ok';
}

function renderAdminIdentityCases() {
  if (!els.adminIdentityCasesWrap) {
    return;
  }
  const cases = Array.isArray(state.admin?.identityCases) ? state.admin.identityCases : [];
  if (!cases.length) {
    els.adminIdentityCasesWrap.innerHTML = '<div class="list-item">No identity cases found for the current filter.</div>';
    return;
  }

  els.adminIdentityCasesWrap.innerHTML = cases.map((item) => {
    const workflowKey = String(item?.workflow_key || 'identity').replace(/_/g, ' ');
    const subjectLabel = item?.student_id
      ? `Student #${Number(item.student_id)}`
      : (item?.applicant_email ? String(item.applicant_email) : `User #${Number(item?.auth_user_id || 0)}`);
    const statusLabel = String(item?.status || 'pending').replace(/_/g, ' ');
    const riskLabel = String(item?.risk_level || 'low').toUpperCase();
    const riskScore = Number(item?.risk_score || 0).toFixed(1);
    const updatedAt = adminTimestampLabel(item?.updated_at || item?.created_at, '--');
    const latestReason = String(item?.latest_reason || 'No immediate issue recorded.').trim();
    const signals = Array.isArray(item?.signals) ? item.signals.slice(0, 4) : [];
    const completedChecks = Array.isArray(item?.completed_checks) ? item.completed_checks.slice(0, 3) : [];
    const requestedChecks = Array.isArray(item?.requested_checks) ? item.requested_checks.slice(0, 3) : [];

    return `
      <div class="list-item ${identityRiskTone(item?.risk_level) === 'bad' ? 'warn' : (String(item?.status || '').toLowerCase() === 'verified' ? 'good' : '')}">
        <div class="admin-identity-case-head">
          <div>
            <strong>${escapeHtml(workflowKey.toUpperCase())}</strong>
            <div class="admin-identity-case-meta">${escapeHtml(subjectLabel)} • Updated ${escapeHtml(updatedAt)}</div>
          </div>
          <div class="admin-identity-case-badges">
            <span class="badge ${identityCaseStatusBadgeClass(item?.status)}">${escapeHtml(statusLabel)}</span>
            <span class="attendance-pill ${identityRiskTone(item?.risk_level)}">${escapeHtml(riskLabel)}</span>
          </div>
        </div>
        <div class="admin-identity-case-reason">${escapeHtml(latestReason)}</div>
        <div class="admin-identity-case-meta">Risk score ${escapeHtml(riskScore)} • Signals ${signals.length} • Case #${Number(item?.id || 0)}</div>
        ${signals.length ? `
          <div class="admin-identity-case-signals">
            ${signals.map((signal) => `<span class="admin-identity-signal">${escapeHtml(String(signal?.signal_type || 'signal').replace(/_/g, ' '))}</span>`).join('')}
          </div>
        ` : ''}
        ${(completedChecks.length || requestedChecks.length) ? `
          <div class="admin-identity-case-checks">
            ${completedChecks.length ? `<span>Completed: ${escapeHtml(completedChecks.join(', '))}</span>` : ''}
            ${requestedChecks.length ? `<span>Pending: ${escapeHtml(requestedChecks.join(', '))}</span>` : ''}
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}

async function refreshAdminIdentityCases(options = {}) {
  if (!authState.user || authState.user.role !== 'admin') {
    return [];
  }

  const silent = Boolean(options?.silent);
  const rawStudentId = String(options?.studentId || els.adminIdentityStudentId?.value || '').trim();
  const studentId = rawStudentId ? Number(rawStudentId) : 0;
  const params = new URLSearchParams({ limit: '12' });
  if (Number.isFinite(studentId) && studentId > 0) {
    params.set('student_id', String(studentId));
  }

  if (!silent) {
    setAdminIdentityShieldStatus('Loading identity cases...', false, 'loading');
  }

  const payload = await api(`/identity-shield/cases?${params.toString()}`);
  state.admin.identityCases = Array.isArray(payload) ? payload : [];
  renderAdminIdentityCases();

  if (!silent) {
    const scopeNote = Number.isFinite(studentId) && studentId > 0 ? ` for student ${studentId}` : '';
    setAdminIdentityShieldStatus(
      `Loaded ${state.admin.identityCases.length} identity case(s)${scopeNote}.`,
      false,
      state.admin.identityCases.length ? 'success' : 'empty',
    );
  }

  return state.admin.identityCases;
}

async function runAdminEnrollmentIdentityScreening() {
  if (!authState.user || authState.user.role !== 'admin') {
    throw new Error('Only admin can run identity screening from this panel.');
  }

  const studentId = Number(els.adminIdentityStudentId?.value || 0);
  if (!Number.isFinite(studentId) || studentId <= 0) {
    throw new Error('Enter a valid Student ID before running screening.');
  }

  setAdminIdentityShieldStatus(`Running identity screening for student ${studentId}...`, false, 'loading');
  const saved = await api(`/identity-shield/screenings/enrollment/students/${studentId}`, {
    method: 'POST',
  });
  await refreshAdminIdentityCases({ silent: true, studentId });
  setAdminIdentityShieldStatus(
    `Screening completed for student ${studentId}: ${String(saved?.risk_level || 'low').toUpperCase()} risk, status ${String(saved?.status || 'verified').replace(/_/g, ' ')}.`,
    false,
    String(saved?.status || '').toLowerCase() === 'flagged' ? 'error' : 'success',
  );
  return saved;
}

function renderAdminSearchResultsFromGlobal(payload) {
  if (!els.adminSearchResults) {
    return;
  }
  els.adminSearchResults.innerHTML = '';
  const students = Array.isArray(payload?.students) ? payload.students : [];
  const facultyRows = Array.isArray(payload?.faculty) ? payload.faculty : [];
  const courses = Array.isArray(payload?.courses) ? payload.courses : [];

  if (!students.length && !facultyRows.length && !courses.length) {
    els.adminSearchResults.innerHTML = '<div class="list-item">No results found for this query.</div>';
    return;
  }

  const pushRow = (text) => {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = text;
    els.adminSearchResults.appendChild(row);
  };

  for (const item of students) {
    const reg = String(item?.registration_number || '').trim() || 'NoReg';
    const section = String(item?.section || '').trim() || 'UNASSIGNED';
    pushRow(`Student | ${String(item?.name || '')} | ${reg} | ${section} | ${String(item?.email || '')}`);
  }
  for (const item of facultyRows) {
    const identifier = String(item?.faculty_identifier || '').trim() || 'NoID';
    const section = String(item?.section || '').trim() || 'UNASSIGNED';
    pushRow(`Faculty | ${String(item?.name || '')} | ${identifier} | ${section} | ${String(item?.email || '')}`);
  }
  for (const item of courses) {
    pushRow(
      `Course | ${String(item?.course_code || '')} | ${String(item?.course_title || '')} | Faculty: ${String(item?.faculty_name || item?.faculty_id || '')}`,
    );
  }
}

function renderAdminGradeHistory(payload) {
  if (!els.adminGradeHistoryWrap) {
    return;
  }
  els.adminGradeHistoryWrap.innerHTML = '';
  const grades = Array.isArray(payload?.grades) ? payload.grades : [];
  if (!grades.length) {
    els.adminGradeHistoryWrap.innerHTML = '<div class="list-item">No grade records found for this student.</div>';
    return;
  }
  for (const item of grades) {
    const marks = item?.marks_percent === null || item?.marks_percent === undefined
      ? '--'
      : `${Number(item.marks_percent).toFixed(2)}%`;
    const remark = String(item?.remark || '').trim();
    const updatedAt = item?.updated_at ? new Date(item.updated_at).toLocaleString() : '--';
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = `${String(item?.course_code || '')} | ${String(item?.grade_letter || '')} | ${marks} | ${updatedAt}${remark ? ` | ${remark}` : ''}`;
    els.adminGradeHistoryWrap.appendChild(row);
  }
}

function formatCopilotAuditLabel(rawValue) {
  const text = String(rawValue || '').trim().replaceAll('_', ' ');
  if (!text) {
    return '--';
  }
  return text.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatCopilotAuditTimestamp(rawValue) {
  const parsed = new Date(rawValue);
  if (Number.isNaN(parsed.getTime())) {
    return '--';
  }
  return parsed.toLocaleString([], {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function renderCopilotAuditTimeline(rows = []) {
  if (!els.adminCopilotAuditWrap) {
    return;
  }
  els.adminCopilotAuditWrap.innerHTML = '';
  if (!Array.isArray(rows) || !rows.length) {
    els.adminCopilotAuditWrap.innerHTML = `
      <div class="empty-state-row">
        <strong>No copilot runs match the current filters.</strong>
        <span>Try a broader search, or clear one of the governance filters above.</span>
      </div>
    `;
    return;
  }

  for (const row of rows) {
    const outcome = String(row?.outcome || '').trim().toLowerCase();
    const explanation = Array.isArray(row?.explanation) ? row.explanation : [];
    const evidence = Array.isArray(row?.evidence) ? row.evidence : [];
    const actions = Array.isArray(row?.actions) ? row.actions : [];
    const nextSteps = Array.isArray(row?.result?.next_steps) ? row.result.next_steps : [];
    const scopeParts = [];
    if (row?.scope) {
      scopeParts.push(`Scope: ${String(row.scope)}`);
    }
    if (row?.target_section) {
      scopeParts.push(`Section: ${String(row.target_section)}`);
    }
    if (row?.target_student_id) {
      scopeParts.push(`Student ID: ${Number(row.target_student_id)}`);
    }
    if (row?.target_course_id) {
      scopeParts.push(`Course ID: ${Number(row.target_course_id)}`);
    }
    const actorLabel = String(row?.actor_email || '').trim() || `User ${Number(row?.actor_user_id || 0)}`;
    const details = document.createElement('details');
    details.className = `admin-copilot-entry admin-copilot-entry--${escapeHtml(outcome || 'blocked')}`;
    details.innerHTML = `
      <summary>
        <div class="admin-copilot-entry-head">
          <div class="admin-copilot-entry-title">${escapeHtml(String(row?.query_text || row?.result?.title || 'Campus Copilot run'))}</div>
          <div class="admin-copilot-entry-badges">
            <span class="admin-copilot-badge">#${Number(row?.id || 0)}</span>
            <span class="admin-copilot-badge">${escapeHtml(formatCopilotAuditLabel(row?.intent))}</span>
            <span class="admin-copilot-badge" data-tone="${escapeHtml(outcome || 'blocked')}">${escapeHtml(formatCopilotAuditLabel(outcome))}</span>
          </div>
        </div>
        <div class="admin-copilot-entry-meta">
          <span>${escapeHtml(actorLabel)} (${escapeHtml(formatCopilotAuditLabel(row?.actor_role || '--'))})</span>
          <span>${escapeHtml(formatCopilotAuditTimestamp(row?.created_at))}</span>
        </div>
        ${scopeParts.length ? `<div class="admin-copilot-entry-scope">${escapeHtml(scopeParts.join(' | '))}</div>` : ''}
      </summary>
      <div class="admin-copilot-entry-body">
        <section class="admin-copilot-entry-section">
          <strong>Explanation</strong>
          ${explanation.length
            ? `<ul class="admin-copilot-entry-list">${explanation.map((item) => `<li>${escapeHtml(String(item))}</li>`).join('')}</ul>`
            : '<p class="admin-copilot-entry-empty">No explanation stored.</p>'}
        </section>
        <section class="admin-copilot-entry-section">
          <strong>Evidence</strong>
          ${evidence.length
            ? `<ul class="admin-copilot-entry-list">${evidence.map((item) => `<li>[${escapeHtml(String(item?.status || 'info').toUpperCase())}] ${escapeHtml(String(item?.label || 'Item'))}: ${escapeHtml(String(item?.value || ''))}</li>`).join('')}</ul>`
            : '<p class="admin-copilot-entry-empty">No evidence items stored.</p>'}
        </section>
        <section class="admin-copilot-entry-section">
          <strong>Actions</strong>
          ${actions.length
            ? `<ul class="admin-copilot-entry-list">${actions.map((item) => `<li>[${escapeHtml(String(item?.status || 'preview').toUpperCase())}] ${escapeHtml(formatCopilotAuditLabel(item?.action || 'action'))}${item?.detail ? `: ${escapeHtml(String(item.detail))}` : ''}</li>`).join('')}</ul>`
            : '<p class="admin-copilot-entry-empty">No action log stored.</p>'}
        </section>
        ${nextSteps.length
          ? `<section class="admin-copilot-entry-section"><strong>Next Steps</strong><ul class="admin-copilot-entry-list">${nextSteps.map((item) => `<li>${escapeHtml(String(item))}</li>`).join('')}</ul></section>`
          : ''}
      </div>
    `;
    els.adminCopilotAuditWrap.appendChild(details);
  }
}

function buildCopilotAuditQueryString() {
  const params = new URLSearchParams();
  const limit = Number(els.adminCopilotAuditLimit?.value || 50);
  params.set('limit', String(Number.isFinite(limit) && limit > 0 ? limit : 50));

  const search = String(els.adminCopilotAuditSearch?.value || '').trim();
  const intent = String(els.adminCopilotAuditIntent?.value || '').trim();
  const outcome = String(els.adminCopilotAuditOutcome?.value || '').trim();
  const actorRole = String(els.adminCopilotAuditRole?.value || '').trim();
  const actorUserId = Number(els.adminCopilotAuditActorUserId?.value || 0) || 0;

  if (search) {
    params.set('q', search);
  }
  if (intent && intent !== 'all') {
    params.set('intent', intent);
  }
  if (outcome && outcome !== 'all') {
    params.set('outcome', outcome);
  }
  if (actorRole && actorRole !== 'all') {
    params.set('actor_role', actorRole);
  }
  if (actorUserId > 0) {
    params.set('actor_user_id', String(actorUserId));
  }
  return params.toString();
}

async function refreshCopilotAuditTimeline({ silent = false, force = false } = {}) {
  if (!authState.user || authState.user.role !== 'admin') {
    return;
  }
  if (!els.adminCopilotAuditWrap) {
    return;
  }
  const ageMs = Date.now() - Number(state.admin.copilotAuditLoadedAtMs || 0);
  if (state.admin.copilotAuditBusy) {
    state.admin.copilotAuditQueued = true;
    return;
  }
  if (!force && silent && ageMs < 30000 && els.adminCopilotAuditWrap.childElementCount) {
    return;
  }
  state.admin.copilotAuditBusy = true;
  if (!silent) {
    setAdminCopilotAuditStatus('Loading copilot action timeline...', false, 'loading');
  }
  try {
    const rows = await api(`/copilot/audit?${buildCopilotAuditQueryString()}`);
    renderCopilotAuditTimeline(rows);
    state.admin.copilotAuditLoadedAtMs = Date.now();
    setAdminCopilotAuditStatus(
      `Loaded ${Array.isArray(rows) ? rows.length : 0} copilot run${Array.isArray(rows) && rows.length === 1 ? '' : 's'}.`,
      false,
      'success',
    );
  } catch (error) {
    setAdminCopilotAuditStatus(error?.message || 'Failed to load copilot audit timeline.', true, 'error');
  } finally {
    state.admin.copilotAuditBusy = false;
    if (state.admin.copilotAuditQueued) {
      state.admin.copilotAuditQueued = false;
      void refreshCopilotAuditTimeline({ silent: true, force: true });
    }
  }
}

function resetCopilotAuditFilters() {
  if (els.adminCopilotAuditSearch) {
    els.adminCopilotAuditSearch.value = '';
  }
  if (els.adminCopilotAuditIntent) {
    els.adminCopilotAuditIntent.value = 'all';
  }
  if (els.adminCopilotAuditOutcome) {
    els.adminCopilotAuditOutcome.value = 'all';
  }
  if (els.adminCopilotAuditRole) {
    els.adminCopilotAuditRole.value = 'all';
  }
  if (els.adminCopilotAuditActorUserId) {
    els.adminCopilotAuditActorUserId.value = '';
  }
  if (els.adminCopilotAuditLimit) {
    els.adminCopilotAuditLimit.value = '50';
  }
}

async function fetchAdminStudentGradeHistory(registrationNumber, { silent = false } = {}) {
  if (!authState.user || authState.user.role !== 'admin') {
    throw new Error('Only admin can fetch grade history.');
  }
  const normalized = normalizedRegistrationInput(registrationNumber || '');
  if (!normalized) {
    throw new Error('Enter student registration number.');
  }
  const payload = await api(`/admin/grades/students/${encodeURIComponent(normalized)}`);
  renderAdminGradeHistory(payload);
  if (!silent) {
    setAdminGradeStatus(`Loaded grade history for ${normalized}.`, false);
  }
}

async function adminSearchStudentByRegistration() {
  if (!authState.user || authState.user.role !== 'admin') {
    throw new Error('Only admin can search students from this panel.');
  }
  const registrationNumber = normalizedRegistrationInput(els.adminSearchStudentRegistration?.value || '');
  if (!registrationNumber) {
    throw new Error('Enter student registration number.');
  }
  if (els.adminSearchStudentRegistration) {
    els.adminSearchStudentRegistration.value = registrationNumber;
  }
  const payload = await api(
    `/admin/search/students/by-registration?registration_number=${encodeURIComponent(registrationNumber)}`
  );
  renderAdminSearchResultsFromGlobal({ students: [payload], faculty: [], courses: [] });
  if (els.adminGradeStudentRegistration) {
    els.adminGradeStudentRegistration.value = registrationNumber;
  }
  setAdminSearchStatus(`Student found for registration ${registrationNumber}.`, false);
  syncVisibleVerlynQuickActions();
  await fetchAdminStudentGradeHistory(registrationNumber, { silent: true });
}

async function adminSearchFacultyByIdentifier() {
  if (!authState.user || authState.user.role !== 'admin') {
    throw new Error('Only admin can search faculty from this panel.');
  }
  const facultyIdentifier = normalizedRegistrationInput(els.adminSearchFacultyIdentifier?.value || '');
  if (!facultyIdentifier) {
    throw new Error('Enter faculty identifier.');
  }
  if (els.adminSearchFacultyIdentifier) {
    els.adminSearchFacultyIdentifier.value = facultyIdentifier;
  }
  const payload = await api(
    `/admin/search/faculty/by-identifier?faculty_identifier=${encodeURIComponent(facultyIdentifier)}`
  );
  renderAdminSearchResultsFromGlobal({ students: [], faculty: [payload], courses: [] });
  setAdminSearchStatus(`Faculty found for identifier ${facultyIdentifier}.`, false);
}

async function adminSearchEverything() {
  if (!authState.user || authState.user.role !== 'admin') {
    throw new Error('Only admin can run global search from this panel.');
  }
  const query = String(els.adminGlobalSearchQuery?.value || '').trim();
  if (!query) {
    throw new Error('Enter a global search query.');
  }
  const payload = await api(`/admin/search/everything?query=${encodeURIComponent(query)}&limit=25`);
  renderAdminSearchResultsFromGlobal(payload);
  setAdminSearchStatus(`Global search complete. Matches: ${Number(payload?.total_matches || 0)}.`, false);
}

async function adminUpsertStudentGrade() {
  if (!authState.user || authState.user.role !== 'admin') {
    throw new Error('Only admin can save grades from this panel.');
  }
  const registrationNumber = normalizedRegistrationInput(els.adminGradeStudentRegistration?.value || '');
  const courseCode = normalizedRegistrationInput(els.adminGradeCourseCode?.value || '');
  const gradeLetter = String(els.adminGradeLetter?.value || '').trim().toUpperCase();
  const marksRaw = String(els.adminGradeMarks?.value || '').trim();
  const remark = String(els.adminGradeRemark?.value || '').trim();

  if (!registrationNumber || !courseCode || !gradeLetter) {
    throw new Error('Registration number, course code, and grade are required.');
  }

  const payload = {
    registration_number: registrationNumber,
    course_code: courseCode,
    grade_letter: gradeLetter,
    marks_percent: marksRaw ? Number(marksRaw) : null,
    remark: remark || null,
  };
  const saved = await api('/admin/grades/upsert', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  setAdminGradeStatus(
    `Grade saved: ${String(saved?.registration_number || registrationNumber)} | ${String(saved?.course_code || courseCode)} -> ${String(saved?.grade_letter || gradeLetter)}.`,
    false,
  );
  await fetchAdminStudentGradeHistory(registrationNumber, { silent: true });
}

async function createAdminAttendanceSchedule() {
  if (!authState.user || authState.user.role !== 'admin') {
    throw new Error('Only admin can create schedules from this panel.');
  }

  const courseId = Number(els.adminCreateScheduleCourseId?.value || 0);
  const facultyId = Number(els.adminCreateScheduleFacultyId?.value || 0);
  const weekday = Number(els.adminCreateScheduleWeekday?.value || 0);
  const startTime = String(els.adminCreateScheduleStartTime?.value || '').trim();
  const endTime = String(els.adminCreateScheduleEndTime?.value || '').trim();
  const classroomLabel = String(els.adminCreateScheduleRoomLabel?.value || '').trim();

  if (!Number.isFinite(courseId) || courseId <= 0) {
    throw new Error('Enter a valid Course ID.');
  }
  if (!Number.isFinite(facultyId) || facultyId <= 0) {
    throw new Error('Enter a valid Faculty ID.');
  }
  if (!Number.isFinite(weekday) || weekday < 0 || weekday > 6) {
    throw new Error('Select a valid weekday.');
  }
  if (!startTime || !endTime) {
    throw new Error('Select both start and end time.');
  }

  const payload = {
    course_id: courseId,
    faculty_id: facultyId,
    weekday,
    start_time: startTime,
    end_time: endTime,
    classroom_label: classroomLabel || null,
    is_active: true,
  };

  const created = await api('/attendance/schedules', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

  setAdminCreateScheduleStatus(
    `Schedule created (ID ${Number(created?.id || 0)}) for course ${courseId} on ${DAY_LABELS[weekday]}.`,
    false,
  );
  log(`Admin created schedule ${Number(created?.id || 0)} for course ${courseId}.`);

  if (els.adminCreateScheduleRoomLabel) {
    els.adminCreateScheduleRoomLabel.value = '';
  }

  await loadFacultySchedules();
}

async function saveAdminTimetableOverride() {
  if (!authState.user || authState.user.role !== 'admin') {
    throw new Error('Only admin can update timetable overrides from this panel.');
  }

  const scope = String(els.adminTimetableOverrideScope?.value || 'student').trim().toLowerCase();
  const studentId = Number(els.adminTimetableOverrideStudentId?.value || 0);
  const section = String(els.adminTimetableOverrideSection?.value || '')
    .trim()
    .toUpperCase()
    .replace(/\s+/g, '');
  const sourceWeekday = Number(els.adminTimetableOverrideSourceWeekday?.value || 0);
  const sourceStartTime = String(els.adminTimetableOverrideSourceStartTime?.value || '').trim();
  const courseId = Number(els.adminTimetableOverrideCourseId?.value || 0);
  const facultyId = Number(els.adminTimetableOverrideFacultyId?.value || 0);
  const weekday = Number(els.adminTimetableOverrideWeekday?.value || 0);
  const startTime = String(els.adminTimetableOverrideStartTime?.value || '').trim();
  const endTime = String(els.adminTimetableOverrideEndTime?.value || '').trim();
  const classroomLabel = String(els.adminTimetableOverrideRoomLabel?.value || '').trim();

  if (scope !== 'student' && scope !== 'section') {
    throw new Error('Select a valid timetable scope.');
  }
  if (scope === 'student' && (!Number.isFinite(studentId) || studentId <= 0)) {
    throw new Error('Enter a valid Student ID for single-student timetable updates.');
  }
  if (scope === 'section' && !section) {
    throw new Error('Enter target section for section-wide timetable updates.');
  }
  if (!sourceStartTime) {
    throw new Error('Select the existing slot start time to replace.');
  }
  if (!Number.isFinite(courseId) || courseId <= 0) {
    throw new Error('Enter a valid Course ID.');
  }
  if (!Number.isFinite(facultyId) || facultyId <= 0) {
    throw new Error('Enter a valid Faculty ID.');
  }
  if (!startTime || !endTime) {
    throw new Error('Select the new class start and end time.');
  }

  const payload = {
    scope_type: scope,
    student_id: scope === 'student' ? studentId : null,
    section: scope === 'section' ? section : null,
    source_weekday: sourceWeekday,
    source_start_time: sourceStartTime,
    course_id: courseId,
    faculty_id: facultyId,
    weekday,
    start_time: startTime,
    end_time: endTime,
    classroom_label: classroomLabel || null,
    is_active: true,
  };

  const saved = await api('/attendance/timetable-overrides', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  const scopeLabel = scope === 'student'
    ? `student ${studentId}`
    : `section ${String(saved?.section || section)}`;
  setAdminTimetableOverrideStatus(
    `Timetable override saved for ${scopeLabel}. Replaced ${DAY_LABELS[sourceWeekday]} ${sourceStartTime} with ${DAY_LABELS[weekday]} ${startTime}-${endTime}.`,
    false,
  );
  log(`Admin updated timetable for ${scopeLabel}. Override ${Number(saved?.id || 0)}.`);
}

async function approveAdminStudentSectionUpdate() {
  if (!authState.user || authState.user.role !== 'admin') {
    throw new Error('Only admin can approve student section updates from this panel.');
  }

  const studentId = Number(els.adminUpdateStudentId?.value || 0);
  const section = String(els.adminUpdateStudentSection?.value || '')
    .trim()
    .toUpperCase()
    .replace(/\s+/g, '');

  if (!Number.isFinite(studentId) || studentId <= 0) {
    throw new Error('Enter a valid Student ID.');
  }
  if (!section) {
    throw new Error('Enter target section.');
  }

  const saved = await api(`/attendance/faculty/students/${studentId}/section`, {
    method: 'PUT',
    body: JSON.stringify({ section }),
  });

  setAdminSectionUpdateStatus(
    `Section updated for student ${studentId}. New section: ${String(saved?.section || section)}.`,
    false,
  );
  log(`Admin approved section update for student ${studentId} -> ${String(saved?.section || section)}.`);
}

function renderRemedialCourseOptions() {
  if (!els.remedialCourseSelect) {
    return;
  }
  const previous = String(els.remedialCourseSelect.value || '').trim();
  const role = authState.user?.role;
  const courses = role === 'faculty'
    ? (Array.isArray(state.remedial.eligibleCourses) ? state.remedial.eligibleCourses : [])
    : Object.values(state.coursesById || {});

  els.remedialCourseSelect.innerHTML = '';
  if (!courses.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = role === 'faculty'
      ? 'No assigned subjects. Enter manual course code + name.'
      : 'No eligible courses';
    els.remedialCourseSelect.appendChild(option);
    els.remedialCourseSelect.disabled = true;
    return;
  }

  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = 'Select assigned course (optional)';
  els.remedialCourseSelect.appendChild(placeholder);

  for (const course of courses) {
    const option = document.createElement('option');
    option.value = String(course.id);
    option.textContent = `${course.code} - ${course.title}`;
    els.remedialCourseSelect.appendChild(option);
  }
  els.remedialCourseSelect.disabled = false;
  if (previous && courses.some((course) => String(course.id) === previous)) {
    els.remedialCourseSelect.value = previous;
    return;
  }
  els.remedialCourseSelect.value = '';
}

async function loadRemedialEligibleCourses() {
  if (!authState.user || authState.user.role !== 'faculty') {
    state.remedial.eligibleCourses = [];
    return;
  }
  const rows = await api('/makeup/faculty/eligible-courses');
  state.remedial.eligibleCourses = Array.isArray(rows) ? rows : [];
}

function normalizeRemedialSections(rawValue) {
  const tokens = String(rawValue || '')
    .split(',')
    .map((token) => token.trim().toUpperCase().replace(/\s+/g, ''))
    .filter(Boolean);
  return [...new Set(tokens)];
}

function normalizeRemedialCourseCode(rawValue) {
  return String(rawValue || '')
    .trim()
    .toUpperCase()
    .replace(/\s+/g, '')
    .slice(0, 20);
}

function normalizeRemedialCourseTitle(rawValue) {
  return String(rawValue || '')
    .trim()
    .replace(/\s+/g, ' ')
    .slice(0, 150);
}

function syncRemedialManualCourseFromSelect() {
  if (!els.remedialCourseSelect || !els.remedialCourseCodeInput || !els.remedialCourseTitleInput) {
    return;
  }
  const selectedCourseId = Number(els.remedialCourseSelect.value || 0);
  if (!selectedCourseId) {
    return;
  }
  const role = authState.user?.role;
  const sourceCourses = role === 'faculty'
    ? (Array.isArray(state.remedial.eligibleCourses) ? state.remedial.eligibleCourses : [])
    : Object.values(state.coursesById || {});
  const selected = sourceCourses.find((course) => Number(course.id) === selectedCourseId);
  if (!selected) {
    return;
  }
  if (!String(els.remedialCourseCodeInput.value || '').trim()) {
    els.remedialCourseCodeInput.value = normalizeRemedialCourseCode(selected.code || '');
  }
  if (!String(els.remedialCourseTitleInput.value || '').trim()) {
    els.remedialCourseTitleInput.value = normalizeRemedialCourseTitle(selected.title || '');
  }
}

function remedialModeLabel(entry) {
  const mode = String(entry?.class_mode || 'offline').toLowerCase();
  if (mode === 'online') {
    return `Online • ${REMEDIAL_DEFAULT_ONLINE_LINK}`;
  }
  const room = String(entry?.room_number || '').trim() || 'Room TBA';
  return `Offline • Room ${room}`;
}

function normalizedRemedialOnlineLink(rawLink) {
  const link = String(rawLink || '').trim();
  if (!link) {
    return REMEDIAL_DEFAULT_ONLINE_LINK;
  }
  if (/^https?:\/\/myclass\.lpu\.in\/?/i.test(link)) {
    return link.endsWith('/') ? link : `${link}/`;
  }
  return REMEDIAL_DEFAULT_ONLINE_LINK;
}

function remedialCourseDisplay(entry) {
  const code = String(entry?.course_code || '').trim();
  const title = String(entry?.course_title || '').trim();
  if (code && title) {
    return `${code} - ${title}`;
  }
  if (code) {
    return code;
  }
  const courseId = Number(entry?.course_id || 0);
  if (courseId > 0) {
    return getCourseLabel(courseId);
  }
  return 'Remedial Class';
}

function remedialSectionsLabel(value) {
  if (Array.isArray(value) && value.length) {
    return value
      .map((section) => String(section || '').trim().toUpperCase())
      .filter(Boolean)
      .join(', ');
  }
  const fallback = String(value || '').trim().toUpperCase();
  return fallback || '--';
}

function parseApiDateTime(value) {
  if (!value) {
    return null;
  }
  const parsed = new Date(String(value));
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed;
}

function isRemedialRejectWindowOpen(entry) {
  if (!entry || typeof entry !== 'object') {
    return false;
  }
  if (typeof entry.can_reject === 'boolean') {
    return entry.can_reject;
  }
  const scheduledAt = parseApiDateTime(entry.scheduled_at);
  if (!scheduledAt) {
    return false;
  }
  return (Date.now() - scheduledAt.getTime()) <= REMEDIAL_REJECT_WINDOW_MS;
}

function parseTimeStringToParts(rawValue) {
  const match = String(rawValue || '').trim().match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
  if (!match) {
    return null;
  }
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  const second = Number(match[3] || 0);
  if (!Number.isInteger(hour) || !Number.isInteger(minute) || !Number.isInteger(second)) {
    return null;
  }
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59 || second < 0 || second > 59) {
    return null;
  }
  return { hour, minute, second };
}

function remedialClassWindow(entry) {
  const classDate = String(entry?.class_date || '').trim();
  if (!classDate) {
    return null;
  }
  const parts = classDate.split('-').map((value) => Number(value));
  if (parts.length !== 3 || parts.some((value) => Number.isNaN(value))) {
    return null;
  }
  const [year, month, day] = parts;
  const startParts = parseTimeStringToParts(entry?.start_time);
  const endParts = parseTimeStringToParts(entry?.end_time);
  if (!startParts || !endParts) {
    return null;
  }
  const startAt = new Date(year, month - 1, day, startParts.hour, startParts.minute, startParts.second, 0);
  const endAt = new Date(year, month - 1, day, endParts.hour, endParts.minute, endParts.second, 0);
  if (Number.isNaN(startAt.getTime()) || Number.isNaN(endAt.getTime())) {
    return null;
  }
  if (endAt.getTime() <= startAt.getTime()) {
    endAt.setDate(endAt.getDate() + 1);
  }
  return { startAt, endAt };
}

function isRemedialClassPrevious(entry, nowDate = new Date()) {
  if (typeof entry?.is_active === 'boolean') {
    return !entry.is_active;
  }
  const window = remedialClassWindow(entry);
  if (!window) {
    return false;
  }
  return nowDate.getTime() > window.endAt.getTime();
}

function remedialClassSortTimestamp(entry, kind = 'start') {
  const window = remedialClassWindow(entry);
  if (!window) {
    return kind === 'end' ? 0 : Number.MAX_SAFE_INTEGER;
  }
  return kind === 'end' ? window.endAt.getTime() : window.startAt.getTime();
}

function applyRemedialModeVisibility() {
  const mode = String(els.remedialModeSelect?.value || 'offline').toLowerCase();
  const isOnline = mode === 'online';
  setHidden(els.remedialRoomWrap, isOnline);
  setHidden(els.remedialOnlineWrap, !isOnline);
  if (els.remedialOnlineLinkInput) {
    els.remedialOnlineLinkInput.readOnly = false;
    if (isOnline && !String(els.remedialOnlineLinkInput.value || '').trim()) {
      els.remedialOnlineLinkInput.value = REMEDIAL_DEFAULT_ONLINE_LINK;
    }
  }
}

function renderRemedialDemoToggle() {
  if (!els.remedialDemoInstantBtn) {
    return;
  }
  const enabled = Boolean(state.remedial.demoBypassLeadTime);
  els.remedialDemoInstantBtn.dataset.active = enabled ? 'true' : 'false';
  els.remedialDemoInstantBtn.setAttribute('aria-pressed', enabled ? 'true' : 'false');
  els.remedialDemoInstantBtn.textContent = enabled
    ? 'Demo: Instant Scheduling ON'
    : 'Demo: Instant Scheduling OFF';
}

function renderRemedialClassesList() {
  if (!els.remedialClassesList) {
    return;
  }
  els.remedialClassesList.innerHTML = '';
  if (els.remedialPreviousClassesList) {
    els.remedialPreviousClassesList.innerHTML = '';
  }
  if (!state.remedial.classes.length) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'No active/upcoming remedial classes.';
    els.remedialClassesList.appendChild(row);
    if (els.remedialPreviousClassesList) {
      const previousRow = document.createElement('div');
      previousRow.className = 'list-item';
      previousRow.textContent = 'Completed classes will appear here automatically.';
      els.remedialPreviousClassesList.appendChild(previousRow);
    }
    return;
  }
  const nowDate = new Date();
  const scheduledClasses = [];
  const previousClasses = [];
  for (const entry of state.remedial.classes) {
    if (isRemedialClassPrevious(entry, nowDate)) {
      previousClasses.push(entry);
    } else {
      scheduledClasses.push(entry);
    }
  }
  scheduledClasses.sort((a, b) => remedialClassSortTimestamp(a, 'start') - remedialClassSortTimestamp(b, 'start'));
  previousClasses.sort((a, b) => remedialClassSortTimestamp(b, 'end') - remedialClassSortTimestamp(a, 'end'));

  const renderRow = (entry, { previous = false } = {}) => {
    const row = document.createElement('div');
    const isActive = Boolean(entry.is_active ?? true);
    const canRejectByRole = authState.user?.role === 'faculty';
    const rejectWindowOpen = isRemedialRejectWindowOpen(entry);
    const rejectEnabled = isActive && canRejectByRole && rejectWindowOpen;
    const rejectButtonLabel = !isActive
      ? 'Rejected'
      : (rejectWindowOpen ? 'Reject Class' : 'Reject Window Closed');
    const rejectButtonTitle = rejectWindowOpen
      ? 'Reject this remedial class'
      : 'Reject available only within 30 minutes of scheduling';
    row.className = `remedial-card remedial-class-card ${isActive ? 'is-active' : 'is-inactive'}`;
    const sections = remedialSectionsLabel(entry.sections);
    const dateText = entry.class_date
      ? parseISODateLocal(entry.class_date).toLocaleDateString('en-GB')
      : '--';
    const code = String(entry.remedial_code || '').trim().toUpperCase() || '--';
    const topic = String(entry.topic || '').trim() || 'Remedial Session';
    const classMode = remedialModeLabel(entry);
    const statusLabel = previous
      ? (isActive ? 'Completed' : 'Rejected')
      : (isActive ? 'Active' : 'Rejected');
    const statusClass = previous
      ? (isActive ? 'remedial-chip-complete' : 'remedial-chip-muted')
      : (isActive ? 'remedial-chip-live' : 'remedial-chip-muted');
    const actionsHtml = previous
      ? ''
      : `
          <div class="remedial-card-actions">
            <button type="button" class="btn btn-primary" data-remedial-send-code="${entry.id}" ${isActive ? '' : 'disabled'}>Send Code to Section(s)</button>
            ${canRejectByRole
    ? `<button type="button" class="btn btn-ghost" data-remedial-cancel="${entry.id}" title="${escapeHtml(rejectButtonTitle)}" ${rejectEnabled ? '' : 'disabled'}>${escapeHtml(rejectButtonLabel)}</button>`
    : ''}
          </div>
        `;
    row.innerHTML = `
      <div class="remedial-card-grid">
        <div class="remedial-card-primary">
          <p class="remedial-card-title">${escapeHtml(remedialCourseDisplay(entry))}</p>
          <p class="remedial-card-subtitle">${escapeHtml(topic)}</p>
          <div class="remedial-card-meta-row">
            <span class="remedial-meta-badge">${escapeHtml(dateText)}</span>
            <span class="remedial-meta-badge">${escapeHtml(formatTime(entry.start_time))}-${escapeHtml(formatTime(entry.end_time))}</span>
            <span class="remedial-meta-badge">${escapeHtml(classMode)}</span>
            <span class="remedial-meta-badge">Sections ${escapeHtml(sections)}</span>
          </div>
        </div>
        <div class="remedial-card-secondary">
          <div class="remedial-badge-group">
            <span class="remedial-chip remedial-chip-code">Code ${escapeHtml(code)}</span>
            <span class="remedial-chip ${statusClass}">${statusLabel}</span>
          </div>
          ${actionsHtml}
        </div>
      </div>
    `;
    return row;
  };

  if (!scheduledClasses.length) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'No active/upcoming remedial classes.';
    els.remedialClassesList.appendChild(row);
  } else {
    for (const entry of scheduledClasses) {
      els.remedialClassesList.appendChild(renderRow(entry, { previous: false }));
    }
  }

  if (els.remedialPreviousClassesList) {
    if (!previousClasses.length) {
      const row = document.createElement('div');
      row.className = 'list-item';
      row.textContent = 'Completed classes will appear here automatically.';
      els.remedialPreviousClassesList.appendChild(row);
    } else {
      for (const entry of previousClasses) {
        els.remedialPreviousClassesList.appendChild(renderRow(entry, { previous: true }));
      }
    }
  }
}

function renderRemedialClassSelect() {
  if (!els.remedialClassSelect) {
    return;
  }
  const previous = Number(state.remedial.selectedClassId || els.remedialClassSelect.value || 0);
  els.remedialClassSelect.innerHTML = '';
  if (!state.remedial.classes.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'No class available';
    els.remedialClassSelect.appendChild(option);
    els.remedialClassSelect.disabled = true;
    return;
  }

  for (const entry of state.remedial.classes) {
    const option = document.createElement('option');
    option.value = String(entry.id);
    option.textContent = `${parseISODateLocal(entry.class_date).toLocaleDateString('en-GB')} • ${remedialCourseDisplay(entry)} • ${entry.remedial_code}`;
    els.remedialClassSelect.appendChild(option);
  }
  els.remedialClassSelect.disabled = false;
  if (previous && state.remedial.classes.some((entry) => entry.id === previous)) {
    els.remedialClassSelect.value = String(previous);
  }
  state.remedial.selectedClassId = Number(els.remedialClassSelect.value || 0) || null;
}

function closeRemedialAttendanceModal() {
  state.remedial.selectedAttendanceModalSection = '';
  state.remedial.selectedAttendanceModalCourseKey = '';
  if (els.remedialAttendanceModal) {
    els.remedialAttendanceModal.classList.add('hidden');
  }
}

function selectedRemedialClassEntry() {
  const classId = Number(state.remedial.selectedClassId || 0);
  if (!classId) {
    return null;
  }
  return (state.remedial.classes || []).find((entry) => Number(entry.id) === classId) || null;
}

function openRemedialAttendanceSectionModal(sectionToken) {
  if (
    !els.remedialAttendanceModal
    || !els.remedialAttendanceModalTitle
    || !els.remedialAttendanceModalMeta
    || !els.remedialAttendanceModalList
  ) {
    return;
  }

  const safeSection = String(sectionToken || '').trim().toUpperCase();
  if (!safeSection) {
    return;
  }
  const sectionRows = Array.isArray(state.remedial.selectedClassAttendanceSections)
    ? state.remedial.selectedClassAttendanceSections
    : [];
  const summary = sectionRows.find((row) => String(row?.section || '').trim().toUpperCase() === safeSection);
  if (!summary) {
    return;
  }

  const classEntry = selectedRemedialClassEntry();
  const titleCourse = classEntry ? remedialCourseDisplay(classEntry) : 'Remedial Class';
  const totalStudents = Number(summary.total_students || 0);
  const markedStudents = Number(summary.marked_students || 0);
  const notMarkedStudents = Number(summary.not_marked_students || 0);
  const classDateText = classEntry?.class_date
    ? parseISODateLocal(classEntry.class_date).toLocaleDateString('en-GB')
    : '--';
  const classTimeText = classEntry
    ? `${formatTime(classEntry.start_time)}-${formatTime(classEntry.end_time)}`
    : '';

  els.remedialAttendanceModalTitle.textContent = `${safeSection} • ${titleCourse}`;
  els.remedialAttendanceModalMeta.textContent =
    `${classDateText} ${classTimeText} | Marked ${markedStudents}/${totalStudents} | Not Marked ${notMarkedStudents}`;

  const students = Array.isArray(summary.students) ? [...summary.students] : [];
  students.sort((left, right) => String(left.student_name || '').localeCompare(String(right.student_name || '')));
  const marked = students.filter((student) => Boolean(student.marked));
  const notMarked = students.filter((student) => !student.marked);

  const renderGroup = ({ title, rows, markedGroup }) => {
    if (!rows.length) {
      const emptyText = markedGroup
        ? 'No students have marked attendance yet.'
        : 'Everyone in this section has already marked attendance.';
      return `
        <section class="remedial-attendance-modal-group">
          <h4>${escapeHtml(title)}</h4>
          <div class="remedial-attendance-modal-empty">${escapeHtml(emptyText)}</div>
        </section>
      `;
    }

    const rowsMarkup = rows
      .map((student) => {
        const displayName = String(student.student_name || '').trim() || `Student #${student.student_id}`;
        const displayMarkedAt = student.marked_at ? new Date(student.marked_at).toLocaleString() : 'Not marked yet';
        const sourceText = student.source ? asTitleCase(String(student.source).replaceAll('-', ' ')) : 'Pending';
        const statusClass = markedGroup ? 'present' : 'absent';
        const detailLine = markedGroup
          ? `${displayMarkedAt} • ${sourceText}`
          : 'Attendance pending';
        const statusText = markedGroup ? 'Marked' : 'Not Marked';
        return `
          <article class="attendance-detail-row ${statusClass}">
            <div class="attendance-detail-main">
              <strong>${escapeHtml(displayName)}</strong>
              <small>${escapeHtml(detailLine)}</small>
            </div>
            <span class="attendance-detail-status ${statusClass}">${escapeHtml(statusText)}</span>
          </article>
        `;
      })
      .join('');

    return `
      <section class="remedial-attendance-modal-group">
        <h4>${escapeHtml(title)}</h4>
        <div class="remedial-attendance-modal-group-list">${rowsMarkup}</div>
      </section>
    `;
  };

  els.remedialAttendanceModalList.innerHTML = [
    renderGroup({ title: `Marked (${marked.length})`, rows: marked, markedGroup: true }),
    renderGroup({ title: `Not Marked (${notMarked.length})`, rows: notMarked, markedGroup: false }),
  ].join('');

  state.remedial.selectedAttendanceModalSection = safeSection;
  state.remedial.selectedAttendanceModalCourseKey = '';
  els.remedialAttendanceModal.classList.remove('hidden');
}

function renderRemedialAttendanceList() {
  if (!els.remedialAttendanceList) {
    return;
  }
  els.remedialAttendanceList.innerHTML = '';
  const sectionRows = Array.isArray(state.remedial.selectedClassAttendanceSections)
    ? state.remedial.selectedClassAttendanceSections
    : [];
  if (!sectionRows.length) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'No attendance data for selected class sections.';
    els.remedialAttendanceList.appendChild(row);
    return;
  }

  const totalStudents = Number(state.remedial.selectedClassAttendanceAllStudents.length || 0);
  const markedStudents = Number(state.remedial.selectedClassAttendance.length || 0);
  const summary = document.createElement('div');
  summary.className = 'remedial-attendance-overview';
  summary.innerHTML = `
    <span>Total Students: <strong>${totalStudents}</strong></span>
    <span>Marked: <strong>${markedStudents}</strong></span>
    <span>Not Marked: <strong>${Math.max(0, totalStudents - markedStudents)}</strong></span>
  `;
  els.remedialAttendanceList.appendChild(summary);

  for (const section of sectionRows) {
    const sectionName = String(section.section || '').trim().toUpperCase() || '--';
    const total = Number(section.total_students || 0);
    const marked = Number(section.marked_students || 0);
    const notMarked = Number(section.not_marked_students || 0);
    const percent = total > 0 ? Math.round((marked / total) * 100) : 0;

    const row = document.createElement('article');
    row.className = 'remedial-section-item';
    row.tabIndex = 0;
    row.setAttribute('role', 'button');
    row.dataset.remedialSection = sectionName;
    row.setAttribute('aria-label', `Open ${sectionName} attendance details`);
    row.innerHTML = `
      <div class="remedial-section-head">
        <p class="remedial-section-title">${escapeHtml(sectionName)}</p>
        <span class="remedial-section-pill">${escapeHtml(`${marked}/${total} marked`)}</span>
      </div>
      <div class="remedial-section-meta">
        <span>Not marked: <strong>${notMarked}</strong></span>
        <span>Coverage: <strong>${percent}%</strong></span>
      </div>
      <div class="remedial-section-progress" aria-hidden="true">
        <span style="width:${Math.max(0, Math.min(100, percent))}%"></span>
      </div>
    `;
    els.remedialAttendanceList.appendChild(row);
  }
}

function renderRemedialCodeDetails() {
  if (!els.remedialCodeDetails) {
    return;
  }
  els.remedialCodeDetails.innerHTML = '';
  const details = state.remedial.validatedClass;
  if (!details) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'Validate remedial code to view class details and attendance window.';
    els.remedialCodeDetails.appendChild(row);
    return;
  }

  const row = document.createElement('div');
  row.className = `list-item ${details.attendance_window_open ? 'good' : 'warn'}`;
  const windowMinutes = getAttendanceWindowMinutes(details);
  const isOnlineClass = String(details.class_mode || '').toLowerCase() === 'online';
  const onlineLink = normalizedRemedialOnlineLink(details.online_link);
  const modeText = isOnlineClass
    ? `Online • ${onlineLink}`
    : `Offline • Room ${details.room_number || 'TBA'}`;
  const detailsClassId = Number(details.class_id || 0);
  const showProceedBtn = isOnlineClass
    && detailsClassId > 0
    && Number(state.remedial.markedClassId || 0) === detailsClassId
    && Boolean(String(state.remedial.markedOnlineLink || '').trim());
  row.innerHTML = `
    <span>${escapeHtml(details.course_code || '--')} • ${escapeHtml(details.course_title || 'Remedial Class')}</span>
    <span>${escapeHtml(parseISODateLocal(details.class_date).toLocaleDateString('en-GB'))} • ${escapeHtml(formatTime(details.start_time))}-${escapeHtml(formatTime(details.end_time))} • ${escapeHtml(modeText)}</span>
    <span>${details.attendance_window_open ? `Attendance window is open (first ${windowMinutes} minutes).` : `Attendance window currently closed (opens only in first ${windowMinutes} minutes).`}</span>
    ${showProceedBtn ? `<div class="inline-controls"><button type="button" class="btn btn-primary" data-remedial-open-online-link="${escapeHtml(state.remedial.markedOnlineLink)}">Proceed to MyClass</button></div>` : ''}
  `;
  els.remedialCodeDetails.appendChild(row);
}

function renderRemedialMessagesList() {
  if (!els.remedialMessagesList) {
    return;
  }
  els.remedialMessagesList.innerHTML = '';
  const messagesRaw = Array.isArray(state.remedial.messages) ? state.remedial.messages : [];
  const messages = messagesRaw.filter((message) => {
    if (!message?.class_date || !message?.start_time || !message?.end_time) {
      return true;
    }
    return !isRemedialClassPrevious(message);
  });
  if (!messages.length) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'No active remedial classes right now.';
    els.remedialMessagesList.appendChild(row);
    return;
  }

  for (const message of messages) {
    const row = document.createElement('div');
    row.className = 'remedial-card remedial-message-card';
    const dateText = message.class_date
      ? parseISODateLocal(message.class_date).toLocaleDateString('en-GB')
      : '--';
    const code = String(message.remedial_code || '').trim().toUpperCase();
    const hasCode = Boolean(code);
    const windowMinutes = getAttendanceWindowMinutes(message);
    const attendanceNote = `Attendance open for first ${windowMinutes} minutes.`;
    row.innerHTML = `
      <div class="remedial-card-grid">
        <div class="remedial-card-primary">
          <p class="remedial-card-title">${escapeHtml(remedialCourseDisplay(message))}</p>
          <div class="remedial-card-meta-row">
            <span class="remedial-meta-badge">${escapeHtml(dateText)}</span>
            <span class="remedial-meta-badge">${escapeHtml(formatTime(message.start_time))}-${escapeHtml(formatTime(message.end_time))}</span>
            <span class="remedial-meta-badge">${escapeHtml(remedialModeLabel(message))}</span>
          </div>
          <p class="remedial-card-message">${escapeHtml(attendanceNote)}</p>
        </div>
        <div class="remedial-card-secondary">
          <div class="remedial-badge-group">
            <span class="remedial-chip remedial-chip-code">Code ${escapeHtml(code || '--')}</span>
          </div>
          <div class="remedial-card-actions">
            <button type="button" class="btn btn-primary" data-remedial-use-code="${escapeHtml(code)}" ${hasCode ? '' : 'disabled'}>Use Code ${escapeHtml(code || '--')}</button>
          </div>
        </div>
      </div>
    `;
    els.remedialMessagesList.appendChild(row);
  }
}

function renderStudentMessagesCenter() {
  if (!els.studentMessagesList) {
    return;
  }
  els.studentMessagesList.innerHTML = '';
  if (!authState.user || authState.user.role !== 'student') {
    return;
  }

  const messagesRaw = Array.isArray(state.studentMessages) ? state.studentMessages : [];
  const messages = messagesRaw
    .filter((message) => {
      const hasCode = Boolean(String(message?.remedial_code || '').trim());
      if (!hasCode || !message?.class_date || !message?.start_time || !message?.end_time) {
        return true;
      }
      return !isRemedialClassPrevious(message);
    })
    .slice(0, 5);
  if (!messages.length) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'No new faculty messages for your section.';
    els.studentMessagesList.appendChild(row);
    return;
  }

  for (const message of messages) {
    const row = document.createElement('div');
    row.className = 'list-item student-message-item';
    const dateText = message.class_date
      ? parseISODateLocal(message.class_date).toLocaleDateString('en-GB')
      : '--';
    const facultyName = String(message.faculty_name || '').trim() || 'Your faculty';
    const summaryDate = message.class_date === todayISO() ? 'today' : `on ${dateText}`;
    const messageType = String(message.message_type || 'Announcement').trim();
    const hasCode = Boolean(String(message.remedial_code || '').trim());
    const summary = `${facultyName} shared an update ${summaryDate}.`;
    const bodyLine = hasCode
      ? `${remedialCourseDisplay(message)} • ${formatTime(message.start_time)}-${formatTime(message.end_time)} • ${remedialModeLabel(message)}`
      : String(message.message || '').trim();
    row.innerHTML = `
      <span>${escapeHtml(summary)}</span>
      <span>${escapeHtml(bodyLine || '')}</span>
      <div class="inline-controls">
        <span class="status-pill neutral">${escapeHtml(messageType)}</span>
        ${hasCode ? '<button type="button" class="btn btn-ghost" data-student-open-remedial="1">View Details</button>' : ''}
      </div>
    `;
    els.studentMessagesList.appendChild(row);
  }
}

function normalizeRemedialAttendanceStatus(row) {
  const statusRaw = String(row?.status || '').trim().toLowerCase();
  if (statusRaw === 'present' || statusRaw === 'absent') {
    return statusRaw;
  }
  return row?.marked_at ? 'present' : 'absent';
}

function remedialAttendanceSortMs(row) {
  const markedAtMs = Date.parse(row?.marked_at || '');
  if (Number.isFinite(markedAtMs) && markedAtMs > 0) {
    return markedAtMs;
  }
  const classDate = String(row?.class_date || '').trim();
  const startTimeRaw = String(row?.start_time || '').trim();
  if (!classDate || !startTimeRaw) {
    return 0;
  }
  const [hhRaw, mmRaw, ssRaw] = startTimeRaw.split(':');
  const hh = String(Number(hhRaw || 0)).padStart(2, '0');
  const mm = String(Number(mmRaw || 0)).padStart(2, '0');
  const ss = String(Number(ssRaw || 0)).padStart(2, '0');
  const classStartMs = Date.parse(`${classDate}T${hh}:${mm}:${ss}`);
  return Number.isFinite(classStartMs) ? classStartMs : 0;
}

function indexRemedialAttendanceByCourse(rows = []) {
  const grouped = {};
  for (const rawEntry of rows) {
    const status = normalizeRemedialAttendanceStatus(rawEntry);
    if (status !== 'present' && status !== 'absent') {
      continue;
    }
    const entry = { ...rawEntry, status };
    const courseKey = attendanceCourseKey(entry.course_code, entry.course_title);
    if (!grouped[courseKey]) {
      grouped[courseKey] = {
        course_code: String(entry.course_code || '').trim() || '--',
        course_title: String(entry.course_title || '').trim() || 'Untitled Course',
        rows: [],
      };
    }
    grouped[courseKey].rows.push(entry);
  }
  for (const key of Object.keys(grouped)) {
    grouped[key].rows.sort((left, right) => remedialAttendanceSortMs(right) - remedialAttendanceSortMs(left));
  }
  return grouped;
}

function openRemedialStudentAttendanceModal(courseKey) {
  if (
    !els.remedialAttendanceModal
    || !els.remedialAttendanceModalTitle
    || !els.remedialAttendanceModalMeta
    || !els.remedialAttendanceModalList
  ) {
    return;
  }
  const safeCourseKey = String(courseKey || '').trim();
  if (!safeCourseKey) {
    return;
  }

  const grouped = state.remedial.attendanceLedgerByCourse || {};
  const group = grouped[safeCourseKey];
  if (!group || !Array.isArray(group.rows) || !group.rows.length) {
    return;
  }

  const rows = [...group.rows];
  const deliveredCount = rows.length;
  const attendedCount = rows.filter((row) => row.status === 'present').length;
  const attendancePercent = deliveredCount > 0 ? (attendedCount / deliveredCount) * 100 : 0;
  els.remedialAttendanceModalTitle.textContent = `${group.course_code} - ${group.course_title}`;
  els.remedialAttendanceModalMeta.textContent =
    `Attendance ${attendancePercent.toFixed(1)}% | Present/Delivered: ${attendedCount}/${deliveredCount}`;

  const rowsMarkup = rows
    .map((row) => {
      const isPresent = row.status === 'present';
      const statusClass = isPresent ? 'present' : 'absent';
      const statusText = isPresent ? 'Present' : 'Absent';
      const classDate = row.class_date ? parseISODateLocal(row.class_date).toLocaleDateString('en-GB') : '--';
      const timeRange = `${formatTime24(row.start_time)}-${formatTime24(row.end_time)}`;
      const detailParts = [timeRange, remedialModeLabel(row)];
      if (isPresent && row.marked_at) {
        detailParts.push(`Marked ${new Date(row.marked_at).toLocaleString()}`);
      }
      return `
        <article class="attendance-detail-row ${statusClass}">
          <div class="attendance-detail-main">
            <strong>${escapeHtml(classDate)}</strong>
            <small>${escapeHtml(detailParts.join(' • '))}</small>
          </div>
          <span class="attendance-detail-status ${statusClass}">${escapeHtml(statusText)}</span>
        </article>
      `;
    })
    .join('');

  els.remedialAttendanceModalList.innerHTML =
    rowsMarkup || '<div class="list-item">No class records found for this subject.</div>';

  state.remedial.selectedAttendanceModalSection = '';
  state.remedial.selectedAttendanceModalCourseKey = safeCourseKey;
  els.remedialAttendanceModal.classList.remove('hidden');
}

function renderRemedialStudentLedgerList() {
  if (!els.remedialStudentLedgerList) {
    return;
  }
  els.remedialStudentLedgerList.innerHTML = '';

  const sourceRows = Array.isArray(state.remedial.attendanceLedger) ? state.remedial.attendanceLedger : [];
  const groupedByCourse = indexRemedialAttendanceByCourse(sourceRows);
  state.remedial.attendanceLedgerByCourse = groupedByCourse;
  const courseKeys = Object.keys(groupedByCourse);

  let deliveredTotal = 0;
  let attendedTotal = 0;
  for (const courseKey of courseKeys) {
    const rows = groupedByCourse[courseKey].rows;
    deliveredTotal += rows.length;
    attendedTotal += rows.filter((row) => row.status === 'present').length;
  }
  const aggregatePercent = deliveredTotal > 0 ? (attendedTotal / deliveredTotal) * 100 : 0;
  if (els.remedialStudentAggregatePercent) {
    els.remedialStudentAggregatePercent.textContent = `${aggregatePercent.toFixed(1)}%`;
  }
  if (els.remedialStudentAttendedDelivered) {
    els.remedialStudentAttendedDelivered.textContent = `${attendedTotal} / ${deliveredTotal}`;
  }

  if (!deliveredTotal) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'No remedial attendance records yet.';
    els.remedialStudentLedgerList.appendChild(row);
    if (state.remedial.selectedAttendanceModalCourseKey) {
      closeRemedialAttendanceModal();
    }
    return;
  }

  const cards = courseKeys
    .map((courseKey) => {
      const group = groupedByCourse[courseKey];
      const rows = group.rows;
      const latest = rows[0] || {};
      const latestDate = latest.class_date ? parseISODateLocal(latest.class_date).toLocaleDateString('en-GB') : 'N/A';
      const latestTime = `${formatTime24(latest.start_time)}-${formatTime24(latest.end_time)}`;
      const latestStatus = latest.status === 'present' ? 'Present' : 'Absent';
      const attendedCount = rows.filter((row) => row.status === 'present').length;
      const deliveredCount = rows.length;
      const percent = deliveredCount > 0 ? (attendedCount / deliveredCount) * 100 : 0;
      const tone = percent >= 75 ? 'good' : percent >= 50 ? 'mid' : 'low';
      const recordLabel = deliveredCount === 1 ? '1 class record' : `${deliveredCount} class records`;

      return {
        latestAtMs: remedialAttendanceSortMs(latest),
        markup: `
          <article
            class="course-aggregate-item course-clickable ${tone}"
            role="button"
            tabindex="0"
            data-remedial-course-key="${escapeHtml(courseKey)}"
            aria-label="Open remedial attendance details for ${escapeHtml(group.course_code)}"
          >
            <div class="course-aggregate-head">
              <h4>${escapeHtml(group.course_code)} - ${escapeHtml(group.course_title)}</h4>
              <span class="course-percent-badge ${tone}">${percent.toFixed(1)}%</span>
            </div>
            <p>${escapeHtml(`Last Class: ${latestDate} | ${latestTime} | ${latestStatus}`)}</p>
            <p>Attended/Delivered: ${attendedCount} / ${deliveredCount}</p>
            <p class="course-card-hint">${escapeHtml(recordLabel)} • Click to view</p>
          </article>
        `,
      };
    })
    .sort((left, right) => right.latestAtMs - left.latestAtMs);

  els.remedialStudentLedgerList.innerHTML = cards.map((card) => card.markup).join('');

  if (state.remedial.selectedAttendanceModalCourseKey) {
    const selectedCourseKey = String(state.remedial.selectedAttendanceModalCourseKey || '');
    if (groupedByCourse[selectedCourseKey]) {
      openRemedialStudentAttendanceModal(selectedCourseKey);
    } else {
      closeRemedialAttendanceModal();
    }
  }
}

async function refreshRemedialClasses() {
  if (!authState.user || (authState.user.role !== 'faculty' && authState.user.role !== 'admin')) {
    state.remedial.classes = [];
    state.remedial.selectedClassAttendance = [];
    state.remedial.selectedClassAttendanceSections = [];
    state.remedial.selectedClassAttendanceAllStudents = [];
    closeRemedialAttendanceModal();
    renderRemedialClassesList();
    renderRemedialClassSelect();
    renderRemedialAttendanceList();
    return;
  }
  const rows = await api('/makeup/classes');
  state.remedial.classes = Array.isArray(rows) ? rows : [];
  renderRemedialClassesList();
  renderRemedialClassSelect();
}

async function refreshRemedialMessages() {
  if (!authState.user || authState.user.role !== 'student') {
    state.remedial.messages = [];
    renderRemedialMessagesList();
    return;
  }
  const rows = await api('/makeup/messages?limit=80');
  state.remedial.messages = Array.isArray(rows) ? rows : [];
  renderRemedialMessagesList();
}

async function refreshRemedialAttendanceLedger() {
  if (!authState.user || authState.user.role !== 'student') {
    state.remedial.attendanceLedger = [];
    renderRemedialStudentLedgerList();
    return;
  }
  const rows = await api('/makeup/attendance/history?limit=80');
  state.remedial.attendanceLedger = Array.isArray(rows) ? rows : [];
  renderRemedialStudentLedgerList();
}

async function refreshStudentMessages() {
  if (!authState.user || authState.user.role !== 'student') {
    state.studentMessages = [];
    renderStudentMessagesCenter();
    return;
  }
  const rows = await api('/messages?limit=60');
  state.studentMessages = Array.isArray(rows) ? rows : [];
  renderStudentMessagesCenter();
}

async function refreshRemedialAttendanceForClass(classId = null) {
  const targetClassId = Number(classId || state.remedial.selectedClassId || els.remedialClassSelect?.value || 0);
  if (!targetClassId) {
    state.remedial.selectedClassAttendance = [];
    state.remedial.selectedClassAttendanceSections = [];
    state.remedial.selectedClassAttendanceAllStudents = [];
    closeRemedialAttendanceModal();
    renderRemedialAttendanceList();
    return;
  }
  state.remedial.selectedClassId = targetClassId;
  const payload = await api(`/makeup/classes/${targetClassId}/attendance`);
  state.remedial.selectedClassAttendance = Array.isArray(payload?.students) ? payload.students : [];
  state.remedial.selectedClassAttendanceSections = Array.isArray(payload?.section_summaries)
    ? payload.section_summaries
    : [];
  state.remedial.selectedClassAttendanceAllStudents = Array.isArray(payload?.all_students)
    ? payload.all_students
    : [];
  closeRemedialAttendanceModal();
  renderRemedialAttendanceList();
}

async function refreshRemedialModule() {
  if (!authState.user) {
    return;
  }
  if (!Object.keys(state.coursesById).length) {
    await loadCoursesMap();
  }
  if (authState.user.role === 'faculty') {
    await loadRemedialEligibleCourses();
  } else {
    state.remedial.eligibleCourses = [];
    state.remedial.demoBypassLeadTime = false;
  }
  renderRemedialCourseOptions();
  applyRemedialModeVisibility();
  renderRemedialDemoToggle();
  if (authState.user.role === 'student') {
    await refreshRemedialMessages();
    await refreshRemedialAttendanceLedger();
    await refreshStudentMessages();
    renderRemedialCodeDetails();
    setRemedialStudentStatus('Use code from Messages, validate, then mark attendance in first 15 minutes.');
    return;
  }
  await refreshRemedialClasses();
  if (state.remedial.selectedClassId) {
    await refreshRemedialAttendanceForClass(state.remedial.selectedClassId);
  } else {
    state.remedial.selectedClassAttendance = [];
    state.remedial.selectedClassAttendanceSections = [];
    state.remedial.selectedClassAttendanceAllStudents = [];
    closeRemedialAttendanceModal();
    renderRemedialAttendanceList();
  }
}

async function sendRemedialCodeToSections(classId) {
  const targetClassId = Number(classId || 0);
  if (!targetClassId) {
    throw new Error('Select a valid remedial class first.');
  }
  const customMessage = String(els.remedialCustomMessageInput?.value || '').trim();
  const payload = await api(`/makeup/classes/${targetClassId}/send-message`, {
    method: 'POST',
    body: JSON.stringify({
      custom_message: customMessage || null,
    }),
  });
  setRemedialFacultyStatus(String(payload?.message || 'Code message sent to selected sections.'));
  log(`Remedial code broadcast sent for class #${targetClassId}`);
  await refreshRemedialClasses();
}

async function sendFacultyBroadcastMessage() {
  if (!authState.user || authState.user.role !== 'faculty') {
    throw new Error('Only faculty can send broadcast messages.');
  }
  const sections = normalizeRemedialSections(els.facultyMessageSections?.value);
  const messageType = String(els.facultyMessageType?.value || 'Announcement').trim();
  const messageText = String(els.facultyMessageText?.value || '').trim();
  if (!sections.length || !messageText) {
    throw new Error('Enter section(s) and a message to send.');
  }
  const payload = await api('/messages/send', {
    method: 'POST',
    body: JSON.stringify({
      sections,
      message_type: messageType,
      message: messageText,
    }),
  });
  setFacultyMessageStatus(String(payload?.message || 'Message sent.'));
  log(`Faculty message sent (${messageType})`);
  if (els.facultyMessageText) {
    els.facultyMessageText.value = '';
  }
  await refreshStudentMessages();
}

async function sendDirectStudentEmail() {
  const role = authState.user?.role;
  if (role !== 'admin' && role !== 'faculty') {
    throw new Error('Only admin or faculty can send direct student emails.');
  }
  const studentId = Number(els.directEmailStudentId?.value || 0);
  const registrationNumber = String(els.directEmailRegistration?.value || '').trim();
  const email = String(els.directEmailStudentEmail?.value || '').trim().toLowerCase();
  const subject = String(els.directEmailSubject?.value || '').trim();
  const message = String(els.directEmailMessage?.value || '').trim();
  if (!studentId && !registrationNumber && !email) {
    throw new Error('Provide student id, registration number, or email.');
  }
  if (!subject || !message) {
    throw new Error('Add subject and message before sending.');
  }
  const payload = {
    student_id: studentId || null,
    registration_number: registrationNumber || null,
    email: email || null,
    subject,
    message,
  };
  const response = await api('/messages/direct-email', {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs: 60000,
  });
  const deliveredTo = String(response?.delivered_to || '').trim();
  const statusMessage = deliveredTo ? `Email sent to ${deliveredTo}.` : 'Email sent to student.';
  setDirectEmailStatus(statusMessage, false, 'success');
  if (els.directEmailMessage) {
    els.directEmailMessage.value = '';
  }
}

async function cancelRemedialClass(classId) {
  const targetClassId = Number(classId || 0);
  if (!targetClassId) {
    throw new Error('Select a valid remedial class first.');
  }
  const confirmed = window.confirm('Reject this remedial class? Students will stop seeing it.');
  if (!confirmed) {
    return;
  }
  const payload = await api(`/makeup/classes/${targetClassId}/cancel`, { method: 'POST' });
  setRemedialFacultyStatus(`Remedial class ${payload.remedial_code} rejected.`);
  log(`Remedial class rejected (#${targetClassId})`);
  await refreshRemedialModule();
}

async function createRemedialClass() {
  if (!authState.user || authState.user.role !== 'faculty') {
    throw new Error('Only faculty can schedule remedial classes from this panel.');
  }
  const courseId = Number(els.remedialCourseSelect?.value || 0);
  const manualCourseCode = normalizeRemedialCourseCode(els.remedialCourseCodeInput?.value);
  const manualCourseTitle = normalizeRemedialCourseTitle(els.remedialCourseTitleInput?.value);
  const useManualCourse = !courseId;
  const facultyId = Number(authState.user.faculty_id || 0);
  const classDate = String(els.remedialDate?.value || '').trim();
  const startTime = String(els.remedialStartTime?.value || '').trim();
  const endTime = String(els.remedialEndTime?.value || '').trim();
  const topic = String(els.remedialTopic?.value || '').trim();
  const sections = normalizeRemedialSections(els.remedialSectionsInput?.value);
  const classMode = String(els.remedialModeSelect?.value || 'offline').toLowerCase();
  const roomNumber = String(els.remedialRoomInput?.value || '').trim();
  let onlineLink = normalizedRemedialOnlineLink(els.remedialOnlineLinkInput?.value);
  if (!facultyId || !classDate || !startTime || !endTime || !topic || !sections.length) {
    throw new Error('Select date/time, enter section(s) and topic to schedule remedial class.');
  }
  if (useManualCourse && (!manualCourseCode || !manualCourseTitle)) {
    throw new Error('Select assigned course, or enter both manual course code and course name.');
  }
  if (classMode === 'online') {
    onlineLink = normalizedRemedialOnlineLink(onlineLink);
    if (els.remedialOnlineLinkInput) {
      els.remedialOnlineLinkInput.value = onlineLink;
    }
  }
  if (classMode === 'offline' && !roomNumber) {
    throw new Error('Offline remedial class requires a room number.');
  }

  const payload = await api('/makeup/classes', {
    method: 'POST',
    body: JSON.stringify({
      course_id: courseId || null,
      course_code: useManualCourse ? manualCourseCode : null,
      course_title: useManualCourse ? manualCourseTitle : null,
      faculty_id: facultyId,
      class_date: classDate,
      start_time: startTime,
      end_time: endTime,
      topic,
      sections,
      class_mode: classMode,
      room_number: classMode === 'offline' ? roomNumber : null,
      online_link: classMode === 'online' ? onlineLink : null,
      demo_bypass_lead_time: Boolean(state.remedial.demoBypassLeadTime),
    }),
  });
  setRemedialFacultyStatus(`Remedial class scheduled. Generated code: ${payload.remedial_code}. Click "Send Code to Section(s)" to notify students.`);
  log(`Remedial class created (${payload.remedial_code})`);
  await loadCoursesMap();
  if (els.remedialTopic) {
    els.remedialTopic.value = '';
  }
  if (els.remedialSectionsInput) {
    els.remedialSectionsInput.value = '';
  }
  if (els.remedialRoomInput) {
    els.remedialRoomInput.value = '';
  }
  if (els.remedialOnlineLinkInput) {
    els.remedialOnlineLinkInput.value = '';
  }
  await refreshRemedialModule();
}

async function validateRemedialCode() {
  if (!authState.user || authState.user.role !== 'student') {
    throw new Error('Only students can validate remedial code.');
  }
  const remedialCode = String(els.remedialCodeInput?.value || '').trim().toUpperCase();
  if (!remedialCode) {
    throw new Error('Enter remedial code to validate.');
  }
  const payload = await api('/makeup/code/validate', {
    method: 'POST',
    body: JSON.stringify({ remedial_code: remedialCode }),
  });
  state.remedial.validatedClass = payload || null;
  const classId = Number(payload?.class_id || 0);
  if (!classId || classId !== Number(state.remedial.markedClassId || 0)) {
    state.remedial.markedClassId = null;
    state.remedial.markedOnlineLink = '';
  }
  renderRemedialCodeDetails();
  setRemedialStudentStatus(String(payload?.message || 'Code validated successfully.'));
  log(`Remedial code validated (${remedialCode})`);
  await Promise.allSettled([
    loadStudentTimetable({ forceNetwork: true }),
    refreshRemedialMessages(),
    refreshStudentMessages(),
  ]);
  return payload;
}

async function applyRemedialCodeFromMessage(remedialCode) {
  const code = String(remedialCode || '').trim().toUpperCase();
  if (!code) {
    throw new Error('Invalid remedial code in message.');
  }
  if (els.remedialCodeInput) {
    els.remedialCodeInput.value = code;
  }
  await validateRemedialCode();
}

function resolveRemedialClassLabel(details = null, remedialCode = '') {
  const resolvedCode = String(details?.course_code || '').trim();
  const resolvedTitle = String(details?.course_title || '').trim();
  if (resolvedCode && resolvedTitle) {
    return `${resolvedCode} - ${resolvedTitle}`;
  }
  const normalizedCode = String(remedialCode || '').trim().toUpperCase();
  const matched = (Array.isArray(state.remedial.messages) ? state.remedial.messages : []).find((row) => {
    const rowCode = String(row?.remedial_code || '').trim().toUpperCase();
    return normalizedCode && rowCode === normalizedCode;
  });
  if (matched?.course_code && matched?.course_title) {
    return `${matched.course_code} - ${matched.course_title}`;
  }
  const classId = Number(details?.class_id || 0);
  if (classId > 0) {
    return `Remedial Class #${classId}`;
  }
  if (normalizedCode) {
    return `Remedial Class (${normalizedCode})`;
  }
  return 'Remedial Class';
}

async function buildRemedialVerificationPayload(remedialCode, studentId, selfieDataUrl, selfieFrames = []) {
  const payload = {
    remedial_code: String(remedialCode || '').trim().toUpperCase(),
    student_id: Number(studentId || 0),
    selfie_photo_data_url: selfieDataUrl,
  };
  if (Array.isArray(selfieFrames) && selfieFrames.length) {
    payload.selfie_frames_data_urls = selfieFrames;
  }

  if (!USE_CLIENT_AI_FACE_ASSIST || !state.student.profilePhotoDataUrl) {
    return payload;
  }

  try {
    const verdict = await Promise.race([
      compareFacesWithAI(state.student.profilePhotoDataUrl, selfieDataUrl),
      new Promise((resolve) => {
        window.setTimeout(() => resolve(null), 1200);
      }),
    ]);
    if (verdict) {
      payload.ai_match = verdict.match;
      payload.ai_confidence = verdict.confidence;
      payload.ai_reason = verdict.reason;
      payload.ai_model = verdict.model;
    }
  } catch (error) {
    log(`Client AI verification unavailable for remedial, using server OpenCV fallback: ${error.message}`);
  }

  return payload;
}

async function submitRemedialAttendanceAttempt(remedialCode, studentId, selfieDataUrl, selfieFrames = []) {
  const payload = await buildRemedialVerificationPayload(remedialCode, studentId, selfieDataUrl, selfieFrames);
  return apiWithTimeout(
    '/makeup/attendance/mark',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    ATTENDANCE_VERIFY_REQUEST_TIMEOUT_MS,
    'Verification request timed out. Retrying automatically...'
  );
}

async function startRemedialLiveAttendanceVerification({ remedialCode, studentId, details }) {
  if (state.camera.liveVerificationActive) {
    throw new Error('Live verification is already running.');
  }
  const classLabel = resolveRemedialClassLabel(details, remedialCode);

  await openCameraModal({
    title: 'Remedial Facial Attendance Verification',
    facingMode: 'user',
    referencePhotoDataUrl: state.student.profilePhotoDataUrl,
    burstFrames: LIVE_VERIFICATION_BURST_FRAMES,
    captureEnabled: false,
    messageOverride: 'OpenCV face verification running for remedial class. Keep one face centered and move head slightly left/right/up/down.',
  });

  const sessionToken = state.camera.liveSessionToken;
  state.camera.liveVerificationActive = true;

  let attempts = 0;
  const maxAttempts = LIVE_VERIFICATION_MAX_ATTEMPTS;
  while (
    state.camera.liveVerificationActive
    && state.camera.stream
    && sessionToken === state.camera.liveSessionToken
  ) {
    if (attempts >= maxAttempts) {
      const timeoutMsg = 'Verification took too long. Improve front lighting, keep one centered face, then retry.';
      if (els.cameraMessage) {
        els.cameraMessage.textContent = timeoutMsg;
      }
      setRemedialStudentStatus(timeoutMsg, true);
      break;
    }
    attempts += 1;
    try {
      if (els.cameraMessage) {
        els.cameraMessage.textContent = `Analyzing live frames... attempt ${attempts}/${maxAttempts}`;
      }
      const selfieFrames = await captureBurstFramesFromCamera(
        LIVE_VERIFICATION_BURST_FRAMES,
        LIVE_VERIFICATION_BURST_INTERVAL_MS,
        0.9
      );
      const selfieDataUrl = selfieFrames[0];
      if (selfieDataUrl) {
        state.student.selfieDataUrl = selfieDataUrl;
      }

      const response = await submitRemedialAttendanceAttempt(remedialCode, studentId, selfieDataUrl, selfieFrames);
      const rawMessage = String(response?.message || '').trim();
      const alreadyMarked = rawMessage.toLowerCase().includes('already marked');
      const detailMessage = alreadyMarked
        ? `Attendance already marked for ${classLabel}.`
        : `Attendance successfully marked for ${classLabel}.`;
      if (els.cameraMessage) {
        els.cameraMessage.textContent = 'Attendance verified. Closing camera...';
      }

      const responseMode = String(response?.class_mode || details?.class_mode || '').toLowerCase();
      const isOnlineClass = responseMode === 'online';
      const classId = Number(details?.class_id || response?.makeup_class_id || 0);
      if (isOnlineClass && classId > 0) {
        state.remedial.markedClassId = classId;
        state.remedial.markedOnlineLink = normalizedRemedialOnlineLink(response?.online_link || details?.online_link);
      } else {
        state.remedial.markedClassId = null;
        state.remedial.markedOnlineLink = '';
      }

      setRemedialStudentStatus(detailMessage);
      renderRemedialCodeDetails();
      log(detailMessage);
      await sleep(850);
      closeCameraModal();
      return response;
    } catch (error) {
      const message = String(error?.message || 'Live verification attempt failed.');
      if (els.cameraMessage) {
        els.cameraMessage.textContent = `${deriveLiveGuidance(message)} Auto retry in progress...`;
      }
      if (shouldStopLiveVerification(message)) {
        if (els.cameraMessage) {
          els.cameraMessage.textContent = `Verification stopped: ${message}`;
        }
        setRemedialStudentStatus(message, true);
        break;
      }
      await sleep(650);
    }
  }

  if (state.camera.stream && sessionToken === state.camera.liveSessionToken) {
    closeCameraModal();
  }
  throw new Error('Remedial facial verification was not completed. Please retry.');
}

async function markRemedialAttendance() {
  if (!authState.user || authState.user.role !== 'student') {
    throw new Error('Only students can mark remedial attendance.');
  }
  const studentId = Number(authState.user.student_id || 0);
  const remedialCode = String(els.remedialCodeInput?.value || '').trim().toUpperCase();
  if (!studentId || !remedialCode) {
    throw new Error('Enter remedial code before submitting.');
  }

  if (!state.student.profilePhotoDataUrl) {
    throw new Error('Upload profile photo first. It is required for facial attendance.');
  }
  if (requiresStudentEnrollmentSetup()) {
    throw new Error('Complete one-time enrollment video before marking attendance.');
  }

  let validated = state.remedial.validatedClass;
  if (
    !validated
    || !validated.valid
    || Number(validated.class_id || 0) <= 0
    || String(remedialCode) !== String(els.remedialCodeInput?.value || '').trim().toUpperCase()
  ) {
    validated = await validateRemedialCode();
  }
  if (!validated?.attendance_window_open) {
    throw new Error('Attendance window currently closed for this remedial class.');
  }

  await startRemedialLiveAttendanceVerification({
    remedialCode,
    studentId,
    details: validated,
  });
  await Promise.allSettled([
    loadStudentTimetable({ forceNetwork: true }),
    loadStudentAttendanceInsights(),
    refreshRemedialMessages(),
    refreshRemedialAttendanceLedger(),
  ]);
}

async function refreshActiveModuleData() {
  if (!authState.user) {
    return;
  }
  const moduleKey = getSanitizedModuleKey(state.ui.activeModule);
  if (moduleKey === 'saarthi') {
    if (authState.user.role === 'student') {
      await loadSaarthiStatus({ silent: true });
    }
    return;
  }
  if (moduleKey === 'food') {
    await refreshFoodModule();
    return;
  }
  if (moduleKey === 'administrative') {
    await refreshAdministrativeModule();
    return;
  }
  if (moduleKey === 'rms') {
    await refreshRmsModule();
    return;
  }
  if (moduleKey === 'remedial') {
    await refreshRemedialModule();
    return;
  }
  if (authState.user.role === 'student') {
    await refreshStudentTimetableSurface({ forceNetwork: true });
    const results = await Promise.allSettled([
      loadStudentAttendanceInsights(),
      refreshStudentMessages(),
      loadSaarthiStatus({ silent: true }),
    ]);
    const failed = results.find((result) => result.status === 'rejected');
    if (failed?.status === 'rejected') {
      throw failed.reason;
    }
  }
  if (authState.user.role === 'faculty' || authState.user.role === 'admin') {
    await loadFacultySchedules();
    await refreshFacultyDashboard();
    return;
  }
  await refreshAttendanceData();
}

function loadPuterSdk() {
  if (window.puter?.ai?.chat) {
    return Promise.resolve(window.puter.ai);
  }

  if (puterSdkPromise) {
    return puterSdkPromise;
  }

  puterSdkPromise = new Promise((resolve, reject) => {
    const existingScript = document.querySelector(`script[src="${PUTER_SDK_URL}"]`);
    if (existingScript) {
      existingScript.addEventListener('load', () => {
        if (window.puter?.ai?.chat) {
          resolve(window.puter.ai);
          return;
        }
        reject(new Error('Puter SDK loaded but AI client is unavailable.'));
      });
      existingScript.addEventListener('error', () => {
        reject(new Error('Failed to load Puter SDK.'));
      });
      return;
    }

    const script = document.createElement('script');
    script.src = PUTER_SDK_URL;
    script.async = true;
    script.onload = () => {
      if (window.puter?.ai?.chat) {
        resolve(window.puter.ai);
        return;
      }
      reject(new Error('Puter SDK loaded but AI client is unavailable.'));
    };
    script.onerror = () => reject(new Error('Failed to load Puter SDK.'));
    document.head.appendChild(script);
  });

  return puterSdkPromise;
}

function loadRazorpayCheckoutSdk() {
  if (window.Razorpay) {
    return Promise.resolve(window.Razorpay);
  }

  if (razorpaySdkPromise) {
    return razorpaySdkPromise;
  }

  const ensureRazorpayNetworkHints = () => {
    const hints = [
      { rel: 'preconnect', href: RAZORPAY_SDK_ORIGIN, crossOrigin: 'anonymous' },
      { rel: 'dns-prefetch', href: '//checkout.razorpay.com' },
    ];
    for (const hint of hints) {
      if (document.head.querySelector(`link[rel="${hint.rel}"][href="${hint.href}"]`)) {
        continue;
      }
      const link = document.createElement('link');
      link.rel = hint.rel;
      link.href = hint.href;
      if (hint.crossOrigin) {
        link.crossOrigin = hint.crossOrigin;
      }
      document.head.appendChild(link);
    }
  };
  const removeRazorpayScript = (scriptEl) => {
    if (scriptEl?.parentNode) {
      scriptEl.parentNode.removeChild(scriptEl);
    }
  };

  ensureRazorpayNetworkHints();
  razorpaySdkPromise = new Promise((resolve, reject) => {
    let settled = false;
    let timeoutId = null;
    const settle = (payload, asError = false) => {
      if (settled) {
        return;
      }
      settled = true;
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
      if (asError) {
        reject(payload);
        return;
      }
      resolve(payload);
    };
    const resolveIfReady = () => {
      if (window.Razorpay) {
        settle(window.Razorpay);
        return true;
      }
      return false;
    };

    const attachScriptListeners = (scriptEl) => {
      const handleLoad = () => {
        scriptEl.dataset.loadState = 'loaded';
        if (resolveIfReady()) {
          return;
        }
        removeRazorpayScript(scriptEl);
        settle(new Error('Razorpay checkout loaded but client is unavailable.'), true);
      };
      const handleError = () => {
        scriptEl.dataset.loadState = 'error';
        removeRazorpayScript(scriptEl);
        settle(new Error('Failed to load Razorpay checkout.'), true);
      };
      scriptEl.addEventListener('load', handleLoad, { once: true });
      scriptEl.addEventListener('error', handleError, { once: true });
      timeoutId = window.setTimeout(() => {
        if (settled) {
          return;
        }
        scriptEl.dataset.loadState = 'error';
        removeRazorpayScript(scriptEl);
        settle(new Error('Razorpay checkout timed out while loading.'), true);
      }, RAZORPAY_SDK_LOAD_TIMEOUT_MS);
    };

    const mountScript = () => {
      const script = document.createElement('script');
      script.src = RAZORPAY_SDK_URL;
      script.async = true;
      script.dataset.loadState = 'loading';
      document.head.appendChild(script);
      attachScriptListeners(script);
    };

    let existingScript = document.querySelector(`script[src="${RAZORPAY_SDK_URL}"]`);
    if (existingScript) {
      if (resolveIfReady()) {
        return;
      }
      const loadState = String(existingScript.dataset.loadState || '').trim().toLowerCase();
      if (loadState === 'error' || loadState === 'loaded') {
        removeRazorpayScript(existingScript);
        existingScript = null;
      }
    }
    if (existingScript) {
      attachScriptListeners(existingScript);
      return;
    }
    mountScript();
  }).catch((error) => {
    razorpaySdkPromise = null;
    throw error;
  });

  return razorpaySdkPromise;
}

async function ensureRazorpayCheckoutSdk() {
  try {
    return await loadRazorpayCheckoutSdk();
  } catch (_) {
    throw new Error('Razorpay checkout failed to load. Check internet and retry.');
  }
}

function warmRazorpayCheckoutSdk() {
  void loadRazorpayCheckoutSdk().catch(() => {});
}

async function getPuterClient() {
  try {
    return await loadPuterSdk();
  } catch (_) {
    throw new Error('AI assistant unavailable right now. Check internet and retry.');
  }
}

function extractAiText(response) {
  if (typeof response === 'string') {
    return response;
  }
  if (response?.text && typeof response.text === 'string') {
    return response.text;
  }
  if (response?.message?.content && typeof response.message.content === 'string') {
    return response.message.content;
  }
  if (response?.content && typeof response.content === 'string') {
    return response.content;
  }
  if (Array.isArray(response?.choices) && response.choices[0]?.message?.content) {
    return String(response.choices[0].message.content);
  }
  try {
    return JSON.stringify(response);
  } catch (_) {
    return String(response || '');
  }
}

function parseJsonFromText(text) {
  if (!text) {
    throw new Error('AI returned empty text');
  }

  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const candidate = fenced ? fenced[1].trim() : text.trim();

  try {
    return JSON.parse(candidate);
  } catch (_) {
    const first = candidate.indexOf('{');
    const last = candidate.lastIndexOf('}');
    if (first >= 0 && last > first) {
      return JSON.parse(candidate.slice(first, last + 1));
    }
    throw new Error('Unable to parse JSON from AI response');
  }
}

async function coerceJsonWithAI(rawText, schemaHint) {
  const puter = await getPuterClient();
  const prompt = [
    'Convert the following content into strict JSON only.',
    `Schema hint: ${schemaHint}`,
    'Do not add markdown. Return JSON only.',
    `Content:\\n${rawText}`,
  ].join('\\n');
  const response = await puter.chat(prompt, { model: AI_MODEL });
  return parseJsonFromText(extractAiText(response));
}

async function runPuter(prompt) {
  const puter = await getPuterClient();
  const stream = await puter.chat(prompt, {
    model: AI_MODEL,
    stream: true,
  });

  els.aiOutput.textContent = '';
  for await (const part of stream) {
    if (part?.text) {
      els.aiOutput.textContent += part.text;
    }
  }
}

async function callVisionAI(prompt, imageDataUrl) {
  const puter = await getPuterClient();
  const response = await puter.chat(prompt, imageDataUrl, {
    model: AI_MODEL,
  });
  return extractAiText(response);
}

async function describeFace(imageDataUrl, label) {
  const prompt = [
    'You are a biometric face descriptor for attendance matching.',
    `Analyze the ${label} image and return JSON only with keys:`,
    'face_signature (string), key_traits (array of strings), quality_score (number 0..1).',
    'Focus mostly on stable facial structure: eye spacing, nose geometry, jawline, cheekbone layout, face proportions.',
    'Treat changeable details (beard, mustache, hairstyle, minor lighting, skin tone shift, expression) as low-priority.',
    'Do not include markdown.',
  ].join('\n');

  const text = await callVisionAI(prompt, imageDataUrl);
  return parseJsonFromText(text);
}

async function compareFacesWithAI(profileImageDataUrl, selfieDataUrl) {
  const profile = await describeFace(profileImageDataUrl, 'stored profile photo');
  const selfie = await describeFace(selfieDataUrl, 'live selfie photo');

  const puter = await getPuterClient();
  const comparePrompt = [
    'You compare two face descriptors for attendance verification.',
    'Return JSON only with keys: match (boolean), confidence (number 0..1), reason (string).',
    'Decision rule: prioritize core face geometry and relative feature distances.',
    'Do not reject for only minor differences like beard/mustache/hairstyle/expression.',
    'If core structure appears the same person, keep confidence moderate-to-high.',
    `Profile Descriptor: ${JSON.stringify(profile)}`,
    `Selfie Descriptor: ${JSON.stringify(selfie)}`,
  ].join('\n');

  const response = await puter.chat(comparePrompt, {
    model: AI_MODEL,
  });
  const rawText = extractAiText(response);
  let parsed;
  try {
    parsed = parseJsonFromText(rawText);
  } catch (_) {
    parsed = await coerceJsonWithAI(
      rawText,
      '{\"match\": boolean, \"confidence\": number(0..1), \"reason\": string}'
    );
  }

  const confidence = Math.max(0, Math.min(1, Number(parsed.confidence) || 0));
  return {
    match: Boolean(parsed.match),
    confidence,
    reason: String(parsed.reason || 'AI comparison completed'),
    model: AI_MODEL,
  };
}

function formatTime(rawTime) {
  if (!rawTime) {
    return '--:--';
  }
  const [h, m] = String(rawTime).split(':');
  const hours24 = Number(h);
  const minutes = Number(m || 0);
  const suffix = hours24 >= 12 ? 'PM' : 'AM';
  const hours12 = ((hours24 + 11) % 12) + 1;
  return `${hours12}:${String(minutes).padStart(2, '0')} ${suffix}`;
}

function toMinutes(rawTime) {
  if (!rawTime) {
    return 0;
  }
  const [h, m] = String(rawTime).split(':');
  return Number(h) * 60 + Number(m || 0);
}

function formatTime24(rawTime) {
  if (!rawTime) {
    return '--:--';
  }
  const [h, m] = String(rawTime).split(':');
  return `${String(Number(h)).padStart(2, '0')}:${String(Number(m || 0)).padStart(2, '0')}`;
}

function weekdayFromWeekStart(weekStartRaw) {
  if (!weekStartRaw) {
    return null;
  }
  const parts = String(weekStartRaw).split('-').map((part) => Number(part));
  if (parts.length !== 3 || parts.some((value) => Number.isNaN(value))) {
    return null;
  }
  const [year, month, day] = parts;
  const weekStart = new Date(year, month - 1, day);
  const today = new Date();
  const todayMidnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const diffDays = Math.floor((todayMidnight.getTime() - weekStart.getTime()) / 86400000);
  if (diffDays < 0 || diffDays > 6) {
    return null;
  }
  return diffDays;
}

function slotTextLines(item) {
  const labelRaw = String(item.classroom_label || '').trim();
  const [firstPart, secondPart] = labelRaw.split('|').map((part) => String(part || '').trim());
  const roomNo = secondPart
    || (firstPart ? String(firstPart).split(' - ')[0].trim() : '')
    || 'Room TBA';
  return {
    primary: `${item.course_code} - ${item.course_title}`,
    secondary: roomNo,
  };
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function statusLabel(status) {
  if (!status) {
    return 'Not Marked';
  }
  return status.replaceAll('_', ' ').toUpperCase();
}

function parseClassDateTimeLocal(classDateRaw, rawTime) {
  const dateText = String(classDateRaw || '');
  const timeText = String(rawTime || '');
  const dateParts = dateText.split('-').map((part) => Number(part));
  const timeParts = timeText.split(':').map((part) => Number(part));
  if (dateParts.length !== 3 || dateParts.some((value) => Number.isNaN(value))) {
    return null;
  }
  if (timeParts.length < 2 || Number.isNaN(timeParts[0]) || Number.isNaN(timeParts[1])) {
    return null;
  }
  const [year, month, day] = dateParts;
  const [hour, minute] = timeParts;
  return new Date(year, month - 1, day, hour, minute, 0, 0);
}

function getAttendanceWindowMinutes(item) {
  const raw = Number(item?.attendance_window_minutes || 0);
  if (Number.isFinite(raw) && raw > 0) {
    return Math.min(90, Math.max(1, Math.round(raw)));
  }
  return 10;
}

function buildStudentAttendanceTimeline(source = getKpiSourceTimetable()) {
  if (!Array.isArray(source) || !source.length) {
    return [];
  }
  return source
    .map((item) => {
      const start = parseClassDateTimeLocal(item.class_date, item.start_time);
      const end = parseClassDateTimeLocal(item.class_date, item.end_time);
      if (!start || !end || Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        return null;
      }
      return {
        item,
        start,
        end,
        windowEnd: new Date(start.getTime() + (getAttendanceWindowMinutes(item) * 60 * 1000)),
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.start.getTime() - b.start.getTime());
}

function isStudentAttendanceDemoEnabled() {
  return Boolean(CLIENT_DEMO_FEATURES_ENABLED && authState.user?.role === 'student' && state.student.demoAttendanceEnabled);
}

function findStudentDemoAttendanceState(nowArg = new Date()) {
  if (!isStudentAttendanceDemoEnabled()) {
    return null;
  }
  return {
    mode: 'demo',
    schedule: null,
    headline: 'Demo Attendance | Anytime',
    subtitle: 'Independent demo mode for testing full attendance verification flow. No attendance data will be saved.',
  };
}

function findEffectiveAttendanceManagementState(nowArg = new Date()) {
  return findStudentDemoAttendanceState(nowArg) || findAttendanceManagementState(nowArg);
}

function getSlotClass(item) {
  const status = resolveTimetableKpi(item);
  if (status.key === 'present') {
    return 'slot-present';
  }
  if (status.key === 'absent') {
    return 'slot-absent';
  }
  if (status.key === 'mark') {
    return 'slot-mark slot-open-window';
  }
  return 'slot-upcoming';
}

function resolveTimetableKpi(item, nowArg = new Date()) {
  const now = nowArg instanceof Date ? nowArg : new Date();
  const raw = String(item.attendance_status || '').toLowerCase();
  const markedPresent = ['verified', 'approved', 'present', 'pending_review'].includes(raw);
  const classStart = parseClassDateTimeLocal(item.class_date, item.start_time);
  const classEnd = parseClassDateTimeLocal(item.class_date, item.end_time);

  if (!classStart || !classEnd || Number.isNaN(classStart.getTime()) || Number.isNaN(classEnd.getTime())) {
    if (markedPresent) {
      return { key: 'present', label: 'Present' };
    }
    if (item.is_open_now) {
      return { key: 'mark', label: 'Mark Attendance' };
    }
    if (item.is_ended_now || item.is_active_now) {
      return { key: 'absent', label: 'Absent' };
    }
    return { key: 'upcoming', label: 'Upcoming' };
  }

  const windowMinutes = getAttendanceWindowMinutes(item);
  const windowEnd = new Date(classStart.getTime() + (windowMinutes * 60 * 1000));

  if (now < classStart) {
    return { key: 'upcoming', label: 'Upcoming' };
  }

  if (markedPresent) {
    return { key: 'present', label: 'Present' };
  }

  if (now <= windowEnd) {
    if (String(item.class_kind || 'regular').toLowerCase() === 'remedial') {
      return { key: 'mark', label: 'Use Remedial Code' };
    }
    return { key: 'mark', label: 'Mark Attendance' };
  }

  return { key: 'absent', label: 'Absent' };
}

function getKpiSourceTimetable() {
  if (Array.isArray(state.student.kpiTimetable) && state.student.kpiTimetable.length) {
    return state.student.kpiTimetable;
  }
  return Array.isArray(state.student.timetable) ? state.student.timetable : [];
}

function findAttendanceManagementState(nowArg = new Date()) {
  const now = nowArg instanceof Date ? nowArg : new Date();
  const source = getKpiSourceTimetable();
  if (!source.length) {
    return {
      mode: 'none',
      schedule: null,
      headline: 'Upcoming Class | --:-- -- - --:-- -- | --',
      subtitle: 'Timetable sync in progress. KPI auto-refreshes every 45 seconds.',
    };
  }

  const timeline = buildStudentAttendanceTimeline(source);
  if (!timeline.length) {
    return {
      mode: 'none',
      schedule: null,
      headline: 'Upcoming Class | --:-- -- - --:-- -- | --',
      subtitle: 'No valid class slots available in timetable.',
    };
  }

  const openNow = timeline.find((slot) => now >= slot.start && now <= slot.windowEnd);
  if (openNow) {
    const selected = openNow.item;
    const isRemedial = String(selected.class_kind || 'regular').toLowerCase() === 'remedial';
    return {
      mode: 'mark',
      schedule: selected,
      headline: `${isRemedial ? 'Remedial Attendance' : 'Mark Attendance'} | ${selected.course_code}`,
      subtitle: `${formatTime(selected.start_time)} - ${formatTime(selected.end_time)} | ${selected.course_code} | ${selected.classroom_label || 'Room TBA'}`,
    };
  }

  const upcoming = timeline.find((slot) => now < slot.start);
  if (upcoming) {
    const selected = upcoming.item;
    return {
      mode: 'upcoming',
      schedule: selected,
      headline: `Upcoming Class | ${formatTime(selected.start_time)} - ${formatTime(selected.end_time)} | ${selected.course_code}`,
      subtitle: `${selected.course_code} | ${selected.classroom_label || 'Room TBA'} | ${parseISODateLocal(selected.class_date).toLocaleDateString('en-GB')}`,
    };
  }

  return {
    mode: 'none',
    schedule: null,
    headline: 'Upcoming Class | --:-- -- - --:-- -- | --',
    subtitle: 'No more upcoming classes in the active timetable range.',
  };
}

function isRemedialAttendanceWindow(kpi = null) {
  const resolved = kpi || findAttendanceManagementState();
  const scheduleId = Number(resolved?.schedule?.schedule_id || 0);
  const classKind = String(resolved?.schedule?.class_kind || 'regular').toLowerCase();
  return resolved?.mode === 'mark' && scheduleId > 0 && classKind === 'remedial';
}

function renderStudentAttendanceDemoToggle() {
  if (!els.studentAttendanceDemoBtn) {
    return;
  }
  const enabled = Boolean(state.student.demoAttendanceEnabled);
  els.studentAttendanceDemoBtn.dataset.active = enabled ? 'true' : 'false';
  els.studentAttendanceDemoBtn.setAttribute('aria-pressed', enabled ? 'true' : 'false');
  els.studentAttendanceDemoBtn.textContent = enabled
    ? 'Demo Attendance ON'
    : 'Demo Attendance OFF';
}

function normalizeTimeForMatch(value = '') {
  const token = String(value || '').trim();
  if (!token) {
    return '';
  }
  if (token.length >= 5) {
    return token.slice(0, 5);
  }
  return token;
}

function findMatchingRemedialMessageForSchedule(schedule = null) {
  if (!schedule) {
    return null;
  }
  const messages = Array.isArray(state.remedial.messages) ? state.remedial.messages : [];
  const candidates = messages.filter((row) => String(row?.remedial_code || '').trim());
  if (!candidates.length) {
    return null;
  }

  const targetCourse = String(schedule.course_code || '').trim().toUpperCase();
  const targetDate = String(schedule.class_date || '').trim();
  const targetStart = normalizeTimeForMatch(schedule.start_time);

  return (
    candidates.find((row) => (
      String(row?.course_code || '').trim().toUpperCase() === targetCourse
      && String(row?.class_date || '').trim() === targetDate
      && normalizeTimeForMatch(row?.start_time) === targetStart
    ))
    || candidates.find((row) => (
      String(row?.course_code || '').trim().toUpperCase() === targetCourse
      && String(row?.class_date || '').trim() === targetDate
    ))
    || candidates.find((row) => String(row?.course_code || '').trim().toUpperCase() === targetCourse)
    || candidates[0]
    || null
  );
}

async function openRemedialFromAttendance(kpi = null) {
  if (!authState.user || authState.user.role !== 'student') {
    throw new Error('Only students can access remedial attendance.');
  }
  const resolved = kpi || findAttendanceManagementState();
  setActiveModule('remedial', { updateHash: true });
  try {
    await refreshActiveModuleData();
  } catch (error) {
    log(error.message || 'Failed to refresh remedial module');
  }

  const matched = findMatchingRemedialMessageForSchedule(resolved?.schedule || null);
  const matchedCode = String(matched?.remedial_code || '').trim().toUpperCase();
  if (!matchedCode) {
    setRemedialStudentStatus('Opened Remedial module. Use code from Messages, validate, then mark attendance in first 15 minutes.');
    return;
  }

  try {
    await applyRemedialCodeFromMessage(matchedCode);
    setRemedialStudentStatus(`Code ${matchedCode} loaded from Messages. If window is open, tap "Mark Attendance".`);
  } catch (error) {
    setRemedialStudentStatus(`Code ${matchedCode} found, but validation failed: ${error.message}`, true);
  }
}

async function handleStudentMarkAttendanceAction() {
  const kpi = findEffectiveAttendanceManagementState();
  if (kpi.mode === 'demo') {
    await startStudentDemoAttendanceFlow(kpi);
    return;
  }
  if (isRemedialAttendanceWindow(kpi)) {
    await openRemedialFromAttendance(kpi);
    return;
  }
  await startStudentSelfieFlow();
}

function renderProfilePhotoPreview(photoDataUrl) {
  if (!els.profilePhotoPreview) {
    return;
  }
  if (!photoDataUrl) {
    els.profilePhotoPreview.classList.add('hidden');
    return;
  }
  els.profilePhotoPreview.src = photoDataUrl;
  els.profilePhotoPreview.classList.remove('hidden');
}

function renderStudentProfilePreview(photoDataUrl) {
  renderProfilePhotoPreview(photoDataUrl);
}

function renderFacultyProfilePreview(photoDataUrl) {
  renderProfilePhotoPreview(photoDataUrl);
}

function updateProfileSaveState() {
  if (!els.saveProfilePhotoBtn) {
    return;
  }
  const role = authState.user?.role;
  if (role !== 'student' && role !== 'faculty') {
    els.saveProfilePhotoBtn.disabled = true;
    return;
  }

  if (role === 'student') {
    const draftName = normalizeProfileName(els.profileFullName?.value || '');
    const existingName = normalizeProfileName(state.student.name || authState.user?.name || '');
    const hasName = hasValidProfileName(existingName || draftName);
    const draftRegistration = (els.profileRegistrationNumber?.value || '').trim().toUpperCase().replace(/\s+/g, '');
    const draftSection = (els.profileSectionInput?.value || '').trim().toUpperCase().replace(/\s+/g, '');
    const existingSection = state.student.section || '';
    const hasRegistration = Boolean(state.student.registrationNumber || draftRegistration);
    const hasSection = Boolean(existingSection || draftSection);
    const hasPhoto = Boolean(state.student.profilePhotoDataUrl || state.student.pendingProfilePhotoDataUrl);
    const hasNewName = hasValidProfileName(draftName) && draftName !== existingName;
    const hasNewReg = Boolean(draftRegistration) && draftRegistration !== (state.student.registrationNumber || '');
    const hasNewSection = Boolean(draftSection) && draftSection !== existingSection;
    const hasNewPhoto = Boolean(state.student.pendingProfilePhotoDataUrl)
      && state.student.pendingProfilePhotoDataUrl !== (state.student.profilePhotoDataUrl || '');
    const setupRequired = state.student.profileSetupRequired || requiresStudentProfileSetup();

    if (setupRequired) {
      els.saveProfilePhotoBtn.disabled = !(hasName && hasRegistration && hasSection && hasPhoto);
      return;
    }

    if (existingSection && hasNewSection) {
      els.saveProfilePhotoBtn.disabled = true;
      return;
    }

    els.saveProfilePhotoBtn.disabled = !(hasNewName || hasNewReg || hasNewPhoto || (!existingSection && hasNewSection));
    return;
  }

  const draftName = normalizeProfileName(els.profileFullName?.value || '');
  const existingName = normalizeProfileName(state.facultyProfile.name || authState.user?.name || '');
  const hasName = hasValidProfileName(existingName || draftName);
  const draftFacultyId = (els.profileRegistrationNumber?.value || '').trim().toUpperCase().replace(/\s+/g, '');
  const draftSection = (els.profileSectionInput?.value || '').trim().toUpperCase().replace(/\s+/g, '');
  const existingFacultyId = state.facultyProfile.facultyIdentifier || '';
  const existingSection = (state.facultyProfile.section || '').trim().toUpperCase().replace(/\s+/g, '');
  const hasFacultyId = Boolean(existingFacultyId || draftFacultyId);
  const hasSection = Boolean(existingSection || draftSection);
  const hasPhoto = Boolean(state.facultyProfile.profilePhotoDataUrl || state.facultyProfile.pendingProfilePhotoDataUrl);
  const hasNewName = hasValidProfileName(draftName) && draftName !== existingName;
  const hasNewFacultyId = Boolean(draftFacultyId) && draftFacultyId !== existingFacultyId;
  const hasNewSection = Boolean(draftSection) && draftSection !== existingSection;
  const hasNewPhoto = Boolean(state.facultyProfile.pendingProfilePhotoDataUrl)
    && state.facultyProfile.pendingProfilePhotoDataUrl !== (state.facultyProfile.profilePhotoDataUrl || '');
  const sectionLocked = Boolean(existingSection) && !state.facultyProfile.sectionCanUpdateNow;
  const setupRequired = state.facultyProfile.profileSetupRequired || requiresFacultyProfileSetup();

  if (setupRequired) {
    els.saveProfilePhotoBtn.disabled = !(hasName && hasFacultyId && hasSection && hasPhoto);
    return;
  }
  if (sectionLocked && hasNewSection) {
    els.saveProfilePhotoBtn.disabled = true;
    return;
  }
  els.saveProfilePhotoBtn.disabled = !(hasNewName || hasNewFacultyId || hasNewSection || hasNewPhoto);
}

function renderStudentProfileStatus() {
  if (!els.profileStatus) {
    return;
  }

  const draftName = normalizeProfileName(els.profileFullName?.value || '');
  const hasName = hasValidProfileName(state.student.name || authState.user?.name || draftName);
  const draftRegistration = (els.profileRegistrationNumber?.value || '').trim().toUpperCase().replace(/\s+/g, '');
  const draftSection = (els.profileSectionInput?.value || '').trim().toUpperCase().replace(/\s+/g, '');
  const existingSection = state.student.section || '';
  const hasRegistration = Boolean(state.student.registrationNumber || draftRegistration);
  const hasSection = Boolean(existingSection || draftSection);
  const hasPhoto = Boolean(state.student.profilePhotoDataUrl || state.student.pendingProfilePhotoDataUrl);
  const sectionEditAttempt = Boolean(existingSection) && Boolean(draftSection) && draftSection !== existingSection;

  if (!hasName && !hasRegistration && !hasSection && !hasPhoto) {
    els.profileStatus.textContent = 'Full name, registration number, section, and profile photo are required before continuing.';
    updateProfileSaveState();
    return;
  }
  if (!hasName) {
    els.profileStatus.textContent = 'Full name is required and can only be set once from profile setup.';
    updateProfileSaveState();
    return;
  }
  if (!hasRegistration && !hasSection && !hasPhoto) {
    els.profileStatus.textContent = 'Registration number, section, and profile photo are required before continuing.';
    updateProfileSaveState();
    return;
  }
  if (!hasRegistration) {
    els.profileStatus.textContent = 'Registration number is required and becomes permanent after save.';
    updateProfileSaveState();
    return;
  }
  if (!hasSection) {
    els.profileStatus.textContent = 'Section is required before continuing.';
    updateProfileSaveState();
    return;
  }
  if (!hasPhoto) {
    els.profileStatus.textContent = 'Profile photo is mandatory. Upload once to enable facial attendance.';
    updateProfileSaveState();
    return;
  }
  if (sectionEditAttempt) {
    if (state.student.sectionChangeRequiresFacultyApproval) {
      els.profileStatus.textContent = 'Section change requires faculty approval. Ask your faculty to approve the update.';
    } else {
      els.profileStatus.textContent = `Section change request window opens after ${formatLockDateTime(state.student.sectionLockedUntil)} (${formatRemainingMinutes(state.student.sectionLockMinutesRemaining)} remaining).`;
    }
    updateProfileSaveState();
    return;
  }

  if (state.student.profilePhotoCanUpdateNow) {
    els.profileStatus.textContent = 'Profile photo verified. You can update it now (next update lock: 14 days).';
  } else {
    els.profileStatus.textContent = 'Profile photo verified. Update is temporarily locked for security.';
  }
  updateProfileSaveState();
}

function renderFacultyProfileStatus() {
  if (!els.profileStatus) {
    return;
  }

  const draftName = normalizeProfileName(els.profileFullName?.value || '');
  const hasName = hasValidProfileName(state.facultyProfile.name || authState.user?.name || draftName);
  const draftFacultyId = (els.profileRegistrationNumber?.value || '').trim().toUpperCase().replace(/\s+/g, '');
  const draftSection = (els.profileSectionInput?.value || '').trim().toUpperCase().replace(/\s+/g, '');
  const hasFacultyId = Boolean(state.facultyProfile.facultyIdentifier || draftFacultyId);
  const hasSection = Boolean(state.facultyProfile.section || draftSection);
  const hasPhoto = Boolean(state.facultyProfile.profilePhotoDataUrl || state.facultyProfile.pendingProfilePhotoDataUrl);

  if (!hasName && !hasFacultyId && !hasSection && !hasPhoto) {
    els.profileStatus.textContent = 'Full name, faculty ID, section, and profile photo are required before continuing.';
    updateProfileSaveState();
    return;
  }
  if (!hasName) {
    els.profileStatus.textContent = 'Full name is required and can only be set once from profile setup.';
    updateProfileSaveState();
    return;
  }
  if (!hasFacultyId && !hasSection && !hasPhoto) {
    els.profileStatus.textContent = 'Faculty ID, section, and profile photo are required before continuing.';
    updateProfileSaveState();
    return;
  }
  if (!hasFacultyId) {
    els.profileStatus.textContent = 'Faculty ID is required and becomes permanent after save.';
    updateProfileSaveState();
    return;
  }
  if (!hasSection) {
    els.profileStatus.textContent = 'Section is required and can be updated every 24 hours after save.';
    updateProfileSaveState();
    return;
  }
  if (!hasPhoto) {
    els.profileStatus.textContent = 'Profile photo is mandatory for faculty verification.';
    updateProfileSaveState();
    return;
  }

  if (!state.facultyProfile.sectionCanUpdateNow) {
    els.profileStatus.textContent = `Section update locked. Try again in ${formatRemainingMinutes(state.facultyProfile.sectionLockMinutesRemaining)}.`;
    updateProfileSaveState();
    return;
  }
  if (state.facultyProfile.profilePhotoCanUpdateNow) {
    els.profileStatus.textContent = 'Faculty profile verified. Photo can be updated now (next lock: 14 days).';
  } else {
    els.profileStatus.textContent = 'Faculty profile verified. Photo update is temporarily locked for security.';
  }
  updateProfileSaveState();
}

function renderOwnerProfileStatus() {
  if (!els.profileStatus) {
    return;
  }
  const linkedShops = Array.isArray(state.food.shops) ? state.food.shops.length : 0;
  if (linkedShops > 0) {
    els.profileStatus.textContent = `Vendor profile linked to ${linkedShops} shop(s). Orders and shop controls stay scoped to your account.`;
  } else {
    els.profileStatus.textContent = 'Vendor profile is active. No shop assigned yet. Ask admin to map a shop to this vendor account.';
  }
  updateProfileSaveState();
}

function renderAdminProfileStatus() {
  if (!els.profileStatus) {
    return;
  }
  els.profileStatus.textContent = 'Admin account is active. Use Attendance module for approvals and schedule controls.';
  updateProfileSaveState();
}

function renderProfileStatusByRole() {
  if (authState.user?.role === 'faculty') {
    renderFacultyProfileStatus();
    return;
  }
  if (authState.user?.role === 'admin') {
    renderAdminProfileStatus();
    return;
  }
  if (authState.user?.role === 'owner') {
    renderOwnerProfileStatus();
    return;
  }
  renderStudentProfileStatus();
}

function resolveFoodPaymentError(error, fallback = 'Payment checkout failed. Please retry.') {
  const raw = String(error?.message || '').trim();
  if (!raw) {
    return fallback;
  }
  const lowered = raw.toLowerCase();
  if (lowered.includes('razorpay configuration is missing') || lowered.includes('razorpay is not configured')) {
    return 'Payments are not configured on server. Add active Razorpay keys (RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET or RAZORPAY_KEYRING_JSON + RAZORPAY_ACTIVE_KEY_ID) in backend env, then restart server.';
  }
  if (lowered.includes('razorpay order id was not returned')) {
    return 'Payment gateway did not return order id. Retry once, then verify Razorpay account/API keys.';
  }
  return raw;
}

async function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('Failed to read selected image file'));
    reader.readAsDataURL(file);
  });
}

async function loadCoursesMap() {
  const courses = await api('/core/courses');
  state.coursesById = {};
  for (const course of courses) {
    state.coursesById[course.id] = course;
  }
}

function getCourseLabel(courseId) {
  const course = state.coursesById[courseId];
  if (!course) {
    return `Course #${courseId}`;
  }
  return `${course.code} - ${course.title}`;
}

async function loadStudentProfilePhoto() {
  if (authState.user?.role !== 'student') {
    return;
  }

  const data = await api('/attendance/student/profile');
  state.student.name = normalizeProfileName(data.name || '');
  if (state.student.name) {
    authState.user.name = state.student.name;
  }
  state.student.registrationNumber = data.registration_number || '';
  state.student.section = (data.section || '').trim().toUpperCase().replace(/\s+/g, '');
  state.student.sectionUpdatedAt = data.section_updated_at || null;
  state.student.profilePhotoDataUrl = data.photo_data_url || '';
  state.student.profilePhotoCanUpdateNow = Boolean(data.can_update_photo_now);
  state.student.profilePhotoLockedUntil = data.photo_locked_until || null;
  state.student.profilePhotoLockDaysRemaining = Number(data.photo_lock_days_remaining || 0);
  state.student.sectionCanUpdateNow = Boolean(data.can_update_section_now);
  state.student.sectionLockedUntil = data.section_locked_until || null;
  state.student.sectionLockMinutesRemaining = Number(data.section_lock_minutes_remaining || 0);
  state.student.sectionChangeRequiresFacultyApproval = Boolean(data.section_change_requires_faculty_approval);
  state.student.profileLoaded = true;
  state.student.pendingProfilePhotoDataUrl = '';

  renderStudentProfilePreview(state.student.profilePhotoDataUrl);
  renderProfileStatusByRole();
  renderEnrollmentSummary();
  renderProfileSecurity();
  maybePromptProfileSetup();
  await loadStudentEnrollmentStatus();
  maybePromptEnrollmentSetup();
  if (state.student.timetable.length) {
    renderStudentTimetable();
  } else {
    updateSelectedClassState();
  }
}

async function loadStudentEnrollmentStatus() {
  if (authState.user?.role !== 'student') {
    return;
  }
  const data = await api('/attendance/student/enrollment-status');
  state.student.hasEnrollmentVideo = Boolean(data.has_enrollment_video);
  state.student.enrollmentCanUpdateNow = Boolean(data.can_update_now);
  state.student.enrollmentLockedUntil = data.locked_until || null;
  state.student.enrollmentLockDaysRemaining = Number(data.lock_days_remaining || 0);
  state.student.enrollmentUpdatedAt = data.enrollment_updated_at || null;
  state.student.enrollmentLoaded = true;
  if (els.enrollmentSaveBtn) {
    els.enrollmentSaveBtn.disabled = !state.student.enrollmentFrames.length || !state.student.enrollmentCanUpdateNow;
  }
  renderEnrollmentSummary();
}

async function loadFacultyProfile() {
  if (authState.user?.role !== 'faculty') {
    return;
  }

  const data = await api('/attendance/faculty/profile');
  state.facultyProfile.name = normalizeProfileName(data.name || '');
  if (state.facultyProfile.name) {
    authState.user.name = state.facultyProfile.name;
  }
  state.facultyProfile.facultyIdentifier = data.faculty_identifier || '';
  state.facultyProfile.section = (data.section || '').trim().toUpperCase().replace(/\s+/g, '');
  state.facultyProfile.sectionUpdatedAt = data.section_updated_at || null;
  state.facultyProfile.profilePhotoDataUrl = data.photo_data_url || '';
  state.facultyProfile.profilePhotoCanUpdateNow = Boolean(data.can_update_photo_now);
  state.facultyProfile.profilePhotoLockedUntil = data.photo_locked_until || null;
  state.facultyProfile.profilePhotoLockDaysRemaining = Number(data.photo_lock_days_remaining || 0);
  state.facultyProfile.sectionCanUpdateNow = Boolean(data.can_update_section_now);
  state.facultyProfile.sectionLockedUntil = data.section_locked_until || null;
  state.facultyProfile.sectionLockMinutesRemaining = Number(data.section_lock_minutes_remaining || 0);
  state.facultyProfile.pendingProfilePhotoDataUrl = '';
  state.facultyProfile.profileLoaded = true;

  renderFacultyProfilePreview(state.facultyProfile.profilePhotoDataUrl);
  renderProfileStatusByRole();
  renderProfileSecurity();
  maybePromptFacultyProfileSetup();
}

async function saveFacultyProfile() {
  const profileName = normalizeProfileName(els.profileFullName?.value || '');
  const existingName = normalizeProfileName(state.facultyProfile.name || authState.user?.name || '');
  const facultyIdentifier = (els.profileRegistrationNumber?.value || '').trim().toUpperCase().replace(/\s+/g, '');
  const section = (els.profileSectionInput?.value || '').trim().toUpperCase().replace(/\s+/g, '');
  const existingFacultyIdentifier = state.facultyProfile.facultyIdentifier || '';
  const existingSection = (state.facultyProfile.section || '').trim().toUpperCase().replace(/\s+/g, '');
  const nextPhotoDataUrl = state.facultyProfile.pendingProfilePhotoDataUrl || '';
  const hasNameAfterSave = hasValidProfileName(existingName || profileName);
  const hasNewName = hasValidProfileName(profileName) && profileName !== existingName;
  const hasNewFacultyIdentifier = Boolean(facultyIdentifier) && facultyIdentifier !== existingFacultyIdentifier;
  const hasNewSection = Boolean(section) && section !== existingSection;
  const hasNewPhoto = Boolean(nextPhotoDataUrl) && nextPhotoDataUrl !== state.facultyProfile.profilePhotoDataUrl;
  const setupRequired = state.facultyProfile.profileSetupRequired || requiresFacultyProfileSetup();
  const hasFacultyIdentifierAfterSave = Boolean(existingFacultyIdentifier || facultyIdentifier);
  const hasSectionAfterSave = Boolean(existingSection || section);
  const hasPhotoAfterSave = Boolean(state.facultyProfile.profilePhotoDataUrl || nextPhotoDataUrl);

  if (setupRequired) {
    if (!hasNameAfterSave) {
      throw new Error('Enter your full name before saving profile.');
    }
    if (!hasFacultyIdentifierAfterSave) {
      throw new Error('Enter your faculty ID before saving profile.');
    }
    if (!hasSectionAfterSave) {
      throw new Error('Enter section before saving profile.');
    }
    if (!hasPhotoAfterSave) {
      throw new Error('Upload profile photo before saving profile.');
    }
  }

  if (hasNewFacultyIdentifier && !existingFacultyIdentifier) {
    const confirmed = window.confirm(
      "Faculty ID is permanent and can't be changed without admin permissions later. Continue?"
    );
    if (!confirmed) {
      throw new Error('Faculty ID confirmation is required.');
    }
  }

  if (hasNewSection && existingSection && !state.facultyProfile.sectionCanUpdateNow) {
    showFacultySectionLockPopup();
    throw new Error(
      `Section is locked until ${formatLockDateTime(state.facultyProfile.sectionLockedUntil)} (${formatRemainingMinutes(state.facultyProfile.sectionLockMinutesRemaining)} remaining).`
    );
  }

  const payload = {};
  if (hasNewName || (!existingName && hasValidProfileName(profileName))) {
    payload.name = profileName;
  }
  if (hasNewFacultyIdentifier || (!existingFacultyIdentifier && facultyIdentifier)) {
    payload.faculty_identifier = facultyIdentifier;
  }
  if (hasNewSection || (!existingSection && section)) {
    payload.section = section;
  }
  if (hasNewPhoto || (!state.facultyProfile.profilePhotoDataUrl && nextPhotoDataUrl)) {
    payload.photo_data_url = nextPhotoDataUrl;
  }

  if (
    payload.photo_data_url
    && state.facultyProfile.profilePhotoDataUrl
    && !state.facultyProfile.profilePhotoCanUpdateNow
  ) {
    showFacultyProfilePhotoLockPopup();
    throw new Error(
      `Faculty profile photo locked until ${formatLockDateTime(state.facultyProfile.profilePhotoLockedUntil)}.`
    );
  }

  if (!Object.keys(payload).length) {
    if (setupRequired) {
      throw new Error('Add faculty ID, section, and profile photo before continuing.');
    }
    throw new Error('No profile changes to save.');
  }

  const originalButtonText = els.saveProfilePhotoBtn?.textContent || 'Save Profile';
  if (els.saveProfilePhotoBtn) {
    els.saveProfilePhotoBtn.disabled = true;
    els.saveProfilePhotoBtn.textContent = 'Saving...';
  }

  let saved;
  try {
    saved = await api('/attendance/faculty/profile', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  } finally {
    if (els.saveProfilePhotoBtn) {
      els.saveProfilePhotoBtn.textContent = originalButtonText;
    }
    updateProfileSaveState();
  }

  state.facultyProfile.facultyIdentifier = saved.faculty_identifier || state.facultyProfile.facultyIdentifier;
  state.facultyProfile.name = normalizeProfileName(saved.name || state.facultyProfile.name || existingName);
  authState.user.name = state.facultyProfile.name || authState.user.name;
  state.facultyProfile.section = (saved.section || '').trim().toUpperCase().replace(/\s+/g, '');
  state.facultyProfile.sectionUpdatedAt = saved.section_updated_at || null;
  state.facultyProfile.profilePhotoDataUrl = saved.photo_data_url || '';
  state.facultyProfile.profilePhotoCanUpdateNow = Boolean(saved.can_update_photo_now);
  state.facultyProfile.profilePhotoLockedUntil = saved.photo_locked_until || null;
  state.facultyProfile.profilePhotoLockDaysRemaining = Number(saved.photo_lock_days_remaining || 0);
  state.facultyProfile.sectionCanUpdateNow = Boolean(saved.can_update_section_now);
  state.facultyProfile.sectionLockedUntil = saved.section_locked_until || null;
  state.facultyProfile.sectionLockMinutesRemaining = Number(saved.section_lock_minutes_remaining || 0);
  state.facultyProfile.pendingProfilePhotoDataUrl = '';
  if (els.profilePhotoInput) {
    els.profilePhotoInput.value = '';
  }

  renderFacultyProfilePreview(state.facultyProfile.profilePhotoDataUrl);
  renderProfileStatusByRole();
  renderProfileSecurity();
  if (!requiresFacultyProfileSetup()) {
    if (els.profileStatus) {
      els.profileStatus.textContent = 'Faculty profile saved successfully.';
    }
    state.facultyProfile.profileSetupRequired = false;
    closeProfileModal();
  }
  log('Faculty profile updated');
}

async function saveStudentProfilePhoto() {
  const profileName = normalizeProfileName(els.profileFullName?.value || '');
  const existingName = normalizeProfileName(state.student.name || authState.user?.name || '');
  const registrationNumber = (els.profileRegistrationNumber?.value || '').trim().toUpperCase().replace(/\s+/g, '');
  const section = (els.profileSectionInput?.value || '').trim().toUpperCase().replace(/\s+/g, '');
  const existingRegistration = state.student.registrationNumber || '';
  const existingSection = state.student.section || '';
  const hasNewReg = Boolean(registrationNumber) && registrationNumber !== existingRegistration;
  const hasNewSection = Boolean(section) && section !== existingSection;
  const nextPhotoDataUrl = state.student.pendingProfilePhotoDataUrl || '';
  const hasNewPhoto = Boolean(nextPhotoDataUrl) && nextPhotoDataUrl !== state.student.profilePhotoDataUrl;
  const hasNewName = hasValidProfileName(profileName) && profileName !== existingName;
  const setupRequired = state.student.profileSetupRequired || requiresStudentProfileSetup();
  const hasNameAfterSave = hasValidProfileName(existingName || profileName);
  const hasRegistrationAfterSave = Boolean(existingRegistration || registrationNumber);
  const hasSectionAfterSave = Boolean(existingSection || section);
  const hasPhotoAfterSave = Boolean(state.student.profilePhotoDataUrl || nextPhotoDataUrl);

  if (setupRequired) {
    if (!hasNameAfterSave) {
      throw new Error('Enter your full name before saving profile.');
    }
    if (!hasRegistrationAfterSave) {
      throw new Error('Enter your registration number before saving profile.');
    }
    if (!hasSectionAfterSave) {
      throw new Error('Enter your section before saving profile.');
    }
    if (!hasPhotoAfterSave) {
      throw new Error('Upload profile photo before saving profile.');
    }
  }

  if (hasNewReg && !existingRegistration) {
    const confirmed = window.confirm(
      "Registration number is permanent and can't be changed without admin permissions later. Continue?"
    );
    if (!confirmed) {
      throw new Error('Registration number confirmation is required.');
    }
  }
  if (hasNewSection && existingSection) {
    if (state.student.sectionChangeRequiresFacultyApproval) {
      throw new Error('Section change requires faculty approval. Ask your faculty to approve the update.');
    }
    throw new Error(
      `Section change is locked until ${formatLockDateTime(state.student.sectionLockedUntil)} (${formatRemainingMinutes(state.student.sectionLockMinutesRemaining)} remaining).`
    );
  }

  const payload = {};
  if (hasNewName || (!existingName && hasValidProfileName(profileName))) {
    payload.name = profileName;
  }
  if (hasNewReg || (!existingRegistration && registrationNumber)) {
    payload.registration_number = registrationNumber;
  }
  if (hasNewSection || (!existingSection && section)) {
    payload.section = section;
  }
  if (hasNewPhoto || (!state.student.profilePhotoDataUrl && nextPhotoDataUrl)) {
    payload.photo_data_url = nextPhotoDataUrl;
  }

  if (
    payload.photo_data_url
    && state.student.profilePhotoDataUrl
    && !state.student.profilePhotoCanUpdateNow
  ) {
    showProfilePhotoLockPopup();
    throw new Error(
      `Profile photo locked until ${formatLockDateTime(state.student.profilePhotoLockedUntil)}.`
    );
  }

  if (!Object.keys(payload).length) {
    if (setupRequired) {
      throw new Error('Add registration number, section, and profile photo before continuing.');
    }
    throw new Error('No profile changes to save.');
  }

  const originalButtonText = els.saveProfilePhotoBtn?.textContent || 'Save Profile';
  if (els.saveProfilePhotoBtn) {
    els.saveProfilePhotoBtn.disabled = true;
    els.saveProfilePhotoBtn.textContent = 'Saving...';
  }

  let saved;
  try {
    saved = await api('/attendance/student/profile', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  } finally {
    if (els.saveProfilePhotoBtn) {
      els.saveProfilePhotoBtn.textContent = originalButtonText;
    }
    updateProfileSaveState();
  }

  state.student.registrationNumber = saved.registration_number || state.student.registrationNumber;
  state.student.name = normalizeProfileName(saved.name || state.student.name || existingName);
  authState.user.name = state.student.name || authState.user.name;
  state.student.section = (saved.section || '').trim().toUpperCase().replace(/\s+/g, '');
  state.student.sectionUpdatedAt = saved.section_updated_at || null;
  state.student.profilePhotoDataUrl = saved.photo_data_url || '';
  state.student.profilePhotoCanUpdateNow = Boolean(saved.can_update_photo_now);
  state.student.profilePhotoLockedUntil = saved.photo_locked_until || null;
  state.student.profilePhotoLockDaysRemaining = Number(saved.photo_lock_days_remaining || 0);
  state.student.sectionCanUpdateNow = Boolean(saved.can_update_section_now);
  state.student.sectionLockedUntil = saved.section_locked_until || null;
  state.student.sectionLockMinutesRemaining = Number(saved.section_lock_minutes_remaining || 0);
  state.student.sectionChangeRequiresFacultyApproval = Boolean(saved.section_change_requires_faculty_approval);
  state.student.pendingProfilePhotoDataUrl = '';
  if (els.profilePhotoInput) {
    els.profilePhotoInput.value = '';
  }
  renderStudentProfilePreview(state.student.profilePhotoDataUrl);
  renderProfileStatusByRole();
  renderEnrollmentSummary();
  renderProfileSecurity();
  if (state.student.timetable.length) {
    renderStudentTimetable();
  } else {
    updateSelectedClassState();
  }
  if (!requiresStudentProfileSetup()) {
    if (els.profileStatus) {
      els.profileStatus.textContent = 'Profile saved successfully. Redirecting to dashboard...';
    }
    state.student.profileSetupRequired = false;
    closeProfileModal();
    navigateSidebar('dashboard');
    try {
      await loadStudentEnrollmentStatus();
      maybePromptEnrollmentSetup();
    } catch (error) {
      log(error.message || 'Failed to load enrollment status');
    }
  }
  log('Student profile updated');
}

function getCalendarBounds(classes) {
  if (!classes.length) {
    return { startMinute: 8 * 60, endMinute: 18 * 60 };
  }

  const normalDurationClasses = classes.filter((item) => {
    const start = toMinutes(item.start_time);
    const end = toMinutes(item.end_time);
    const duration = end - start;
    return duration > 0 && duration <= 240;
  });
  const source = normalDurationClasses.length ? normalDurationClasses : classes;

  let minStart = Infinity;
  let maxEnd = -Infinity;
  for (const item of source) {
    const start = toMinutes(item.start_time);
    const end = toMinutes(item.end_time);
    minStart = Math.min(minStart, start);
    maxEnd = Math.max(maxEnd, end);
  }

  if (!Number.isFinite(minStart) || !Number.isFinite(maxEnd) || maxEnd <= minStart) {
    return { startMinute: 8 * 60, endMinute: 18 * 60 };
  }

  const startMinute = Math.max(6 * 60, Math.floor(minStart / 60) * 60);
  let endMinute = Math.min(22 * 60, Math.ceil(maxEnd / 60) * 60);
  if ((endMinute - startMinute) < 240) {
    endMinute = Math.min(22 * 60, startMinute + 240);
  }
  return {
    startMinute,
    endMinute: endMinute > startMinute ? endMinute : startMinute + 60,
  };
}

function updateSelectedClassState() {
  const hasProfileReady = Boolean(state.student.profilePhotoDataUrl) && Boolean(state.student.registrationNumber) && Boolean(state.student.section);
  const officialKpi = findAttendanceManagementState();
  const kpi = findEffectiveAttendanceManagementState();
  const scheduleId = Number(kpi.schedule?.schedule_id || 0);
  const remedialWindowOpen = isRemedialAttendanceWindow(officialKpi);
  const demoAttendanceActive = kpi.mode === 'demo';
  state.student.kpiScheduleId = demoAttendanceActive ? null : (scheduleId || null);
  renderStudentAttendanceDemoToggle();

  if (els.selectedClassLabel) {
    els.selectedClassLabel.textContent = kpi.headline;
  }
  if (els.attendanceKpiSubtitle) {
    if (demoAttendanceActive) {
      els.attendanceKpiSubtitle.textContent = `${kpi.subtitle} Verification runs end-to-end and does not save attendance data.`;
    } else if (!hasProfileReady) {
      els.attendanceKpiSubtitle.textContent = `${kpi.subtitle} Complete profile setup to enable official marking.`;
    } else if (kpi.mode === 'mark' && String(kpi.schedule?.class_kind || 'regular').toLowerCase() === 'remedial') {
      els.attendanceKpiSubtitle.textContent = `${kpi.subtitle} Use Remedial module with faculty code (15-minute window).`;
    } else {
      els.attendanceKpiSubtitle.textContent = kpi.subtitle;
    }
  }

  const isRegularMarkable = (
    officialKpi.mode === 'mark'
    && Number(officialKpi.schedule?.schedule_id || 0)
    && hasProfileReady
    && String(officialKpi.schedule?.class_kind || 'regular').toLowerCase() !== 'remedial'
  );
  if (els.takeSelfieBtn) {
    els.takeSelfieBtn.textContent = remedialWindowOpen
      ? 'Open Remedial Module'
      : (demoAttendanceActive ? 'Open Camera & Run Demo Attendance' : 'Open Camera & Mark Attendance');
    const demoReady = demoAttendanceActive && hasProfileReady && !requiresStudentEnrollmentSetup();
    els.takeSelfieBtn.disabled = !(isRegularMarkable || remedialWindowOpen || demoReady);
  }
}

function refreshStudentTimetableRealtimeStatus() {
  if (authState.user?.role !== 'student') {
    return;
  }
  const classes = state.student.timetable || [];
  if (!classes.length || !els.timetableGrid) {
    return;
  }
  const classBySchedule = new Map(classes.map((item) => [Number(item.schedule_id), item]));
  const cards = els.timetableGrid.querySelectorAll('.calendar-class[data-schedule-id]');
  if (!cards.length) {
    updateSelectedClassState();
    return;
  }

  for (const card of cards) {
    const scheduleId = Number(card.dataset.scheduleId || '0');
    const item = classBySchedule.get(scheduleId);
    if (!item) {
      continue;
    }
    const kpi = resolveTimetableKpi(item);
    card.classList.remove('slot-present', 'slot-absent', 'slot-upcoming', 'slot-mark', 'slot-open-window');
    const nextClasses = getSlotClass(item).split(' ').filter(Boolean);
    for (const className of nextClasses) {
      card.classList.add(className);
    }

    const badge = card.querySelector('.slot-status');
    if (badge) {
      badge.className = `slot-status ${kpi.key}`;
      badge.textContent = kpi.label;
    }

    const lines = slotTextLines(item);
    card.setAttribute(
      'aria-label',
      `${DAY_LABELS[item.weekday]}, ${formatTime24(item.start_time)} to ${formatTime24(item.end_time)}, ${lines.primary}, ${kpi.label}`
    );
  }

  updateSelectedClassState();
}

function renderStudentTimetable() {
  els.timetableGrid.innerHTML = '';
  const classes = state.student.timetable || [];
  if (!classes.length) {
    const emptyRow = buildEmptyStateRow({
      title: 'No classes found for this week.',
      description: 'Try switching week, or jump back to the current week timetable.',
      iconLabel: 'CLASS',
      ctaLabel: 'Go To Current Week',
      ctaClassName: 'btn btn-primary',
      onCta: () => {
        void ensureCurrentWeekTimetableVisible({ forceNetwork: true }).catch((error) => {
          log(error.message || 'Unable to load current week timetable.');
        });
      },
    });
    els.timetableGrid.appendChild(emptyRow);
    updateSelectedClassState();
    return;
  }
  const { startMinute, endMinute } = getCalendarBounds(classes);
  const rows = Math.max(1, Math.ceil((endMinute - startMinute) / 60));
  const currentDayIndex = weekdayFromWeekStart(state.student.weekStart);

  const calendar = document.createElement('div');
  calendar.className = 'weekly-calendar';
  calendar.setAttribute('role', 'grid');
  calendar.setAttribute('aria-label', 'Weekly class timetable');

  const corner = document.createElement('div');
  corner.className = 'calendar-corner';
  corner.style.gridColumn = '1';
  corner.style.gridRow = '1';
  corner.textContent = 'Time';
  calendar.appendChild(corner);

  if (Number.isInteger(currentDayIndex) && currentDayIndex >= 0 && currentDayIndex <= 6) {
    const dayBand = document.createElement('div');
    dayBand.className = 'calendar-day-band';
    dayBand.style.setProperty('--calendar-band-day', String(currentDayIndex));
    calendar.appendChild(dayBand);
  }

  for (let dayIndex = 0; dayIndex < 7; dayIndex += 1) {
    const header = document.createElement('div');
    header.className = 'calendar-day-header';
    header.setAttribute('role', 'columnheader');
    if (currentDayIndex === dayIndex) {
      header.classList.add('current-day');
      header.setAttribute('aria-current', 'date');
    }
    header.style.gridColumn = String(dayIndex + 2);
    header.style.gridRow = '1';
    header.textContent = DAY_LABELS[dayIndex];
    calendar.appendChild(header);
  }

  for (let row = 0; row < rows; row += 1) {
    const minuteMark = startMinute + row * 60;
    const label = document.createElement('div');
    label.className = 'calendar-time-label';
    label.setAttribute('role', 'rowheader');
    label.dataset.minute = String(minuteMark);
    label.style.gridColumn = '1';
    label.style.gridRow = String(row + 2);
    label.textContent = `${String(Math.floor(minuteMark / 60)).padStart(2, '0')}:00`;
    calendar.appendChild(label);

    for (let dayIndex = 0; dayIndex < 7; dayIndex += 1) {
      const cell = document.createElement('div');
      cell.className = 'calendar-cell';
      cell.setAttribute('role', 'gridcell');
      if (currentDayIndex === dayIndex) {
        cell.classList.add('current-day');
      }
      cell.style.gridColumn = String(dayIndex + 2);
      cell.style.gridRow = String(row + 2);
      calendar.appendChild(cell);
    }
  }

  for (const item of classes) {
    const start = toMinutes(item.start_time);
    const end = toMinutes(item.end_time);
    const rowStart = Math.max(0, Math.floor((start - startMinute) / 60));
    const rowSpan = Math.max(1, Math.ceil((end - start) / 60));
    const lines = slotTextLines(item);

    const card = document.createElement('div');
    card.className = `calendar-class ${getSlotClass(item)}`;
    if (currentDayIndex === item.weekday) {
      card.classList.add('current-day');
    }
    card.dataset.scheduleId = String(item.schedule_id);
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.setAttribute('aria-selected', String(item.schedule_id === state.student.selectedScheduleId));
    card.setAttribute(
      'aria-label',
      `${DAY_LABELS[item.weekday]}, ${formatTime24(item.start_time)} to ${formatTime24(item.end_time)}, ${lines.primary}`
    );
    card.style.gridColumn = String(item.weekday + 2);
    card.style.gridRow = `${rowStart + 2} / span ${rowSpan}`;

    if (item.schedule_id === state.student.selectedScheduleId) {
      card.classList.add('selected');
    }

    const time = document.createElement('p');
    time.className = 'calendar-time';
    time.textContent = `${formatTime24(item.start_time)} - ${formatTime24(item.end_time)}`;
    card.appendChild(time);

    const course = document.createElement('p');
    course.className = 'calendar-course';
    course.textContent = lines.primary;
    card.appendChild(course);

    if (lines.secondary) {
      const room = document.createElement('p');
      room.className = 'calendar-room';
      room.textContent = lines.secondary;
      card.appendChild(room);
    }

    const metaRow = document.createElement('div');
    metaRow.className = 'calendar-meta-row';

    const kpi = resolveTimetableKpi(item);
    const slotState = document.createElement('span');
    slotState.className = `slot-status ${kpi.key}`;
    slotState.textContent = kpi.label;
    metaRow.appendChild(slotState);

    card.appendChild(metaRow);

    calendar.appendChild(card);
  }

  if (Number.isInteger(currentDayIndex) && currentDayIndex >= 0 && currentDayIndex <= 6) {
    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();
    const maxMinute = startMinute + rows * 60;
    if (nowMinutes >= startMinute && nowMinutes <= maxMinute) {
      const nowLine = document.createElement('div');
      nowLine.className = 'calendar-now-line';
      const rowProgress = Math.max(0, Math.min(rows, (nowMinutes - startMinute) / 60));
      nowLine.style.setProperty('--calendar-now-day', String(currentDayIndex));
      nowLine.style.setProperty('--calendar-now-progress', String(rowProgress));
      calendar.appendChild(nowLine);
    }
  }

  els.timetableGrid.appendChild(calendar);
  updateSelectedClassState();
  focusTimetableContext({ smooth: true });
}

function focusTimetableContext({ smooth = true } = {}) {
  const container = els.timetableGrid;
  const behavior = smooth ? 'smooth' : 'auto';
  if (!container) {
    return;
  }

  const selectedCard = state.student.selectedScheduleId
    ? container.querySelector(`.calendar-class[data-schedule-id="${state.student.selectedScheduleId}"]`)
    : null;
  const openCard = container.querySelector('.calendar-class.slot-open-window.current-day, .calendar-class.slot-open-window');
  const currentDayHeader = container.querySelector('.calendar-day-header.current-day');
  const target = selectedCard || openCard || currentDayHeader;

  if (target) {
    target.scrollIntoView({ block: 'nearest', inline: 'center', behavior });
  }

  const currentDayIndex = weekdayFromWeekStart(state.student.weekStart);
  if (currentDayIndex === null) {
    return;
  }

  const now = new Date();
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  const labels = [...container.querySelectorAll('.calendar-time-label[data-minute]')];
  if (!labels.length) {
    return;
  }
  let best = labels[0];
  let bestDelta = Number.POSITIVE_INFINITY;
  for (const row of labels) {
    const minute = Number(row.dataset.minute || '0');
    const delta = Math.abs(minute - nowMinutes);
    if (delta < bestDelta) {
      best = row;
      bestDelta = delta;
    }
  }

  const targetTop = Math.max(0, best.offsetTop - Math.round(container.clientHeight * 0.28));
  container.scrollTo({ top: targetTop, behavior });
}

function renderTimetableViewInfo() {
  if (!els.timetableViewInfo) {
    return;
  }

  const weekStartRaw = state.student.weekStart || weekStartISO(state.student.viewDate || els.weekStartDate?.value || todayISO());
  const weekEndRaw = shiftISODate(weekStartRaw, 6);
  const weekStartText = parseISODateLocal(weekStartRaw).toLocaleDateString();
  const weekEndText = parseISODateLocal(weekEndRaw).toLocaleDateString();
  const minWeekStartRaw = weekStartISO(String(state.student.minTimetableDate || STUDENT_TIMETABLE_START_DATE));
  els.timetableViewInfo.textContent = `Week ${weekStartText} - ${weekEndText}`;

  if (els.prevWeekBtn) {
    els.prevWeekBtn.disabled = weekStartRaw <= minWeekStartRaw;
  }
}

async function ensureCurrentWeekTimetableVisible(options = {}) {
  const { forceNetwork = true } = options;
  if (authState.user?.role !== 'student') {
    return;
  }
  const today = clampStudentViewDate(todayISO());
  state.student.viewDate = today;
  if (els.weekStartDate) {
    els.weekStartDate.value = today;
  }
  await loadStudentTimetable({ forceNetwork });
}

function cacheTimetableWeekPayload(weekStart, payload) {
  if (!weekStart || !payload) {
    return;
  }
  state.student.timetableCache[weekStart] = {
    week_start: payload.week_start || weekStart,
    classes: payload.classes || [],
    cached_at: Date.now(),
  };
}

async function fetchStudentTimetableWeek(weekStart, options = {}) {
  const { forceNetwork = true } = options;
  if (!weekStart) {
    throw new Error('Week start is required.');
  }

  const cached = state.student.timetableCache[weekStart];
  if (cached && !forceNetwork) {
    return cached;
  }

  const requestKey = `${weekStart}:${forceNetwork ? 'network' : 'default'}`;
  const existingRequest = state.student.timetableNetworkRequests.get(requestKey);
  if (existingRequest) {
    return existingRequest;
  }

  const request = (async () => {
    const payload = await api(`/attendance/student/timetable?week_start=${weekStart}`);
    cacheTimetableWeekPayload(payload.week_start || weekStart, payload);
    return payload;
  })().finally(() => {
    state.student.timetableNetworkRequests.delete(requestKey);
  });

  state.student.timetableNetworkRequests.set(requestKey, request);
  return request;
}

function applyStudentTimetablePayload(payload) {
  if (payload?.min_navigable_date) {
    state.student.minTimetableDate = String(payload.min_navigable_date);
  }
  state.student.weekStart = payload.week_start;
  state.student.timetable = payload.classes || [];
  const payloadWeekStart = weekStartISO(payload.week_start || todayISO());
  const currentWeekStart = weekStartISO(todayISO());
  if (payloadWeekStart === currentWeekStart) {
    state.student.kpiTimetable = payload.classes || [];
  }

  const hasSelected = state.student.timetable.some((item) => item.schedule_id === state.student.selectedScheduleId);
  if (!hasSelected) {
    const fallback = pickStudentFallbackSchedule();
    state.student.selectedScheduleId = fallback ? fallback.schedule_id : null;
  }

  if (!state.student.timetable.length) {
    setStudentResult('No classes found for this week.');
  }

  renderTimetableViewInfo();
  renderStudentTimetable();
}

function renderTimetableLoadError(message) {
  if (!els.timetableGrid) {
    return;
  }
  const safe = escapeHtml(message || 'Unable to load timetable right now.');
  els.timetableGrid.innerHTML = `<div class="list-item warn">${safe}</div>`;
}

async function prefetchStudentTimetableWeek(weekStart) {
  if (authState.user?.role !== 'student' || !weekStart) {
    return;
  }
  if (state.student.timetableCache[weekStart]) {
    return;
  }
  if (state.student.timetablePrefetching.has(weekStart)) {
    return;
  }

  state.student.timetablePrefetching.add(weekStart);
  try {
    await fetchStudentTimetableWeek(weekStart, { forceNetwork: true });
  } catch (_) {
    // Keep prefetch best-effort only.
  } finally {
    state.student.timetablePrefetching.delete(weekStart);
  }
}

function prefetchAdjacentStudentWeeks(weekStart) {
  if (!weekStart) {
    return;
  }
  const minWeekStart = weekStartISO(state.student.minTimetableDate || STUDENT_TIMETABLE_START_DATE);
  const prevWeek = shiftISODate(weekStart, -7);
  if (prevWeek >= minWeekStart) {
    void prefetchStudentTimetableWeek(prevWeek);
  }
  void prefetchStudentTimetableWeek(shiftISODate(weekStart, 7));
}

async function refreshStudentKpiTimetable(options = {}) {
  const { forceNetwork = false } = options;
  if (authState.user?.role !== 'student') {
    return;
  }

  const currentWeekStart = weekStartISO(todayISO());
  const cached = state.student.timetableCache[currentWeekStart];
  if (cached && !forceNetwork) {
    state.student.kpiTimetable = cached.classes || [];
    return;
  }

  const viewWeekStart = weekStartISO(els.weekStartDate?.value || state.student.viewDate || todayISO());
  if (!forceNetwork && viewWeekStart === currentWeekStart && Array.isArray(state.student.timetable)) {
    state.student.kpiTimetable = state.student.timetable;
    return;
  }

  if (state.student.kpiRefreshInFlight) {
    return;
  }
  state.student.kpiRefreshInFlight = true;
  try {
    const payload = await fetchStudentTimetableWeek(currentWeekStart, { forceNetwork: true });
    state.student.kpiTimetable = payload.classes || [];
  } catch (_) {
    if (cached) {
      state.student.kpiTimetable = cached.classes || [];
    }
  } finally {
    state.student.kpiRefreshInFlight = false;
    updateSelectedClassState();
  }
}

async function loadStudentTimetable(options = {}) {
  const { forceNetwork = false, skipRepair = false } = options;
  if (authState.user?.role !== 'student') {
    return;
  }

  const rawViewDate = els.weekStartDate.value || state.student.viewDate || todayISO();
  const viewDate = clampStudentViewDate(rawViewDate);
  els.weekStartDate.value = viewDate;
  state.student.viewDate = viewDate;
  const weekStart = weekStartISO(viewDate);
  const currentWeekStart = weekStartISO(todayISO());
  const requestToken = ++state.student.timetableRequestToken;
  const cached = state.student.timetableCache[weekStart];

  if (cached) {
    applyStudentTimetablePayload(cached);
    prefetchAdjacentStudentWeeks(state.student.weekStart || weekStart);
    if (!forceNetwork && weekStart !== currentWeekStart) {
      return;
    }
  }

  let payload;
  try {
    payload = await fetchStudentTimetableWeek(weekStart, { forceNetwork: true });
  } catch (error) {
    if (cached) {
      return;
    }
    renderTimetableLoadError(error.message || 'Failed to load timetable.');
    setStudentResult(error.message || 'Failed to load timetable.');
    throw error;
  }

  if (requestToken !== state.student.timetableRequestToken) {
    return;
  }

  if (!skipRepair && (!payload.classes || payload.classes.length === 0) && !state.student.timetableRepairInFlight) {
    state.student.timetableRepairInFlight = true;
    try {
      await api('/attendance/student/default-timetable', { method: 'POST' });
      const repairedPayload = await fetchStudentTimetableWeek(weekStart, { forceNetwork: true });
      if (requestToken !== state.student.timetableRequestToken) {
        return;
      }
      applyStudentTimetablePayload(repairedPayload);
      prefetchAdjacentStudentWeeks(state.student.weekStart || weekStart);
      return;
    } catch (repairError) {
      log(`Timetable auto-repair failed: ${repairError.message || 'unknown error'}`);
      renderTimetableLoadError(repairError.message || 'Timetable could not be loaded.');
      setStudentResult(repairError.message || 'Timetable could not be loaded.');
      throw repairError;
    } finally {
      state.student.timetableRepairInFlight = false;
    }
  }

  applyStudentTimetablePayload(payload);
  prefetchAdjacentStudentWeeks(state.student.weekStart || weekStart);
  if (weekStart !== currentWeekStart) {
    void refreshStudentKpiTimetable({ forceNetwork: true }).then(() => {
      updateSelectedClassState();
    });
  }
}

async function refreshStudentTimetableSurface(options = {}) {
  const { forceNetwork = true } = options;
  await loadStudentTimetable({ forceNetwork });
  const currentWeekStart = weekStartISO(todayISO());
  const activeWeekStart = weekStartISO(state.student.weekStart || state.student.viewDate || todayISO());
  if (activeWeekStart !== currentWeekStart) {
    await refreshStudentKpiTimetable({ forceNetwork });
  } else {
    state.student.kpiTimetable = Array.isArray(state.student.timetable) ? state.student.timetable : [];
    updateSelectedClassState();
  }
}

function formatSaarthiDateTime(rawValue) {
  const parsed = new Date(rawValue);
  if (Number.isNaN(parsed.getTime())) {
    return '--';
  }
  return parsed.toLocaleString([], {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function looksLikeSaarthiTailFragment(text) {
  const cleaned = String(text || '').trim();
  if (!cleaned) {
    return false;
  }
  if (/['"`(\[{\/\-\s]$/.test(cleaned)) {
    return true;
  }
  const tokens = cleaned.match(/[A-Za-z0-9']+/g) || [];
  if (!tokens.length) {
    return true;
  }
  const connectorTokens = new Set([
    'and',
    'because',
    'but',
    'if',
    'so',
    'that',
    'then',
    'though',
    'to',
    'when',
    'while',
    'which',
    'who',
  ]);
  const leadToken = tokens[0].toLowerCase();
  const tailToken = tokens[tokens.length - 1].toLowerCase();
  if (tokens.length === 1 && !/[.!?]$/.test(cleaned)) {
    return true;
  }
  if (connectorTokens.has(tailToken)) {
    return true;
  }
  if (tokens.length <= 2 && ['i', 'you', 'we', 'they', 'he', 'she', 'it', 'this', 'that'].includes(leadToken)) {
    return true;
  }
  return false;
}

function sanitizeSaarthiMessageText(rawValue) {
  const cleaned = String(rawValue || '').replace(/\s+/g, ' ').trim();
  if (!cleaned) {
    return '';
  }
  const lastTerminalIdx = Math.max(cleaned.lastIndexOf('.'), cleaned.lastIndexOf('!'), cleaned.lastIndexOf('?'));
  if (lastTerminalIdx >= 0 && lastTerminalIdx < cleaned.length - 1) {
    const tail = cleaned.slice(lastTerminalIdx + 1).trim();
    if (looksLikeSaarthiTailFragment(tail)) {
      return cleaned.slice(0, lastTerminalIdx + 1).trim();
    }
  } else if (looksLikeSaarthiTailFragment(cleaned)) {
    return cleaned.replace(/['"`(\[{\/\-\s]+$/g, '').trim();
  }
  return cleaned;
}

function setSaarthiStatus(message, uiState = 'neutral') {
  state.student.saarthiUiMessage = String(message || '');
  state.student.saarthiUiState = normalizeUiState(uiState);
  if (!els.saarthiStatus) {
    return;
  }
  setUiStateMessage(els.saarthiStatus, state.student.saarthiUiMessage, {
    state: state.student.saarthiUiState,
  });
}

function isSaarthiAttendanceRow(row = {}, courseCode = '') {
  const codeValue = String(courseCode || row?.course_code || '').trim().toUpperCase();
  const sourceValue = String(row?.source || '').trim().toLowerCase();
  return codeValue === 'CON111' || sourceValue.startsWith('saarthi');
}

function formatAttendanceDetailTimeRange(row = {}, courseCode = '') {
  if (isSaarthiAttendanceRow(row, courseCode)) {
    const sourceValue = String(row?.source || '').trim().toLowerCase();
    if (sourceValue.includes('missed')) {
      return 'Mandatory Sunday counselling missed';
    }
    return 'Weekly 1-hour counselling credit';
  }
  return `${formatTime24(row?.start_time)}-${formatTime24(row?.end_time)}`;
}

function renderSaarthiPanel() {
  if (!els.studentSaarthiCard) {
    return;
  }

  const status = state.student.saarthiStatus && typeof state.student.saarthiStatus === 'object'
    ? state.student.saarthiStatus
    : null;
  const messages = Array.isArray(state.student.saarthiMessages) ? state.student.saarthiMessages : [];

  if (els.saarthiMandatoryDate) {
    if (status?.mandatory_date) {
      els.saarthiMandatoryDate.textContent = parseISODateLocal(status.mandatory_date).toLocaleDateString([], {
        weekday: 'short',
        day: '2-digit',
        month: 'short',
      });
    } else {
      els.saarthiMandatoryDate.textContent = '--';
    }
  }

  if (els.saarthiWeeklyCredit) {
    if (status?.session_completed_for_week) {
      els.saarthiWeeklyCredit.textContent = '1 hour credited';
    } else if (status?.mandatory_date) {
      els.saarthiWeeklyCredit.textContent = 'Pending Sunday';
    } else {
      els.saarthiWeeklyCredit.textContent = 'Pending';
    }
  }

  const transientUiState = normalizeUiState(state.student.saarthiUiState || 'neutral');
  const preferTransientMessage = transientUiState === 'loading' || transientUiState === 'error';
  const uiMessage = preferTransientMessage
    ? (state.student.saarthiUiMessage || status?.status_message || 'Saarthi session will appear here.')
    : (status?.status_message || state.student.saarthiUiMessage || 'Saarthi session will appear here.');
  const uiState = preferTransientMessage
    ? transientUiState
    : (
      status
        ? (status.session_completed_for_week ? 'success' : 'neutral')
        : transientUiState
    );
  setSaarthiStatus(uiMessage, uiState);

  if (els.saarthiHistory) {
    els.saarthiHistory.classList.toggle('is-empty', !messages.length);
    const typingMarkup = state.student.saarthiSending
      ? `
        <article class="saarthi-typing" role="status" aria-live="polite">
          <span class="saarthi-typing-label">Saarthi is thinking</span>
          <span class="saarthi-typing-dots" aria-hidden="true">
            <i></i><i></i><i></i>
          </span>
        </article>
      `
      : '';
    if (!messages.length) {
      els.saarthiHistory.innerHTML = `
        <div class="saarthi-empty">No chat this week yet. Your Sunday check-in here is mandatory for CON111 attendance.</div>
        ${typingMarkup}
      `;
    } else {
      const chatMarkup = messages.map((row, index) => {
        const senderRole = String(row?.sender_role || '').trim().toLowerCase();
        const mine = senderRole === 'student';
        const senderLabel = mine ? 'You' : 'Saarthi';
        const rawMessage = String(row?.message || '');
        const messageText = mine ? rawMessage : sanitizeSaarthiMessageText(rawMessage);
        const enterDelayMs = Math.min(index * 36, 220);
        return `
          <article class="saarthi-message ${mine ? 'mine' : 'theirs'}" style="animation-delay:${enterDelayMs}ms">
            <div class="saarthi-message-header">
              <strong class="saarthi-message-sender">${escapeHtml(senderLabel)}</strong>
              <span>${escapeHtml(formatSaarthiDateTime(row?.created_at))}</span>
            </div>
            <p class="saarthi-message-text">${escapeHtml(messageText)}</p>
          </article>
        `;
      }).join('');
      els.saarthiHistory.innerHTML = `${chatMarkup}${typingMarkup}`;
    }
    els.saarthiHistory.scrollTop = els.saarthiHistory.scrollHeight;
  }

  if (els.saarthiComposeInput) {
    const busy = state.student.saarthiSending || state.student.saarthiResetting;
    els.saarthiComposeInput.disabled = busy || authState.user?.role !== 'student';
  }
  if (els.saarthiSendBtn) {
    const sending = state.student.saarthiSending;
    const resetting = state.student.saarthiResetting;
    const busy = sending || resetting;
    const canUseSaarthi = authState.user?.role === 'student';
    const sendText = els.saarthiSendBtn.querySelector('.saarthi-send-text');
    els.saarthiSendBtn.disabled = busy || !canUseSaarthi;
    els.saarthiSendBtn.classList.toggle('is-sending', sending);
    els.saarthiSendBtn.setAttribute('aria-label', sending ? 'Sending message to Saarthi' : 'Send message to Saarthi');
    if (sendText) {
      sendText.textContent = sending ? 'Sending message' : 'Send message';
    }
  }
  if (els.saarthiNewChatBtn) {
    const canUseSaarthi = authState.user?.role === 'student';
    const resetting = state.student.saarthiResetting;
    const hasMessages = messages.length > 0;
    els.saarthiNewChatBtn.disabled = !canUseSaarthi || state.student.saarthiSending || resetting || !hasMessages;
    els.saarthiNewChatBtn.classList.toggle('is-loading', resetting);
    els.saarthiNewChatBtn.textContent = resetting ? 'Starting...' : 'New chat';
  }
}

async function loadSaarthiStatus({ silent = false } = {}) {
  if (authState.user?.role !== 'student') {
    state.student.saarthiStatus = null;
    state.student.saarthiMessages = [];
    setSaarthiStatus('Saarthi is available for students only.', 'neutral');
    renderSaarthiPanel();
    return null;
  }

  if (!silent) {
    setSaarthiStatus('Loading Saarthi session...', 'loading');
    renderSaarthiPanel();
  }

  const payload = await api('/saarthi/status');
  state.student.saarthiStatus = payload && typeof payload === 'object' ? payload : null;
  state.student.saarthiMessages = Array.isArray(payload?.messages) ? payload.messages : [];
  setSaarthiStatus(
    payload?.status_message || 'Saarthi session loaded.',
    payload?.session_completed_for_week ? 'success' : 'neutral',
  );
  renderSaarthiPanel();
  return payload;
}

async function sendSaarthiMessage() {
  if (authState.user?.role !== 'student') {
    throw new Error('Only students can use Saarthi.');
  }

  const message = String(els.saarthiComposeInput?.value || '').trim();
  if (!message) {
    throw new Error('Type your message to Saarthi first.');
  }

  state.student.saarthiSending = true;
  setSaarthiStatus('Sending message to Saarthi...', 'loading');
  renderSaarthiPanel();

  try {
    const payload = await api('/saarthi/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
    const session = payload && typeof payload === 'object' ? payload.session || null : null;
    if (els.saarthiComposeInput) {
      els.saarthiComposeInput.value = '';
    }
    state.student.saarthiStatus = session;
    state.student.saarthiMessages = Array.isArray(session?.messages) ? session.messages : [];
    setSaarthiStatus(
      session?.status_message || 'Saarthi session updated.',
      payload?.attendance_awarded_now ? 'success' : 'neutral',
    );
    renderSaarthiPanel();

    if (payload?.attendance_awarded_now) {
      try {
        await loadStudentAttendanceInsights();
      } catch (error) {
        log(error.message || 'Attendance ledger refresh failed after Saarthi credit was applied.');
      }
    }
    return payload;
  } catch (error) {
    setSaarthiStatus(error.message || 'Failed to send message to Saarthi.', 'error');
    renderSaarthiPanel();
    throw error;
  } finally {
    state.student.saarthiSending = false;
    renderSaarthiPanel();
  }
}

async function startNewSaarthiChat() {
  if (authState.user?.role !== 'student') {
    throw new Error('Only students can use Saarthi.');
  }

  if (!Array.isArray(state.student.saarthiMessages) || state.student.saarthiMessages.length === 0) {
    setSaarthiStatus('This week already has a fresh Saarthi chat.', 'neutral');
    renderSaarthiPanel();
    return null;
  }

  state.student.saarthiResetting = true;
  setSaarthiStatus('Starting a new Saarthi chat...', 'loading');
  renderSaarthiPanel();

  try {
    const payload = await api('/saarthi/new-chat', { method: 'POST' });
    state.student.saarthiStatus = payload && typeof payload === 'object' ? payload : null;
    state.student.saarthiMessages = Array.isArray(payload?.messages) ? payload.messages : [];
    if (els.saarthiComposeInput) {
      els.saarthiComposeInput.value = '';
    }
    setSaarthiStatus(payload?.status_message || 'Started a new Saarthi chat.', 'success');
    renderSaarthiPanel();
    return payload;
  } catch (error) {
    setSaarthiStatus(error.message || 'Failed to start a new Saarthi chat.', 'error');
    renderSaarthiPanel();
    throw error;
  } finally {
    state.student.saarthiResetting = false;
    renderSaarthiPanel();
  }
}

function renderStudentAttendanceAggregate() {
  const aggregate = state.student.attendanceAggregate;
  if (!aggregate) {
    els.studentAggregatePercent.textContent = '0%';
    els.studentAttendedDelivered.textContent = '0 / 0';
    els.studentAggregateCourses.innerHTML = '<div class="list-item">No attendance aggregate yet.</div>';
    closeAttendanceDetailsModal();
    return;
  }

  els.studentAggregatePercent.textContent = `${Number(aggregate.aggregate_percent || 0).toFixed(1)}%`;
  els.studentAttendedDelivered.textContent = `${aggregate.attended_total || 0} / ${aggregate.delivered_total || 0}`;

  const rows = aggregate.courses || [];
  if (!rows.length) {
    els.studentAggregateCourses.innerHTML = '<div class="list-item">No course attendance records yet.</div>';
    closeAttendanceDetailsModal();
    return;
  }

  const historyByCourse = state.student.attendanceHistoryByCourse || {};
  const markup = rows
    .map((row) => {
      const last = row.last_attended_on ? new Date(row.last_attended_on).toLocaleDateString('en-GB') : 'N/A';
      const percent = Number(row.attendance_percent || 0);
      const tone = percent >= 75 ? 'good' : percent >= 50 ? 'mid' : 'low';
      const courseKey = attendanceCourseKey(row.course_code, row.course_title);
      const detailsCount = (historyByCourse[courseKey] || []).length;
      const detailsLabel = detailsCount === 1 ? '1 class record' : `${detailsCount} class records`;
      return `
        <article
          class="course-aggregate-item course-clickable ${tone}"
          role="button"
          tabindex="0"
          data-course-key="${escapeHtml(courseKey)}"
          aria-label="Open attendance details for ${escapeHtml(row.course_code)}"
        >
          <div class="course-aggregate-head">
            <h4>${escapeHtml(row.course_code)} - ${escapeHtml(row.course_title)}</h4>
            <span class="course-percent-badge ${tone}">${percent.toFixed(1)}%</span>
          </div>
          <p>Faculty: ${escapeHtml(row.faculty_name)} | Last Attended: ${escapeHtml(last)}</p>
          <p>Attended/Delivered: ${row.attended_classes} / ${row.delivered_classes}</p>
          <p class="course-card-hint">${escapeHtml(detailsLabel)} • Click to view</p>
        </article>
      `;
    })
    .join('');

  els.studentAggregateCourses.innerHTML = markup;

  if (state.student.attendanceDetailsCourseKey) {
    const stillAvailable = rows.some(
      (row) => attendanceCourseKey(row.course_code, row.course_title) === state.student.attendanceDetailsCourseKey
    );
    if (stillAvailable) {
      renderAttendanceDetailsModal(state.student.attendanceDetailsCourseKey);
    } else {
      closeAttendanceDetailsModal();
    }
  }
}

function recoveryRiskTone(level) {
  const value = String(level || '').trim().toLowerCase();
  if (value === 'critical') {
    return 'critical';
  }
  if (value === 'high') {
    return 'high';
  }
  return 'watch';
}

function recoveryPlanStatusTone(status) {
  const value = String(status || '').trim().toLowerCase();
  if (value === 'recovered') {
    return 'completed';
  }
  if (value === 'escalated') {
    return 'critical';
  }
  return 'pending';
}

function recoveryActionTone(status) {
  const value = String(status || '').trim().toLowerCase();
  if (value === 'completed') {
    return 'completed';
  }
  if (value === 'acknowledged') {
    return 'acknowledged';
  }
  return 'pending';
}

function isVisibleRecoveryAction(action) {
  const status = String(action?.status || '').trim().toLowerCase();
  return status !== 'cancelled' && status !== 'skipped';
}

function formatRecoveryDateTime(value) {
  const text = String(value || '').trim();
  if (!text) {
    return 'No due date';
  }
  const stamp = Date.parse(text);
  if (Number.isNaN(stamp)) {
    return text;
  }
  return new Date(stamp).toLocaleString();
}

function buildRecoveryActionButtons(action) {
  const status = String(action?.status || '').trim().toLowerCase();
  if (status === 'completed' || status === 'cancelled' || status === 'skipped') {
    return '';
  }
  if (status === 'acknowledged') {
    return `
      <div class="recovery-action-buttons">
        <button class="btn btn-primary" type="button" data-recovery-action-command="complete" data-recovery-action-id="${Number(action.id || 0)}">
          Mark Complete
        </button>
      </div>
    `;
  }
  return `
    <div class="recovery-action-buttons">
      <button class="btn" type="button" data-recovery-action-command="acknowledge" data-recovery-action-id="${Number(action.id || 0)}">
        Acknowledge
      </button>
      <button class="btn btn-primary" type="button" data-recovery-action-command="complete" data-recovery-action-id="${Number(action.id || 0)}">
        Mark Complete
      </button>
    </div>
  `;
}

function renderStudentRecoveryPlans() {
  if (!els.studentRecoveryPlans) {
    return;
  }
  const plans = Array.isArray(state.student.recoveryPlans) ? state.student.recoveryPlans : [];
  if (!plans.length) {
    els.studentRecoveryPlans.innerHTML = '<div class="recovery-empty">No active recovery plan. If attendance risk builds up, guided interventions will appear here automatically.</div>';
    return;
  }

  els.studentRecoveryPlans.innerHTML = plans.map((plan) => {
    const riskTone = recoveryRiskTone(plan.risk_level);
    const visibleActions = Array.isArray(plan.actions)
      ? plan.actions.filter((action) => isVisibleRecoveryAction(action))
      : [];
    const studentActions = visibleActions
      ? visibleActions.filter((action) => String(action?.recipient_role || '').trim().toLowerCase() === 'student')
      : [];
    const supportSignals = visibleActions.filter((action) => String(action?.recipient_role || '').trim().toLowerCase() !== 'student');
    const supportText = supportSignals.length
      ? supportSignals.map((action) => action.title || statusLabel(action.action_type || action.recipient_role || 'support')).join(' | ')
      : 'Faculty intervention is ready when needed.';
    const suggestedClass = plan.recommended_makeup_class;
    const suggestedClassText = suggestedClass
      ? `${escapeHtml(String(suggestedClass.class_date || ''))} ${escapeHtml(formatTime24(suggestedClass.start_time))}-${escapeHtml(formatTime24(suggestedClass.end_time))} • ${escapeHtml(String(suggestedClass.topic || 'Recovery topic'))}`
      : 'Not scheduled yet';
    const riskNote = riskTone === 'watch'
      ? 'Soft watch active. Follow the suggested slot if useful.'
      : riskTone === 'high'
        ? 'Recovery acknowledgement is required.'
        : 'Critical recovery plan. Admin escalation is active.';
    const actionMarkup = studentActions.length
      ? studentActions.map((action) => `
          <article class="recovery-action-row ${recoveryActionTone(action.status)}">
            <div class="recovery-action-head">
              <div>
                <p class="recovery-action-title">${escapeHtml(action.title || 'Recovery action')}</p>
                <p class="recovery-action-description">${escapeHtml(action.description || '')}</p>
              </div>
              <span class="recovery-plan-risk ${recoveryActionTone(action.status)}">${escapeHtml(statusLabel(action.status || 'pending'))}</span>
            </div>
            <div class="recovery-action-meta">
              <small>Due: ${escapeHtml(formatRecoveryDateTime(action.scheduled_for))}</small>
              ${action.metadata?.mandatory ? '<small>Required action</small>' : ''}
              ${action.metadata?.requires_acknowledgement ? '<small>Acknowledgement required</small>' : ''}
              ${action.metadata?.structured ? '<small>Structured recovery plan</small>' : ''}
              ${action.outcome_note ? `<small>${escapeHtml(action.outcome_note)}</small>` : ''}
            </div>
            ${buildRecoveryActionButtons(action)}
          </article>
        `).join('')
      : '<div class="recovery-empty">No student task is pending right now. Faculty/admin interventions are still tracked for this plan.</div>';

    return `
      <article class="recovery-plan-card ${riskTone}">
        <div class="recovery-plan-head">
          <div>
            <h4>${escapeHtml(plan.course_code)} - ${escapeHtml(plan.course_title)}</h4>
            <p>${escapeHtml(plan.summary || '')}</p>
          </div>
          <span class="recovery-plan-risk ${riskTone}">${escapeHtml(statusLabel(plan.risk_level || 'watch'))}</span>
        </div>
        <p class="recovery-plan-summary">${escapeHtml(riskNote)} Recovery due by ${escapeHtml(formatRecoveryDateTime(plan.recovery_due_at))}. Suggested remedial slot: ${suggestedClassText}.</p>
        <div class="recovery-plan-metrics">
          <div class="recovery-metric">
            <span>Attendance</span>
            <strong>${Number(plan.attendance_percent || 0).toFixed(1)}%</strong>
          </div>
          <div class="recovery-metric">
            <span>Consecutive Absences</span>
            <strong>${Number(plan.consecutive_absences || 0)}</strong>
          </div>
          <div class="recovery-metric">
            <span>Missed Remedials</span>
            <strong>${Number(plan.missed_remedials || 0)}</strong>
          </div>
          <div class="recovery-metric">
            <span>Support Signals</span>
            <strong>${escapeHtml(supportText)}</strong>
          </div>
        </div>
        <div class="recovery-actions">${actionMarkup}</div>
      </article>
    `;
  }).join('');
}

function renderFacultyRecoveryPlans() {
  if (!els.facultyRecoveryList) {
    return;
  }
  const plans = Array.isArray(state.faculty.recoveryPlans) ? state.faculty.recoveryPlans : [];
  if (!plans.length) {
    els.facultyRecoveryList.innerHTML = '<div class="recovery-empty">No active recovery plans for the selected faculty view.</div>';
    return;
  }

  els.facultyRecoveryList.innerHTML = plans.map((plan) => {
    const riskTone = recoveryRiskTone(plan.risk_level);
    const visibleActions = Array.isArray(plan.actions)
      ? plan.actions.filter((action) => isVisibleRecoveryAction(action))
      : [];
    const studentActions = visibleActions
      .filter((action) => String(action?.recipient_role || '').trim().toLowerCase() === 'student');
    const nextAction = studentActions.find((action) => {
      const status = String(action?.status || '').trim().toLowerCase();
      return status !== 'completed';
    }) || studentActions[0] || null;
    return `
      <article class="recovery-plan-card ${riskTone}">
        <div class="recovery-plan-head">
          <div>
            <h4>${escapeHtml(plan.student_name || 'Student')} • ${escapeHtml(plan.registration_number || 'No reg')}</h4>
            <p>${escapeHtml(plan.course_code || '')} - ${escapeHtml(plan.course_title || '')} | Section ${escapeHtml(plan.section || '--')}</p>
          </div>
          <span class="recovery-plan-risk ${riskTone}">${escapeHtml(statusLabel(plan.risk_level || 'watch'))}</span>
        </div>
        <p class="recovery-plan-summary">${escapeHtml(plan.summary || '')}</p>
        <div class="recovery-plan-metrics">
          <div class="recovery-metric">
            <span>Attendance</span>
            <strong>${Number(plan.attendance_percent || 0).toFixed(1)}%</strong>
          </div>
          <div class="recovery-metric">
            <span>Consecutive Absences</span>
            <strong>${Number(plan.consecutive_absences || 0)}</strong>
          </div>
          <div class="recovery-metric">
            <span>Missed Remedials</span>
            <strong>${Number(plan.missed_remedials || 0)}</strong>
          </div>
          <div class="recovery-metric">
            <span>Next Student Action</span>
            <strong>${escapeHtml(nextAction?.title || 'Monitor current plan')}</strong>
          </div>
          <div class="recovery-metric">
            <span>Recovery Due</span>
            <strong>${escapeHtml(formatRecoveryDateTime(plan.recovery_due_at))}</strong>
          </div>
        </div>
      </article>
    `;
  }).join('');
}

function summarizeAdminRecoveryPlans(plans = []) {
  const summary = {
    watch: 0,
    high: 0,
    critical: 0,
    escalated: 0,
    overdue: 0,
    acknowledgementPending: 0,
  };
  const nowMs = Date.now();
  for (const plan of plans) {
    const risk = String(plan?.risk_level || '').trim().toLowerCase();
    if (risk === 'critical') {
      summary.critical += 1;
    } else if (risk === 'high') {
      summary.high += 1;
    } else {
      summary.watch += 1;
    }
    if (String(plan?.status || '').trim().toLowerCase() === 'escalated') {
      summary.escalated += 1;
    }
    const dueStamp = Date.parse(String(plan?.recovery_due_at || '').trim());
    if (Number.isFinite(dueStamp) && dueStamp < nowMs && String(plan?.status || '').trim().toLowerCase() !== 'recovered') {
      summary.overdue += 1;
    }
    const actions = Array.isArray(plan?.actions) ? plan.actions : [];
    if (actions.some((action) => {
      const status = String(action?.status || '').trim().toLowerCase();
      return status === 'pending' && Boolean(action?.metadata?.requires_acknowledgement);
    })) {
      summary.acknowledgementPending += 1;
    }
  }
  return summary;
}

function renderAdminRecoveryPlans() {
  if (!els.adminRecoveryList) {
    return;
  }
  const plans = Array.isArray(state.admin?.recoveryPlans) ? state.admin.recoveryPlans : [];
  const includeResolved = Boolean(state.admin?.recoveryIncludeResolved);
  const counts = summarizeAdminRecoveryPlans(plans);

  if (els.adminRecoverySummary) {
    els.adminRecoverySummary.innerHTML = `
      <div class="admin-recovery-stat">
        <span>Watch</span>
        <strong>${counts.watch}</strong>
      </div>
      <div class="admin-recovery-stat">
        <span>High Risk</span>
        <strong>${counts.high}</strong>
      </div>
      <div class="admin-recovery-stat critical">
        <span>Critical</span>
        <strong>${counts.critical}</strong>
      </div>
      <div class="admin-recovery-stat">
        <span>Escalated</span>
        <strong>${counts.escalated}</strong>
      </div>
      <div class="admin-recovery-stat">
        <span>Overdue</span>
        <strong>${counts.overdue}</strong>
      </div>
      <div class="admin-recovery-stat">
        <span>Ack Pending</span>
        <strong>${counts.acknowledgementPending}</strong>
      </div>
    `;
  }

  if (!plans.length) {
    els.adminRecoveryList.innerHTML = `<div class="recovery-empty">${includeResolved ? 'No recovery plans match the current filter.' : 'No active recovery plan is currently open. The autopilot will surface watch, high, and critical students here.'}</div>`;
    return;
  }

  els.adminRecoveryList.innerHTML = plans.map((plan) => {
    const riskTone = recoveryRiskTone(plan.risk_level);
    const statusTone = recoveryPlanStatusTone(plan.status);
    const visibleActions = Array.isArray(plan.actions)
      ? plan.actions.filter((action) => isVisibleRecoveryAction(action))
      : [];
    const studentAction = visibleActions.find((action) => {
      const role = String(action?.recipient_role || '').trim().toLowerCase();
      const status = String(action?.status || '').trim().toLowerCase();
      return role === 'student' && status !== 'completed';
    }) || visibleActions.find((action) => String(action?.recipient_role || '').trim().toLowerCase() === 'student') || null;
    const supportSignals = visibleActions
      .filter((action) => String(action?.recipient_role || '').trim().toLowerCase() !== 'student')
      .map((action) => action.title || statusLabel(action.action_type || action.recipient_role || 'support'));
    const suggestedClass = plan.recommended_makeup_class;
    const suggestedClassText = suggestedClass
      ? `${escapeHtml(String(suggestedClass.class_date || ''))} ${escapeHtml(formatTime24(suggestedClass.start_time))}-${escapeHtml(formatTime24(suggestedClass.end_time))}`
      : 'Not scheduled';
    const dueStamp = Date.parse(String(plan.recovery_due_at || '').trim());
    const isOverdue = Number.isFinite(dueStamp)
      && dueStamp < Date.now()
      && String(plan.status || '').trim().toLowerCase() !== 'recovered';
    const rmsEscalated = String(plan.status || '').trim().toLowerCase() === 'escalated';
    const supportSummary = supportSignals.length
      ? supportSignals.slice(0, 3).map((label) => escapeHtml(String(label))).join(' | ')
      : 'No support action logged yet.';
    const parentPolicyText = plan.parent_alert_allowed
      ? 'Parent/sponsor alert permitted by policy.'
      : 'Parent/sponsor alert blocked by policy.';

    return `
      <article class="recovery-plan-card ${riskTone}">
        <div class="recovery-plan-head">
          <div>
            <h4>${escapeHtml(plan.student_name || 'Student')} • ${escapeHtml(plan.registration_number || 'No reg')}</h4>
            <p>${escapeHtml(plan.course_code || '')} - ${escapeHtml(plan.course_title || '')} | Section ${escapeHtml(plan.section || '--')} | Faculty ${escapeHtml(plan.faculty_name || '--')}</p>
          </div>
          <div class="recovery-plan-chip-row">
            <span class="recovery-plan-risk ${riskTone}">${escapeHtml(statusLabel(plan.risk_level || 'watch'))}</span>
            <span class="recovery-plan-risk ${statusTone}">${escapeHtml(statusLabel(plan.status || 'active'))}</span>
          </div>
        </div>
        <p class="recovery-plan-summary">${escapeHtml(plan.summary || '')}</p>
        <div class="recovery-plan-metrics">
          <div class="recovery-metric">
            <span>Attendance</span>
            <strong>${Number(plan.attendance_percent || 0).toFixed(1)}%</strong>
          </div>
          <div class="recovery-metric">
            <span>Due By</span>
            <strong>${escapeHtml(formatRecoveryDateTime(plan.recovery_due_at))}</strong>
          </div>
          <div class="recovery-metric">
            <span>Next Student Action</span>
            <strong>${escapeHtml(studentAction?.title || 'Monitoring only')}</strong>
          </div>
          <div class="recovery-metric">
            <span>Support Signals</span>
            <strong>${supportSummary}</strong>
          </div>
          <div class="recovery-metric">
            <span>Suggested Remedial</span>
            <strong>${suggestedClassText}</strong>
          </div>
          <div class="recovery-metric">
            <span>Policy Gate</span>
            <strong>${escapeHtml(parentPolicyText)}</strong>
          </div>
        </div>
        <div class="recovery-action-row ${isOverdue ? 'pending' : recoveryActionTone(studentAction?.status || 'pending')}">
          <div class="recovery-action-head">
            <div>
              <p class="recovery-action-title">${escapeHtml(isOverdue ? 'Recovery deadline breached' : 'Operator next step')}</p>
              <p class="recovery-action-description">${escapeHtml(isOverdue ? 'This plan is overdue and should be reviewed immediately. Recompute the plan, verify attendance drift, and move the case through RMS if the student remains off-track.' : (studentAction?.description || 'Use recompute if attendance changed outside the normal flow, or open RMS for escalated plans.'))}</p>
            </div>
            <span class="recovery-plan-risk ${isOverdue ? 'high' : recoveryPlanStatusTone(plan.status)}">${escapeHtml(isOverdue ? 'Overdue' : statusLabel(plan.status || 'active'))}</span>
          </div>
          <div class="recovery-action-meta">
            <small>Consecutive absences: ${Number(plan.consecutive_absences || 0)}</small>
            <small>Missed remedials: ${Number(plan.missed_remedials || 0)}</small>
            ${studentAction?.metadata?.requires_acknowledgement ? '<small>Student acknowledgement still required.</small>' : ''}
            ${rmsEscalated ? '<small>RMS escalation already active.</small>' : ''}
          </div>
          <div class="recovery-action-buttons">
            <button class="btn" type="button" data-admin-recovery-command="recompute-plan" data-admin-recovery-student-id="${Number(plan.student_id || 0)}" data-admin-recovery-course-id="${Number(plan.course_id || 0)}">
              Recompute
            </button>
            ${rmsEscalated ? `
              <button class="btn btn-primary" type="button" data-admin-recovery-command="open-rms" data-admin-recovery-plan-id="${Number(plan.id || 0)}">
                Open RMS
              </button>
            ` : ''}
          </div>
        </div>
      </article>
    `;
  }).join('');
}

function attendanceCourseKey(courseCode, courseTitle) {
  return `${String(courseCode || '').trim().toUpperCase()}::${String(courseTitle || '').trim().toUpperCase()}`;
}

function attendanceRectificationRowKey({ courseId = 0, scheduleId = 0, classDate = '', startTime = '' }) {
  const schedule = Number(scheduleId || 0);
  const course = Number(courseId || 0);
  const datePart = String(classDate || '').trim();
  const startPart = String(startTime || '').trim();
  if (schedule > 0) {
    return `S:${schedule}|D:${datePart}`;
  }
  return `C:${course}|D:${datePart}|T:${startPart}`;
}

function sortAttendanceHistoryRows(rows = []) {
  return [...rows].sort((left, right) => {
    const leftDate = String(left.class_date || '');
    const rightDate = String(right.class_date || '');
    if (leftDate !== rightDate) {
      return rightDate.localeCompare(leftDate);
    }
    const leftTime = String(left.start_time || '');
    const rightTime = String(right.start_time || '');
    return leftTime.localeCompare(rightTime);
  });
}

function indexAttendanceHistoryByCourse(rows = []) {
  const grouped = {};
  for (const row of rows) {
    const key = attendanceCourseKey(row.course_code, row.course_title);
    if (!grouped[key]) {
      grouped[key] = [];
    }
    grouped[key].push(row);
  }
  for (const key of Object.keys(grouped)) {
    grouped[key] = sortAttendanceHistoryRows(grouped[key]);
  }
  return grouped;
}

function indexAttendanceRectificationRequests(rows = []) {
  const grouped = {};
  for (const row of rows) {
    const key = attendanceRectificationRowKey({
      courseId: row.course_id,
      scheduleId: row.schedule_id,
      classDate: row.class_date,
      startTime: row.class_start_time,
    });
    const previous = grouped[key];
    if (!previous) {
      grouped[key] = row;
      continue;
    }
    const prevTs = Date.parse(previous.requested_at || '') || 0;
    const nextTs = Date.parse(row.requested_at || '') || 0;
    if (nextTs >= prevTs) {
      grouped[key] = row;
    }
  }
  return grouped;
}

function closeAttendanceDetailsModal() {
  state.student.attendanceDetailsCourseKey = '';
  if (els.attendanceDetailsModal) {
    els.attendanceDetailsModal.classList.add('hidden');
  }
  closeAttendanceRectificationModal();
}

function setAttendanceRectificationProofPreview(dataUrl = '') {
  state.student.attendanceRectificationProofDataUrl = String(dataUrl || '');
  if (!els.attendanceRectificationProofPreview) {
    return;
  }
  if (state.student.attendanceRectificationProofDataUrl) {
    els.attendanceRectificationProofPreview.src = state.student.attendanceRectificationProofDataUrl;
    els.attendanceRectificationProofPreview.classList.remove('hidden');
  } else {
    els.attendanceRectificationProofPreview.removeAttribute('src');
    els.attendanceRectificationProofPreview.classList.add('hidden');
  }
}

function closeAttendanceRectificationModal() {
  state.student.attendanceRectificationTarget = null;
  state.student.attendanceRectificationProofDataUrl = '';
  if (els.attendanceRectificationProofNote) {
    els.attendanceRectificationProofNote.value = '';
  }
  if (els.attendanceRectificationProofPhotoInput) {
    els.attendanceRectificationProofPhotoInput.value = '';
  }
  if (els.attendanceRectificationStatus) {
    els.attendanceRectificationStatus.textContent = '';
  }
  setAttendanceRectificationProofPreview('');
  if (els.attendanceRectificationModal) {
    els.attendanceRectificationModal.classList.add('hidden');
  }
}

function openAttendanceRectificationModal({ courseId, scheduleId, classDate, startTime, endTime, courseCode, courseTitle } = {}) {
  if (!els.attendanceRectificationModal || !els.attendanceRectificationContext) {
    return;
  }
  const key = attendanceRectificationRowKey({ courseId, scheduleId, classDate, startTime });
  const existing = state.student.attendanceRectificationByKey?.[key] || null;
  state.student.attendanceRectificationTarget = {
    courseId: Number(courseId || 0),
    scheduleId: Number(scheduleId || 0),
    classDate: String(classDate || ''),
    startTime: String(startTime || ''),
  };

  const classDateLabel = parseISODateLocal(classDate).toLocaleDateString('en-GB');
  const classTimeLabel = `${formatTime24(startTime)}-${formatTime24(endTime)}`;
  els.attendanceRectificationContext.textContent =
    `${courseCode} - ${courseTitle} | ${classDateLabel} ${classTimeLabel}`;

  if (els.attendanceRectificationProofNote) {
    els.attendanceRectificationProofNote.value = existing?.proof_note || '';
  }
  if (els.attendanceRectificationStatus) {
    const reviewNote = existing?.review_note ? ` | Faculty note: ${existing.review_note}` : '';
    els.attendanceRectificationStatus.textContent = existing
      ? `Current status: ${statusLabel(existing.status)}${reviewNote}`
      : '';
  }
  setAttendanceRectificationProofPreview(existing?.proof_photo_data_url || '');
  if (els.attendanceRectificationProofPhotoInput) {
    els.attendanceRectificationProofPhotoInput.value = '';
  }
  els.attendanceRectificationModal.classList.remove('hidden');
}

async function submitStudentRectificationRequest() {
  const target = state.student.attendanceRectificationTarget;
  if (!target) {
    throw new Error('Select a class row first.');
  }

  const proofNote = String(els.attendanceRectificationProofNote?.value || '').trim();
  if (proofNote.length < 10) {
    throw new Error('Please provide clear proof details (minimum 10 characters).');
  }

  await api('/attendance/student/rectification-requests', {
    method: 'POST',
    body: JSON.stringify({
      course_id: target.courseId,
      class_date: target.classDate,
      start_time: target.startTime || null,
      proof_note: proofNote,
      proof_photo_data_url: state.student.attendanceRectificationProofDataUrl || null,
    }),
  });

  log('Attendance rectification request submitted.');
  await loadStudentAttendanceInsights();
  if (state.student.attendanceDetailsCourseKey) {
    renderAttendanceDetailsModal(state.student.attendanceDetailsCourseKey);
  }
  closeAttendanceRectificationModal();
}

function renderAttendanceDetailsModal(courseKey) {
  if (!els.attendanceDetailsModal || !els.attendanceDetailsList || !els.attendanceDetailsTitle || !els.attendanceDetailsMeta) {
    return;
  }

  const aggregateRows = state.student.attendanceAggregate?.courses || [];
  const selected = aggregateRows.find(
    (row) => attendanceCourseKey(row.course_code, row.course_title) === courseKey
  );
  if (!selected) {
    closeAttendanceDetailsModal();
    return;
  }

  const records = state.student.attendanceHistoryByCourse?.[courseKey] || [];
  const percent = Number(selected.attendance_percent || 0).toFixed(1);
  const last = selected.last_attended_on
    ? parseISODateLocal(selected.last_attended_on).toLocaleDateString('en-GB')
    : 'N/A';

  els.attendanceDetailsTitle.textContent = `${selected.course_code} - ${selected.course_title}`;
  els.attendanceDetailsMeta.textContent =
    `Attendance ${percent}% | Faculty: ${selected.faculty_name} | Last Attended: ${last} | ` +
    `Attended/Delivered: ${selected.attended_classes} / ${selected.delivered_classes}`;

  if (!records.length) {
    els.attendanceDetailsList.innerHTML = '<div class="list-item">No class attendance records for this subject yet.</div>';
  } else {
    const rectificationByKey = state.student.attendanceRectificationByKey || {};
    const rowsMarkup = records
      .map((row) => {
        const statusRaw = String(row.status || '').toLowerCase();
        const isPresent = statusRaw === 'present';
        const rowKey = attendanceRectificationRowKey({
          courseId: selected.course_id,
          scheduleId: row.schedule_id,
          classDate: row.class_date,
          startTime: row.start_time,
        });
        const rectification = rectificationByKey[rowKey] || null;
        const rectificationStatus = String(rectification?.status || '').toLowerCase();
        let statusClass = isPresent ? 'present' : 'absent';
        let statusLabelText = isPresent ? 'Present' : 'Absent';
        if (!isPresent && rectificationStatus === 'pending') {
          statusClass = 'pending';
          statusLabelText = 'Pending';
        } else if (!isPresent && rectificationStatus === 'approved') {
          statusClass = 'present';
          statusLabelText = 'Approved';
        } else if (!isPresent && rectificationStatus === 'rejected') {
          statusClass = 'absent';
          statusLabelText = 'Rejected';
        }
        const classDate = parseISODateLocal(row.class_date).toLocaleDateString('en-GB');
        const timeRange = formatAttendanceDetailTimeRange(row, selected.course_code);
        const canRequest = !isPresent && rectificationStatus !== 'approved' && !isSaarthiAttendanceRow(row, selected.course_code);
        const requestLabel = rectificationStatus === 'rejected' ? 'Resubmit Request' : 'Request Rectification';
        const actionMarkup = canRequest
          ? `<button class="btn attendance-detail-proof-btn" type="button"
              data-open-rectification="1"
              data-rectification-course-id="${Number(selected.course_id || 0)}"
              data-rectification-course-code="${escapeHtml(selected.course_code)}"
              data-rectification-course-title="${escapeHtml(selected.course_title)}"
              data-rectification-schedule-id="${Number(row.schedule_id || 0)}"
              data-rectification-class-date="${escapeHtml(row.class_date)}"
              data-rectification-start-time="${escapeHtml(row.start_time)}"
              data-rectification-end-time="${escapeHtml(row.end_time)}"
            >${requestLabel}</button>`
          : '';
        return `
          <article class="attendance-detail-row ${statusClass}">
            <div class="attendance-detail-main">
              <strong>${escapeHtml(classDate)}</strong>
              <small>${escapeHtml(timeRange)}</small>
            </div>
            <div class="attendance-detail-tail">
              <span class="attendance-detail-status ${statusClass}">${statusLabelText}</span>
              ${actionMarkup}
            </div>
          </article>
        `;
      })
      .join('');
    els.attendanceDetailsList.innerHTML = rowsMarkup;
  }

  state.student.attendanceDetailsCourseKey = courseKey;
  els.attendanceDetailsModal.classList.remove('hidden');
}

async function loadStudentAttendanceInsights() {
  if (authState.user?.role !== 'student') {
    return;
  }

  const [aggregateRes, historyRes, rectificationRes, recoveryRes] = await Promise.allSettled([
    api('/attendance/student/attendance-aggregate'),
    api('/attendance/student/attendance-history?limit=80'),
    api('/attendance/student/rectification-requests?limit=200'),
    api('/attendance/student/recovery-plans?limit=12'),
  ]);

  let primaryError = null;
  if (aggregateRes.status === 'fulfilled') {
    state.student.attendanceAggregate = aggregateRes.value;
  } else {
    primaryError = aggregateRes.reason || primaryError;
  }

  if (historyRes.status === 'fulfilled') {
    const history = historyRes.value && typeof historyRes.value === 'object' ? historyRes.value : {};
    state.student.attendanceHistory = Array.isArray(history.records) ? history.records : [];
    state.student.attendanceHistoryByCourse = indexAttendanceHistoryByCourse(state.student.attendanceHistory);
  } else {
    primaryError = historyRes.reason || primaryError;
  }

  if (rectificationRes.status === 'fulfilled') {
    const rectification = rectificationRes.value && typeof rectificationRes.value === 'object'
      ? rectificationRes.value
      : {};
    state.student.attendanceRectificationRequests = Array.isArray(rectification.requests)
      ? rectification.requests
      : [];
    state.student.attendanceRectificationByKey = indexAttendanceRectificationRequests(
      state.student.attendanceRectificationRequests
    );
  } else {
    log(rectificationRes.reason?.message || 'Rectification feed refresh failed; attendance ledger still updated.');
  }

  if (recoveryRes.status === 'fulfilled') {
    const recovery = recoveryRes.value && typeof recoveryRes.value === 'object' ? recoveryRes.value : {};
    state.student.recoveryPlans = Array.isArray(recovery.plans) ? recovery.plans : [];
  } else {
    state.student.recoveryPlans = [];
    primaryError = recoveryRes.reason || primaryError;
  }

  renderStudentAttendanceAggregate();
  renderStudentRecoveryPlans();
  if (primaryError) {
    throw primaryError;
  }
}

async function submitStudentRecoveryAction(actionId, command) {
  const normalizedId = Number(actionId || 0);
  const normalizedCommand = String(command || '').trim().toLowerCase();
  if (!normalizedId) {
    throw new Error('Recovery action is invalid.');
  }
  if (!['acknowledge', 'complete'].includes(normalizedCommand)) {
    throw new Error('Unsupported recovery action.');
  }

  const endpoint = normalizedCommand === 'acknowledge'
    ? `/attendance/student/recovery-actions/${normalizedId}/acknowledge`
    : `/attendance/student/recovery-actions/${normalizedId}/complete`;

  await api(endpoint, {
    method: 'POST',
    body: JSON.stringify({}),
  });
  log(`Recovery action ${normalizedCommand}d.`);
  await loadStudentAttendanceInsights();
}

function setStudentResult(text, options = {}) {
  if (!els.studentAttendanceResult) {
    return;
  }

  const { showRetry = false, retryAction = null } = options;
  els.studentAttendanceResult.replaceChildren();

  const textBlock = document.createElement('div');
  textBlock.style.whiteSpace = 'pre-wrap';
  textBlock.textContent = text;
  els.studentAttendanceResult.appendChild(textBlock);

  if (!showRetry) {
    return;
  }

  const retryBtn = document.createElement('button');
  retryBtn.type = 'button';
  retryBtn.className = 'btn';
  retryBtn.style.marginTop = '0.55rem';
  retryBtn.textContent = 'RETRY';
  retryBtn.addEventListener('click', async () => {
    retryBtn.disabled = true;
    try {
      if (typeof retryAction === 'function') {
        await retryAction();
      } else {
        await startStudentSelfieFlow();
      }
    } catch (error) {
      log(error.message);
      setStudentResult(error.message);
    } finally {
      retryBtn.disabled = false;
    }
  });
  els.studentAttendanceResult.appendChild(retryBtn);
}

function selectStudentSchedule(scheduleId) {
  state.student.selectedScheduleId = scheduleId;
  renderStudentTimetable();
}

function pickStudentFallbackSchedule() {
  const classes = (state.student.timetable && state.student.timetable.length)
    ? state.student.timetable
    : (state.student.kpiTimetable || []);
  if (!classes.length) {
    return null;
  }

  const today = todayISO();
  const todayClasses = classes.filter((item) => String(item.class_date || '') === today);
  const pool = todayClasses.length ? todayClasses : classes;

  return (
    pool.find((item) => resolveTimetableKpi(item).key === 'mark')
    || pool.find((item) => resolveTimetableKpi(item).key === 'upcoming')
    || pool.find((item) => resolveTimetableKpi(item).key === 'present')
    || pool[0]
    || null
  );
}

function ensureStudentScheduleSelection() {
  const selected = state.student.timetable.find((item) => item.schedule_id === state.student.selectedScheduleId) || null;
  if (selected) {
    return selected;
  }
  const fallback = pickStudentFallbackSchedule();
  if (fallback) {
    state.student.selectedScheduleId = fallback.schedule_id;
  }
  return fallback;
}

async function buildAttendanceVerificationPayload(
  selectedScheduleId,
  selfieDataUrl,
  selfieFrames = [],
  options = {},
) {
  const demoMode = Boolean(options?.demoMode);
  const payload = {
    selfie_photo_data_url: selfieDataUrl,
    demo_mode: demoMode,
  };
  const normalizedScheduleId = Number(selectedScheduleId || 0);
  if (!demoMode && normalizedScheduleId > 0) {
    payload.schedule_id = normalizedScheduleId;
  }
  if (Array.isArray(selfieFrames) && selfieFrames.length) {
    payload.selfie_frames_data_urls = selfieFrames;
  }

  // OpenCV end-to-end pipeline: skip client AI call for faster and deterministic verification.
  if (!USE_CLIENT_AI_FACE_ASSIST) {
    return payload;
  }

  try {
    const verdict = await Promise.race([
      compareFacesWithAI(state.student.profilePhotoDataUrl, selfieDataUrl),
      new Promise((resolve) => {
        window.setTimeout(() => resolve(null), 1200);
      }),
    ]);
    if (verdict) {
      payload.ai_match = verdict.match;
      payload.ai_confidence = verdict.confidence;
      payload.ai_reason = verdict.reason;
      payload.ai_model = verdict.model;
    }
  } catch (error) {
    log(`Client AI verification unavailable, using server OpenCV fallback: ${error.message}`);
  }

  return payload;
}

function deriveLiveGuidance(message = '') {
  const text = String(message || '').toLowerCase();
  if (text.includes('unauthorized marking attempt') || text.includes('different person')) {
    return 'Different person detected. Only the registered student can mark attendance.';
  }
  if (text.includes('liveness')) {
    return 'Move your head slowly left/right/up/down while keeping face centered.';
  }
  if (text.includes('centered')) {
    return 'Align your face in the center and keep your phone at eye level.';
  }
  if (text.includes('blurry')) {
    return 'Hold phone steady and improve front lighting on your face.';
  }
  if (text.includes('resolution')) {
    return 'Move closer and keep your face larger in frame for higher quality capture.';
  }
  if (text.includes('lighting') || text.includes('contrast')) {
    return 'Move to a brighter area and keep light in front of your face.';
  }
  if (text.includes('covered')) {
    return 'Keep full face visible. Remove hand/hair/mask from face area.';
  }
  if (text.includes('multiple faces')) {
    return 'Keep only one person in the camera frame.';
  }
  if (text.includes('landmark') || text.includes('eye')) {
    return 'Look straight into the camera and keep both eyes clearly visible.';
  }
  if (text.includes('consistency failed')) {
    return 'Keep your face centered and continue slight head movement until verification stabilizes.';
  }
  return 'Keep face straight, centered, and well-lit while verification continues.';
}

function shouldStopLiveVerification(message = '') {
  const text = String(message || '').toLowerCase();
  return (
    text.includes('attendance already verified')
    || text.includes('window is closed')
    || text.includes('not scheduled for today')
    || text.includes('session expired')
    || text.includes('invalid user session')
    || text.includes('student is not enrolled')
    || text.includes('class schedule not found')
    || text.includes('unauthorized marking attempt')
    || text.includes('different person identified')
  );
}

async function submitStudentAttendanceAttempt(
  selectedScheduleId,
  selfieDataUrl,
  selfieFrames = [],
  options = {},
) {
  const payload = await buildAttendanceVerificationPayload(
    selectedScheduleId,
    selfieDataUrl,
    selfieFrames,
    options,
  );
  return apiWithTimeout(
    '/attendance/realtime/mark',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    ATTENDANCE_VERIFY_REQUEST_TIMEOUT_MS,
    'Verification request timed out. Retrying automatically...'
  );
}

async function startLiveAttendanceVerification(options = {}) {
  const demoMode = Boolean(options?.demoMode);
  const kpi = demoMode ? null : findAttendanceManagementState();
  const selectedScheduleId = demoMode ? null : Number(kpi?.schedule?.schedule_id || 0);
  if (!demoMode) {
    if (kpi.mode !== 'mark' || !selectedScheduleId) {
      throw new Error('Attendance window is closed right now. Wait for the next class.');
    }
    if (String(kpi.schedule?.class_kind || 'regular').toLowerCase() === 'remedial') {
      throw new Error('This is a remedial class. Open Remedial module, validate the faculty code, then mark attendance there.');
    }
    state.student.kpiScheduleId = selectedScheduleId;
    state.student.selectedScheduleId = selectedScheduleId;
  } else {
    const demoState = options?.demoState && options.demoState.mode === 'demo'
      ? options.demoState
      : findStudentDemoAttendanceState();
    if (!demoState || demoState.mode !== 'demo') {
      throw new Error('Demo attendance is disabled. Enable Demo Attendance first.');
    }
    state.student.kpiScheduleId = null;
    state.student.selectedScheduleId = null;
  }
  if (!state.student.profilePhotoDataUrl) {
    throw new Error('Upload profile photo before marking attendance.');
  }
  if (requiresStudentEnrollmentSetup()) {
    throw new Error('Complete one-time enrollment video before marking attendance.');
  }
  if (state.camera.liveVerificationActive) {
    throw new Error('Live verification is already running.');
  }

  setStudentResult(demoMode
    ? 'Live demo attendance verification started...'
    : 'Live attendance verification started...');

  await openCameraModal({
    title: demoMode ? 'Live Realtime Demo Verification' : 'Live Realtime Attendance Verification',
    facingMode: 'user',
    referencePhotoDataUrl: state.student.profilePhotoDataUrl,
    burstFrames: LIVE_VERIFICATION_BURST_FRAMES,
    captureEnabled: false,
    messageOverride: demoMode
      ? 'OpenCV live verification running in demo mode. Keep one face centered, look straight, then move head slightly left/right/up/down. No attendance data is saved.'
      : 'OpenCV live verification running. Keep one face centered, look straight, then move head slightly left/right/up/down.',
  });

  const sessionToken = state.camera.liveSessionToken;
  state.camera.liveVerificationActive = true;

  let attempts = 0;
  let livenessFailures = 0;
  const maxAttempts = LIVE_VERIFICATION_MAX_ATTEMPTS;
  while (
    state.camera.liveVerificationActive
    && state.camera.stream
    && sessionToken === state.camera.liveSessionToken
  ) {
    if (attempts >= maxAttempts) {
      const timeoutMsg = demoMode
        ? 'Verification took too long. Use bright front light, keep one centered face, then retry. Demo mode does not save attendance data.'
        : 'Verification took too long. Use bright front light, keep one centered face, then retry.';
      setStudentResult(timeoutMsg, {
        showRetry: true,
        retryAction: () => (demoMode ? startStudentDemoAttendanceFlow() : startStudentSelfieFlow()),
      });
      if (els.cameraMessage) {
        els.cameraMessage.textContent = timeoutMsg;
      }
      break;
    }
    attempts += 1;
    try {
      if (els.cameraMessage) {
        els.cameraMessage.textContent = `Analyzing live frames... attempt ${attempts}/${maxAttempts}`;
      }
      const selfieFrames = await captureBurstFramesFromCamera(
        LIVE_VERIFICATION_BURST_FRAMES,
        LIVE_VERIFICATION_BURST_INTERVAL_MS,
        0.9
      );
      const selfieDataUrl = selfieFrames[0];
      if (selfieDataUrl) {
        state.student.selfieDataUrl = selfieDataUrl;
        if (els.selfiePreview) {
          els.selfiePreview.src = selfieDataUrl;
          els.selfiePreview.classList.remove('hidden');
        }
      }

      const response = await submitStudentAttendanceAttempt(
        selectedScheduleId,
        selfieDataUrl,
        selfieFrames,
        { demoMode },
      );
      const status = String(response.status || '').toLowerCase();
      const confidencePct = (Number(response.verification_confidence || 0) * 100).toFixed(1);
      const verified = ['verified', 'approved', 'present'].includes(status);

      if (verified) {
        const lines = [
          `Status: ${statusLabel(response.status)}`,
          `Message: ${response.message}`,
        ];
        if (
          (demoMode || response.demo_mode || response.persistence_skipped)
          && !String(response.message || '').toLowerCase().includes('did not save')
        ) {
          lines.push('Persistence: Demo mode did not save attendance data.');
        }
        setStudentResult(lines.join('\n'));
        if (els.cameraMessage) {
          els.cameraMessage.textContent = demoMode
            ? 'Demo verification complete. Closing camera...'
            : 'Attendance verified. Closing camera...';
        }
        if (demoMode || response.demo_mode || response.persistence_skipped) {
          log(`Demo verification completed with confidence: ${confidencePct}%`);
        } else {
          log(`Attendance marked with confidence: ${confidencePct}%`);
          await loadStudentTimetable({ forceNetwork: true });
          await loadStudentAttendanceInsights();
        }
        await sleep(900);
        closeCameraModal();
        return;
      }

      const guidance = deriveLiveGuidance(response.message || response.verification_reason || '');
      const failureText = String(response.message || response.verification_reason || '').toLowerCase();
      if (failureText.includes('liveness')) {
        livenessFailures += 1;
      } else {
        livenessFailures = 0;
      }
      const lines = [
        `Status: ${statusLabel(response.status)}`,
        `Message: ${response.message}`,
      ];
      setStudentResult(lines.join('\n'));
      if (els.cameraMessage) {
        els.cameraMessage.textContent = `${guidance} Auto retry in progress...`;
      }
      log(`Live verification retry (${attempts}/${maxAttempts})`);
      if (livenessFailures >= 3) {
        const livenessTimeoutMessage = demoMode
          ? 'Liveness check still failing. Keep front light on face, center your face, and move head slowly left/right/up/down, then retry. Demo mode does not save attendance data.'
          : 'Liveness check still failing. Keep front light on face, center your face, and move head slowly left/right/up/down, then retry.';
        setStudentResult(livenessTimeoutMessage, {
          showRetry: true,
          retryAction: () => (demoMode ? startStudentDemoAttendanceFlow() : startStudentSelfieFlow()),
        });
        if (els.cameraMessage) {
          els.cameraMessage.textContent = livenessTimeoutMessage;
        }
        break;
      }
      await sleep(600);
    } catch (error) {
      const message = error?.message || 'Live verification attempt failed.';
      setStudentResult(message);
      if (els.cameraMessage) {
        els.cameraMessage.textContent = `${deriveLiveGuidance(message)} Auto retry in progress...`;
      }
      if (shouldStopLiveVerification(message)) {
        if (els.cameraMessage) {
          els.cameraMessage.textContent = `Verification stopped: ${message}`;
        }
        break;
      }
      await sleep(650);
    }
  }

  if (state.camera.stream && sessionToken === state.camera.liveSessionToken) {
    closeCameraModal();
  }
}

async function markStudentAttendance(selfieDataUrl, selfieFrames = []) {
  const selected = ensureStudentScheduleSelection();
  const selectedScheduleId = selected?.schedule_id;
  if (!selectedScheduleId) {
    throw new Error('Select a class with Mark Attendance status first.');
  }

  if (!state.student.profilePhotoDataUrl) {
    throw new Error('Upload profile photo before marking attendance.');
  }

  setStudentResult('Running strict multi-frame face verification...');
  const payload = await buildAttendanceVerificationPayload(selectedScheduleId, selfieDataUrl, selfieFrames);

  const response = await api('/attendance/realtime/mark', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

  const confidencePct = (Number(response.verification_confidence || 0) * 100).toFixed(1);
  const lines = [
    `Status: ${statusLabel(response.status)}`,
    `Message: ${response.message}`,
  ];
  const rejected = String(response.status || '').toLowerCase() === 'rejected';
  setStudentResult(lines.join('\n'), { showRetry: rejected });

  const normalizedStatus = String(response.status || '').toLowerCase();
  if (['verified', 'approved', 'present'].includes(normalizedStatus)) {
    log(`Attendance marked with confidence: ${confidencePct}%`);
  } else {
    log(`Attendance not marked (confidence: ${confidencePct}%)`);
  }
  log(`Student attendance submission: ${response.status}`);
  await loadStudentTimetable({ forceNetwork: true });
  await loadStudentAttendanceInsights();
}

async function loadFacultySchedules() {
  if (!authState.user || (authState.user.role !== 'faculty' && authState.user.role !== 'admin')) {
    return;
  }

  const schedules = await api('/attendance/faculty/schedules');
  state.faculty.schedules = schedules;

  els.facultyScheduleSelect.innerHTML = '';
  for (const schedule of schedules) {
    const option = document.createElement('option');
    const courseName = getCourseLabel(schedule.course_id);
    option.value = String(schedule.id);
    option.textContent = `${courseName} | ${DAY_LABELS[schedule.weekday]} ${formatTime(schedule.start_time)}`;
    els.facultyScheduleSelect.appendChild(option);
  }

  if (!schedules.length) {
    state.faculty.selectedScheduleId = null;
    renderFacultyDashboard(null);
    els.classroomAnalysisHistory.innerHTML = '<div class="list-item">No schedules available.</div>';
    return;
  }

  const selected = Number(els.facultyScheduleSelect.value);
  if (!selected || !schedules.some((item) => item.id === selected)) {
    els.facultyScheduleSelect.value = String(schedules[0].id);
  }

  state.faculty.selectedScheduleId = Number(els.facultyScheduleSelect.value);
  await refreshFacultyDashboard();
}

function renderFacultyDashboard(data) {
  if (!data) {
    animateNumber(els.facultyTotal, 0);
    animateNumber(els.facultyPresent, 0);
    animateNumber(els.facultyPending, 0);
    animateNumber(els.facultyAbsent, 0);
    els.facultySubmissionsBody.innerHTML = '<tr><td colspan="6">No submission data.</td></tr>';
    renderFacultyRectificationQueue([]);
    return;
  }

  animateNumber(els.facultyTotal, data.total_students || 0);
  animateNumber(els.facultyPresent, data.present || 0);
  animateNumber(els.facultyPending, data.pending_review || 0);
  animateNumber(els.facultyAbsent, data.absent || 0);

  const rows = data.submissions || [];
  els.facultySubmissionsBody.innerHTML = '';

  if (!rows.length) {
    els.facultySubmissionsBody.innerHTML = '<tr><td colspan="6">No attendance submissions yet.</td></tr>';
    return;
  }

  for (const row of rows) {
    const tr = document.createElement('tr');
    const isPending = row.status === 'pending_review';
    const checked = state.faculty.selectedSubmissionIds.has(row.id) ? 'checked' : '';

    tr.innerHTML = `
      <td>${isPending ? `<input type="checkbox" class="submission-check" data-submission-id="${row.id}" ${checked}>` : ''}</td>
      <td>${escapeHtml(row.student_name)}</td>
      <td><span class="badge ${row.status}">${escapeHtml(statusLabel(row.status))}</span></td>
      <td>${Number(row.ai_confidence || 0).toFixed(2)}</td>
      <td>${escapeHtml(row.ai_reason || '-')}</td>
      <td>${new Date(row.submitted_at).toLocaleTimeString()}</td>
    `;

    els.facultySubmissionsBody.appendChild(tr);
  }
}

function renderFacultyRectificationQueue(rows = []) {
  if (!els.facultyRectificationBody) {
    return;
  }
  els.facultyRectificationBody.innerHTML = '';
  if (!rows.length) {
    els.facultyRectificationBody.innerHTML = '<tr><td colspan="6">No rectification requests for this class date.</td></tr>';
    return;
  }

  for (const row of rows) {
    const tr = document.createElement('tr');
    const statusRaw = String(row.status || '').toLowerCase();
    const isPending = statusRaw === 'pending';
    const classDateText = parseISODateLocal(row.class_date).toLocaleDateString('en-GB');
    const classTimeText = `${formatTime24(row.class_start_time)}-${formatTime24(row.class_end_time)}`;
    const requestedAtText = row.requested_at
      ? new Date(row.requested_at).toLocaleString()
      : '-';
    const proofSummary = String(row.proof_note || '').trim();
    const proofText = proofSummary.length > 160 ? `${proofSummary.slice(0, 157)}...` : proofSummary;
    const reviewNote = String(row.review_note || '').trim();
    const attachedImage = row.proof_photo_data_url
      ? `<img class="rectification-proof-thumb" src="${escapeHtml(row.proof_photo_data_url)}" alt="Proof">`
      : '<small>No image proof</small>';
    const actionMarkup = isPending
      ? `
          <div class="rectification-action-wrap">
            <input type="text" data-rectification-note="${row.id}" placeholder="Optional note">
            <button type="button" class="btn btn-primary" data-rectification-action="approve" data-rectification-id="${row.id}">Approve</button>
            <button type="button" class="btn" data-rectification-action="reject" data-rectification-id="${row.id}">Reject</button>
          </div>
        `
      : `<small>${escapeHtml(reviewNote || 'Reviewed')}</small>`;

    tr.innerHTML = `
      <td>${escapeHtml(row.student_name)}</td>
      <td>${escapeHtml(classDateText)}<br><small>${escapeHtml(classTimeText)}</small></td>
      <td><div class="rectification-proof-inline"><p>${escapeHtml(proofText || '-')}</p>${attachedImage}</div></td>
      <td>${escapeHtml(requestedAtText)}</td>
      <td><span class="badge ${statusRaw || 'pending'}">${escapeHtml(statusLabel(statusRaw || 'pending'))}</span></td>
      <td>${actionMarkup}</td>
    `;
    els.facultyRectificationBody.appendChild(tr);
  }
}

async function loadFacultyRectificationQueue() {
  if (!authState.user || (authState.user.role !== 'faculty' && authState.user.role !== 'admin')) {
    return;
  }
  const scheduleId = Number(els.facultyScheduleSelect.value);
  const classDate = els.facultyClassDate.value;
  if (!scheduleId || !classDate) {
    renderFacultyRectificationQueue([]);
    return;
  }

  const payload = await api(
    `/attendance/faculty/rectification-requests?schedule_id=${scheduleId}&class_date=${classDate}&include_resolved=true`
  );
  state.faculty.rectificationRequests = payload.requests || [];
  renderFacultyRectificationQueue(state.faculty.rectificationRequests);
}

async function submitFacultyRectificationReview(requestId, action) {
  const noteInput = document.querySelector(`input[data-rectification-note="${Number(requestId || 0)}"]`);
  const note = noteInput instanceof HTMLInputElement ? noteInput.value.trim() : '';
  const result = await api('/attendance/faculty/rectification-review', {
    method: 'POST',
    body: JSON.stringify({
      request_id: Number(requestId),
      action,
      note: note || null,
    }),
  });
  log(`Rectification reviewed: approved ${result.approved}, rejected ${result.rejected}`);
  await refreshFacultyDashboard();
}

function syncReviewSelectionUI() {
  const pendingBoxes = [...els.facultySubmissionsBody.querySelectorAll('input.submission-check')];
  if (!pendingBoxes.length) {
    els.reviewSelectAll.checked = false;
    els.reviewSelectAll.indeterminate = false;
    return;
  }

  const checkedCount = pendingBoxes.filter((box) => box.checked).length;
  els.reviewSelectAll.checked = checkedCount === pendingBoxes.length;
  els.reviewSelectAll.indeterminate = checkedCount > 0 && checkedCount < pendingBoxes.length;
}

async function refreshFacultyDashboard() {
  if (!authState.user || (authState.user.role !== 'faculty' && authState.user.role !== 'admin')) {
    return;
  }

  const scheduleId = Number(els.facultyScheduleSelect.value);
  if (!scheduleId) {
    return;
  }

  state.faculty.selectedScheduleId = scheduleId;
  const classDate = els.facultyClassDate.value || todayISO();
  els.facultyClassDate.value = classDate;
  state.faculty.classDate = classDate;

  const [dashboardRes, recoveryRes] = await Promise.allSettled([
    api(`/attendance/faculty/dashboard?schedule_id=${scheduleId}&class_date=${classDate}`),
    api(`/attendance/faculty/recovery-plans?schedule_id=${scheduleId}&limit=40`),
  ]);

  if (dashboardRes.status !== 'fulfilled') {
    throw dashboardRes.reason;
  }

  const data = dashboardRes.value;
  state.faculty.dashboard = data;
  let recoveryLoadError = '';
  if (recoveryRes.status === 'fulfilled') {
    const recovery = recoveryRes.value && typeof recoveryRes.value === 'object' ? recoveryRes.value : {};
    state.faculty.recoveryPlans = Array.isArray(recovery.plans) ? recovery.plans : [];
  } else {
    state.faculty.recoveryPlans = [];
    recoveryLoadError = recoveryRes.reason?.message || 'Recovery radar failed to load.';
  }

  const validPendingIds = new Set(
    (data.submissions || [])
      .filter((item) => item.status === 'pending_review')
      .map((item) => item.id)
  );
  state.faculty.selectedSubmissionIds = new Set(
    [...state.faculty.selectedSubmissionIds].filter((id) => validPendingIds.has(id))
  );

  renderFacultyDashboard(data);
  renderFacultyRecoveryPlans();
  if (recoveryLoadError && els.facultyRecoveryList) {
    els.facultyRecoveryList.innerHTML = `<div class="recovery-empty">${escapeHtml(recoveryLoadError)}</div>`;
  }
  syncReviewSelectionUI();
  await loadFacultyRectificationQueue();
  await loadClassroomAnalysisHistory();
}

async function submitFacultyBatchReview(action) {
  const scheduleId = Number(els.facultyScheduleSelect.value);
  const classDate = els.facultyClassDate.value;
  const submissionIds = [...state.faculty.selectedSubmissionIds];

  if (!scheduleId) {
    throw new Error('Select a schedule first.');
  }
  if (!classDate) {
    throw new Error('Select class date first.');
  }
  if (!submissionIds.length) {
    throw new Error('Select at least one pending submission.');
  }

  const payload = {
    schedule_id: scheduleId,
    class_date: classDate,
    submission_ids: submissionIds,
    action,
    note: els.facultyReviewNote.value.trim() || null,
  };

  const result = await api('/attendance/faculty/review', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

  state.faculty.selectedSubmissionIds.clear();
  els.facultyReviewNote.value = '';
  log(`Faculty review complete: approved ${result.approved}, rejected ${result.rejected}`);
  await refreshFacultyDashboard();
}

function renderClassroomPhotoPreview(photoDataUrl) {
  if (!photoDataUrl) {
    els.classroomPhotoPreview.classList.add('hidden');
    return;
  }
  els.classroomPhotoPreview.src = photoDataUrl;
  els.classroomPhotoPreview.classList.remove('hidden');
}

async function analyzeClassroomWithAI(photoDataUrl) {
  const prompt = [
    'You are analyzing a classroom photo for attendance insights.',
    'Return JSON only with keys:',
    'estimated_headcount (integer >= 0), engagement_level (string), ai_summary (string up to 220 chars).',
    'Engagement examples: Highly attentive, Moderately attentive, Low attention.',
    'Do not include markdown.',
  ].join('\n');

  const text = await callVisionAI(prompt, photoDataUrl);
  let parsed;
  try {
    parsed = parseJsonFromText(text);
  } catch (_) {
    parsed = await coerceJsonWithAI(
      text,
      '{\"estimated_headcount\": integer, \"engagement_level\": string, \"ai_summary\": string}'
    );
  }

  const estimatedHeadcount = Math.max(0, Math.round(Number(parsed.estimated_headcount) || 0));
  const engagementLevel = String(parsed.engagement_level || 'Unknown').slice(0, 80);
  const aiSummary = String(parsed.ai_summary || '').slice(0, 760);

  return {
    estimatedHeadcount,
    engagementLevel,
    aiSummary,
    aiModel: AI_MODEL,
  };
}

async function loadClassroomAnalysisHistory() {
  if (!authState.user || (authState.user.role !== 'faculty' && authState.user.role !== 'admin')) {
    return;
  }

  const scheduleId = Number(els.facultyScheduleSelect.value);
  const classDate = els.facultyClassDate.value;
  if (!scheduleId || !classDate) {
    return;
  }

  const rows = await api(`/attendance/faculty/classroom-analysis?schedule_id=${scheduleId}&class_date=${classDate}`);
  state.faculty.analysisHistory = rows || [];

  els.classroomAnalysisHistory.innerHTML = '';
  if (!state.faculty.analysisHistory.length) {
    els.classroomAnalysisHistory.innerHTML = '<div class="list-item">No classroom analysis records yet.</div>';
    return;
  }

  for (const item of state.faculty.analysisHistory) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.innerHTML = `
      <span>${escapeHtml(item.engagement_level)} | Headcount ${item.estimated_headcount}</span>
      <span>${new Date(item.created_at).toLocaleTimeString()}</span>
    `;
    els.classroomAnalysisHistory.appendChild(row);
  }
}

async function analyzeAndSaveClassroom() {
  const scheduleId = Number(els.facultyScheduleSelect.value);
  const classDate = els.facultyClassDate.value;

  if (!scheduleId) {
    throw new Error('Select a schedule first.');
  }
  if (!classDate) {
    throw new Error('Select class date first.');
  }
  if (!state.faculty.classroomPhotoDataUrl) {
    throw new Error('Upload or capture a classroom photo first.');
  }

  els.classroomAnalysisOutput.textContent = 'Running Gemini classroom analysis...';

  const aiResult = await analyzeClassroomWithAI(state.faculty.classroomPhotoDataUrl);
  await api('/attendance/faculty/classroom-analysis', {
    method: 'POST',
    body: JSON.stringify({
      schedule_id: scheduleId,
      class_date: classDate,
      photo_data_url: state.faculty.classroomPhotoDataUrl,
      estimated_headcount: aiResult.estimatedHeadcount,
      engagement_level: aiResult.engagementLevel,
      ai_summary: aiResult.aiSummary,
      ai_model: aiResult.aiModel,
    }),
  });

  els.classroomAnalysisOutput.textContent = [
    `Estimated Headcount: ${aiResult.estimatedHeadcount}`,
    `Engagement Level: ${aiResult.engagementLevel}`,
    `Summary: ${aiResult.aiSummary || 'N/A'}`,
  ].join('\n');

  log('Classroom analysis saved to backend');
  await loadClassroomAnalysisHistory();
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function waitForVideoReady(videoElement, timeoutMs = 7000) {
  if (!videoElement) {
    throw new Error('Camera preview is unavailable.');
  }
  if (videoElement.readyState >= 2 && videoElement.videoWidth > 0 && videoElement.videoHeight > 0) {
    return;
  }

  await new Promise((resolve, reject) => {
    let settled = false;
    const timer = window.setTimeout(() => {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      reject(new Error('Camera feed did not become ready. Please allow camera and retry.'));
    }, timeoutMs);

    function cleanup() {
      window.clearTimeout(timer);
      videoElement.removeEventListener('loadeddata', onReady);
      videoElement.removeEventListener('canplay', onReady);
      videoElement.removeEventListener('error', onError);
    }

    function onReady() {
      if (settled) {
        return;
      }
      if (videoElement.videoWidth > 0 && videoElement.videoHeight > 0) {
        settled = true;
        cleanup();
        resolve();
      }
    }

    function onError() {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      reject(new Error('Unable to start camera feed.'));
    }

    videoElement.addEventListener('loadeddata', onReady);
    videoElement.addEventListener('canplay', onReady);
    videoElement.addEventListener('error', onError);
    onReady();
  });
}

async function openCameraModal({
  title,
  facingMode = 'user',
  referencePhotoDataUrl = '',
  onCapture,
  burstFrames = 1,
  captureEnabled = true,
  messageOverride = '',
}) {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('Camera is not supported in this browser.');
  }

  if (state.camera.stream) {
    closeCameraModal();
  }

  const isSelfie = String(facingMode || '').toLowerCase() !== 'environment';
  const stream = await navigator.mediaDevices.getUserMedia({
    video: {
      facingMode: isSelfie ? { ideal: 'user' } : { ideal: 'environment' },
      width: { ideal: 1280 },
      height: { ideal: 720 },
      aspectRatio: { ideal: 4 / 3 },
      frameRate: { ideal: 30, max: 30 },
      resizeMode: 'crop-and-scale',
    },
    audio: false,
  });

  state.camera.stream = stream;
  state.camera.captureHandler = onCapture;
  state.camera.burstFrames = Math.max(1, Number(burstFrames || 1));

  els.cameraTitle.textContent = title;
  els.cameraMessage.textContent = messageOverride || (state.camera.burstFrames > 1
    ? `Keep your face straight, centered at eye-level, with light on your face. Then move slightly left, right, up, and down. ${state.camera.burstFrames} frames will be captured.`
    : 'Frame your capture clearly and click Capture.');
  if (els.cameraReferenceWrap && els.cameraReferencePhoto) {
    const showReference = Boolean(referencePhotoDataUrl);
    els.cameraReferenceWrap.classList.toggle('hidden', !showReference);
    if (showReference) {
      els.cameraReferencePhoto.src = referencePhotoDataUrl;
    } else {
      els.cameraReferencePhoto.removeAttribute('src');
    }
  }
  if (els.cameraCaptureBtn) {
    setHidden(els.cameraCaptureBtn, !captureEnabled);
    els.cameraCaptureBtn.disabled = !captureEnabled;
    els.cameraCaptureBtn.textContent = captureEnabled ? 'Capture' : 'Auto Verifying...';
  }
  els.cameraVideo.srcObject = stream;
  els.cameraVideo.classList.toggle('is-selfie', isSelfie);
  try {
    await els.cameraVideo.play();
  } catch (_) {
    // autoplay may be blocked until user interaction
  }
  await waitForVideoReady(els.cameraVideo, 6000);
  els.cameraModal.classList.remove('hidden');
}

function closeCameraModal() {
  state.camera.liveVerificationActive = false;
  state.camera.liveSessionToken += 1;
  if (state.camera.stream) {
    for (const track of state.camera.stream.getTracks()) {
      track.stop();
    }
  }

  state.camera.stream = null;
  state.camera.captureHandler = null;
  state.camera.burstFrames = 1;
  if (els.cameraReferenceWrap) {
    els.cameraReferenceWrap.classList.add('hidden');
  }
  if (els.cameraReferencePhoto) {
    els.cameraReferencePhoto.removeAttribute('src');
  }
  if (els.cameraCaptureBtn) {
    setHidden(els.cameraCaptureBtn, false);
    els.cameraCaptureBtn.disabled = false;
    els.cameraCaptureBtn.textContent = 'Capture';
  }
  els.cameraVideo.classList.remove('is-selfie');
  els.cameraVideo.srcObject = null;
  els.cameraModal.classList.add('hidden');
}

async function captureFromCamera() {
  if (!state.camera.stream) {
    throw new Error('Camera stream is not active.');
  }

  const captures = await captureBurstFramesFromCamera();
  const handler = state.camera.captureHandler;
  closeCameraModal();

  if (typeof handler === 'function') {
    if (captures.length > 1) {
      await handler(captures);
    } else {
      await handler(captures[0]);
    }
  }
}

async function captureBurstFramesFromCamera(frameCount = null, intervalMs = 120, quality = 0.92) {
  if (!state.camera.stream) {
    throw new Error('Camera stream is not active.');
  }

  if (!els.cameraVideo || !els.cameraCanvas) {
    throw new Error('Camera components are unavailable.');
  }

  await waitForVideoReady(els.cameraVideo, 2500);

  const sourceWidth = els.cameraVideo.videoWidth || 1280;
  const sourceHeight = els.cameraVideo.videoHeight || 720;
  const maxWidth = 640;
  let width = sourceWidth;
  let height = sourceHeight;
  if (sourceWidth > maxWidth) {
    const scale = maxWidth / sourceWidth;
    width = maxWidth;
    height = Math.max(240, Math.round(sourceHeight * scale));
  }

  els.cameraCanvas.width = width;
  els.cameraCanvas.height = height;

  const ctx = els.cameraCanvas.getContext('2d');
  if (!ctx) {
    throw new Error('Camera canvas unavailable.');
  }
  const burstFrames = Math.max(1, Number(frameCount || state.camera.burstFrames || 1));
  const captures = [];
  for (let i = 0; i < burstFrames; i += 1) {
    ctx.drawImage(els.cameraVideo, 0, 0, width, height);
    captures.push(els.cameraCanvas.toDataURL('image/jpeg', quality));
    if (i < burstFrames - 1) {
      await sleep(intervalMs);
    }
  }
  return captures;
}

function resolveVideoCaptureDimensions(videoElement, {
  maxWidth = 640,
  fallbackWidth = 1280,
  fallbackHeight = 720,
  minHeight = 240,
} = {}) {
  const sourceWidth = Math.max(1, Number(videoElement?.videoWidth || fallbackWidth));
  const sourceHeight = Math.max(1, Number(videoElement?.videoHeight || fallbackHeight));
  if (sourceWidth <= maxWidth) {
    return {
      width: sourceWidth,
      height: Math.max(minHeight, sourceHeight),
    };
  }
  const scale = maxWidth / sourceWidth;
  return {
    width: maxWidth,
    height: Math.max(minHeight, Math.round(sourceHeight * scale)),
  };
}

async function startEnrollmentGuidedCapture() {
  if (authState.user?.role !== 'student') {
    throw new Error('Enrollment video is available only for student accounts.');
  }
  if (state.student.enrollmentCaptureRunning) {
    throw new Error('Enrollment capture is already running.');
  }
  if (state.student.hasEnrollmentVideo && !state.student.enrollmentCanUpdateNow) {
    showEnrollmentLockPopup();
    throw new Error(
      `Enrollment video can only be updated after ${state.student.enrollmentLockDaysRemaining} day(s).`
    );
  }
  if (!els.enrollmentVideo || !els.enrollmentCanvas) {
    throw new Error('Enrollment UI is not available.');
  }

  const capturePlan = [
    {
      label: 'Step 1/6: Look straight',
      hint: 'Keep face centered, eye-level, and hold still.',
      frames: 6,
    },
    {
      label: 'Step 2/6: Turn slightly left',
      hint: 'Turn your head slightly left and keep your eyes visible.',
      frames: 5,
    },
    {
      label: 'Step 3/6: Turn slightly right',
      hint: 'Turn your head slightly right and keep your eyes visible.',
      frames: 5,
    },
    {
      label: 'Step 4/6: Tilt up',
      hint: 'Lift chin slightly up. Keep your full face in frame.',
      frames: 4,
    },
    {
      label: 'Step 5/6: Tilt down',
      hint: 'Tilt chin down slightly, keep forehead and eyes visible.',
      frames: 4,
    },
    {
      label: 'Step 6/6: Slow side-to-side sweep',
      hint: 'Move slowly left to right once, no fast movement.',
      frames: 8,
    },
  ];
  const totalTargetFrames = capturePlan.reduce((sum, step) => sum + step.frames, 0);
  const captureIntervalMs = 220;

  const stream = await navigator.mediaDevices.getUserMedia({
    video: {
      facingMode: { ideal: 'user' },
      width: { ideal: 1280 },
      height: { ideal: 720 },
      aspectRatio: { ideal: 4 / 3 },
      frameRate: { ideal: 30, max: 30 },
      resizeMode: 'crop-and-scale',
    },
    audio: false,
  });
  state.student.enrollmentStream = stream;
  els.enrollmentVideo.srcObject = stream;
  els.enrollmentVideo.classList.add('is-selfie');
  if (els.enrollmentVideoDemo) {
    els.enrollmentVideoDemo.classList.add('hidden');
  }
  try {
    await els.enrollmentVideo.play();
  } catch (_) {
    // autoplay may be blocked until user interaction
  }
  await waitForVideoReady(els.enrollmentVideo, 7000);
  await sleep(400);
  state.student.enrollmentFrames = [];
  state.student.enrollmentCaptureRunning = true;
  if (els.enrollmentSaveBtn) {
    els.enrollmentSaveBtn.disabled = true;
  }
  if (els.enrollmentStatus) {
    els.enrollmentStatus.textContent = 'Enrollment capture started. Follow each step exactly.';
  }
  if (els.enrollmentProgress) {
    els.enrollmentProgress.textContent = `Capture progress: 0% (0/${totalTargetFrames} frames)`;
  }

  const originalStartText = els.enrollmentStartBtn?.textContent || 'Start Guided Capture';
  if (els.enrollmentStartBtn) {
    els.enrollmentStartBtn.disabled = true;
    els.enrollmentStartBtn.textContent = 'Recording...';
  }

  try {
    const { width, height } = resolveVideoCaptureDimensions(els.enrollmentVideo, {
      maxWidth: 640,
      fallbackWidth: 1280,
      fallbackHeight: 720,
      minHeight: 360,
    });
    els.enrollmentCanvas.width = width;
    els.enrollmentCanvas.height = height;
    const ctx = els.enrollmentCanvas.getContext('2d');
    if (!ctx) {
      throw new Error('Enrollment capture canvas is unavailable.');
    }

    let capturedCount = 0;
    for (const step of capturePlan) {
      if (els.enrollmentInstruction) {
        els.enrollmentInstruction.textContent = `${step.label} - ${step.hint}`;
      }
      await sleep(350);
      for (let idx = 0; idx < step.frames; idx += 1) {
        ctx.drawImage(els.enrollmentVideo, 0, 0, width, height);
        state.student.enrollmentFrames.push(els.enrollmentCanvas.toDataURL('image/jpeg', 0.82));
        capturedCount += 1;
        if (els.enrollmentProgress) {
          const pct = Math.min(100, Math.round((capturedCount / totalTargetFrames) * 100));
          els.enrollmentProgress.textContent = `Capture progress: ${pct}% (${capturedCount}/${totalTargetFrames} frames)`;
        }
        await sleep(captureIntervalMs);
      }
    }

    if (els.enrollmentInstruction) {
      els.enrollmentInstruction.textContent = 'Capture complete. Review and save enrollment.';
    }
    if (els.enrollmentStatus) {
      els.enrollmentStatus.textContent = `Captured ${state.student.enrollmentFrames.length} frames successfully. Click Save Enrollment.`;
    }
    if (els.enrollmentProgress) {
      els.enrollmentProgress.textContent = `Capture progress: 100% (${state.student.enrollmentFrames.length}/${totalTargetFrames} frames)`;
    }
    if (els.enrollmentSaveBtn) {
      els.enrollmentSaveBtn.disabled = state.student.enrollmentFrames.length < 8;
    }
  } finally {
    stopEnrollmentCameraStream();
    state.student.enrollmentCaptureRunning = false;
    if (els.enrollmentStartBtn) {
      els.enrollmentStartBtn.disabled = false;
      els.enrollmentStartBtn.textContent = originalStartText;
    }
  }
}

async function saveStudentEnrollmentVideo() {
  if (authState.user?.role !== 'student') {
    throw new Error('Enrollment video is available only for student accounts.');
  }
  if (!state.student.enrollmentFrames.length) {
    throw new Error('Capture enrollment frames first.');
  }
  if (state.student.enrollmentFrames.length < 8) {
    throw new Error('Capture more frames. At least 8 valid frames are required.');
  }

  const originalText = els.enrollmentSaveBtn?.textContent || 'Save Enrollment';
  if (els.enrollmentSaveBtn) {
    els.enrollmentSaveBtn.disabled = true;
    els.enrollmentSaveBtn.textContent = 'Saving...';
  }

  try {
    const response = await api('/attendance/student/enrollment-video', {
      method: 'PUT',
      body: JSON.stringify({ frames_data_urls: state.student.enrollmentFrames }),
      timeoutMs: 120000,
    });

    state.student.hasEnrollmentVideo = Boolean(response.has_enrollment_video);
    state.student.enrollmentCanUpdateNow = Boolean(response.can_update_now);
    state.student.enrollmentLockedUntil = response.locked_until || null;
    state.student.enrollmentLockDaysRemaining = Number(response.lock_days_remaining || 0);
    state.student.enrollmentUpdatedAt = response.enrollment_updated_at || null;
    state.student.enrollmentLoaded = true;
    state.student.enrollmentFrames = [];
    state.student.enrollmentRequired = false;

    renderEnrollmentSummary();
    renderProfileSecurity();
    if (els.enrollmentStatus) {
      els.enrollmentStatus.textContent = `${response.message}. Valid frames used: ${response.valid_frames_used}.`;
    }
    if (els.enrollmentProgress) {
      els.enrollmentProgress.textContent = '';
    }
    closeEnrollmentModal();
    navigateSidebar('dashboard');
    log(`Enrollment video saved (${response.valid_frames_used}/${response.total_frames_received} frames)`);
  } finally {
    if (els.enrollmentSaveBtn) {
      els.enrollmentSaveBtn.textContent = originalText;
      els.enrollmentSaveBtn.disabled = false;
    }
  }
}

async function startStudentSelfieFlow() {
  const kpi = findAttendanceManagementState();
  const scheduleId = Number(kpi.schedule?.schedule_id || 0);
  if (kpi.mode !== 'mark' || !scheduleId) {
    throw new Error('Attendance window is closed right now. Wait for the next class.');
  }
  if (String(kpi.schedule?.class_kind || 'regular').toLowerCase() === 'remedial') {
    throw new Error('Remedial attendance is code-based. Open Remedial module and use faculty code within first 15 minutes.');
  }
  state.student.kpiScheduleId = scheduleId;
  state.student.selectedScheduleId = scheduleId;
  if (!state.student.registrationNumber) {
    throw new Error('Complete profile setup with registration number first.');
  }
  if (!state.student.profilePhotoDataUrl) {
    throw new Error('Upload profile photo first. It is required for facial attendance.');
  }
  if (requiresStudentEnrollmentSetup()) {
    throw new Error('Complete one-time enrollment video before marking attendance.');
  }
  await startLiveAttendanceVerification();
}

async function startStudentDemoAttendanceFlow(resolvedState = null) {
  const demoState = resolvedState?.mode === 'demo'
    ? resolvedState
    : findStudentDemoAttendanceState();
  if (!demoState || demoState.mode !== 'demo') {
    throw new Error('Demo attendance is disabled. Enable Demo Attendance first.');
  }
  if (!state.student.registrationNumber) {
    throw new Error('Complete profile setup with registration number first.');
  }
  if (!state.student.profilePhotoDataUrl) {
    throw new Error('Upload profile photo first. It is required for facial attendance.');
  }
  if (requiresStudentEnrollmentSetup()) {
    throw new Error('Complete one-time enrollment video before marking attendance.');
  }
  await startLiveAttendanceVerification({ demoMode: true, demoState });
}

async function startClassroomCaptureFlow() {
  await openCameraModal({
    title: 'Classroom Photo Capture',
    facingMode: 'environment',
    onCapture: async (photoDataUrl) => {
      state.faculty.classroomPhotoDataUrl = photoDataUrl;
      renderClassroomPhotoPreview(photoDataUrl);
      els.classroomAnalysisOutput.textContent = 'Classroom photo captured. Click Analyze & Save.';
    },
  });
}

async function aiAbsenceDraft() {
  const date = els.workDate.value;
  const courseId = Number(els.courseId.value);
  const absentNames = state.absentees.map((s) => `${s.name} <${s.email}>`).join(', ') || 'none';

  const prompt = [
    'You are a campus assistant.',
    `Draft a concise parent notification for absentees in course ID ${courseId} on ${date}.`,
    `Absentees: ${absentNames}.`,
    'Tone: formal, clear, 120 words max.',
  ].join('\n');

  await runPuter(prompt);
  log('AI generated parent absence notice');
}

async function aiRushPlan() {
  const date = els.workDate.value;
  const demandLines = state.demand
    .map((d) => `${d.slot_label}: ${d.orders}/${d.capacity} (${d.utilization_percent}%)`)
    .join('; ') || 'no demand data';

  const prompt = [
    'You are a canteen operations planner.',
    `Given slot demand for ${date}: ${demandLines}.`,
    'Recommend a short anti-congestion action plan with staffing and prep priorities.',
    'Output in bullet points.',
  ].join('\n');

  await runPuter(prompt);
  log('AI generated canteen rush strategy');
}

async function aiRemedialPlan() {
  const courseId = Number(els.courseId.value);
  const absentees = state.absentees.map((s) => s.name).join(', ') || 'none';

  const prompt = [
    'You are an academic coordinator.',
    `Create a remedial make-up class plan for course ID ${courseId}.`,
    `Students currently absent: ${absentees}.`,
    'Include objectives, 60-minute breakdown, and quick assessment method.',
  ].join('\n');

  await runPuter(prompt);
  log('AI generated remedial class plan');
}

function normalizedForgotEmailInput() {
  return (els.forgotEmail?.value || els.authEmail?.value || '').trim().toLowerCase();
}

function normalizedRegistrationInput(rawValue = '') {
  return String(rawValue || '').trim().toUpperCase().replace(/\s+/g, '');
}

function normalizedAuthUppercaseInput(rawValue = '', { compact = false } = {}) {
  const raw = String(rawValue || '').toUpperCase();
  return compact
    ? raw.replace(/\s+/g, '')
    : raw.replace(/\s+/g, ' ').trimStart();
}

async function requestForgotPasswordOtp() {
  const remaining = getForgotOtpCooldownRemainingSeconds();
  if (remaining > 0) {
    showOtpPopup(
      'OTP Cooldown Active',
      `Please wait ${remaining} seconds before requesting OTP again.`,
      { tone: 'cooldown' }
    );
    throw new Error(`Please wait ${remaining} seconds before requesting OTP again.`);
  }

  const email = normalizedForgotEmailInput();
  const registrationNumber = normalizedRegistrationInput(els.forgotRegistrationNumber?.value || '');
  if (!email || !registrationNumber) {
    throw new Error('Enter email and registration number first.');
  }
  if (!email.endsWith('@gmail.com')) {
    throw new Error('Email must end with @gmail.com');
  }
  authState.forgotResetToken = '';
  authState.forgotResetTokenExpiresAt = '';
  renderForgotOtpCooldown();

  setForgotOtpRequestInFlight(true);
  showOtpPopup(
    'Sending Reset OTP',
    'Validating account and delivering OTP to your email. This can take up to 60 seconds.',
    { tone: 'sending', loading: true, closable: false }
  );
  try {
    const data = await api('/auth/password/request-otp', {
      method: 'POST',
      timeoutMs: 60000,
      body: JSON.stringify({
        email,
        registration_number: registrationNumber,
      }),
      skipAuth: true,
    });

    if (els.forgotEmail) {
      els.forgotEmail.value = email;
    }
    authState.pendingEmail = email;
    const cooldownSeconds = Math.max(1, Number(data.cooldown_seconds || 30));
    startForgotOtpCooldown(cooldownSeconds);
    const validityMinutes = Math.max(1, Number(data.validity_minutes || 10));
    setForgotMessage(`Reset OTP sent. Valid for ${validityMinutes} minutes.`);
    showOtpPopup(
      'Reset OTP Sent',
      `OTP sent successfully. It is valid for ${validityMinutes} minutes.`,
      { tone: 'success', loading: false, closable: true }
    );
    log('Password reset OTP requested');
  } catch (error) {
    showOtpPopup(
      'Reset OTP Failed',
      String(error?.message || 'Unable to send reset OTP right now.'),
      { tone: 'danger', loading: false, closable: true }
    );
    throw error;
  } finally {
    setForgotOtpRequestInFlight(false);
  }
}

async function verifyForgotPasswordOtp() {
  const email = normalizedForgotEmailInput();
  const otpCode = (els.forgotOtp?.value || '').trim();
  if (!email || !otpCode) {
    throw new Error('Email and OTP code are required for verification.');
  }
  const data = await api('/auth/password/verify-otp', {
    method: 'POST',
    body: JSON.stringify({
      email,
      otp_code: otpCode,
    }),
    skipAuth: true,
  });
  authState.forgotResetToken = String(data.reset_token || '');
  authState.forgotResetTokenExpiresAt = String(data.expires_at || '');
  setForgotMessage('OTP verified. Set your new password below.');
  showOtpPopup(
    'OTP Verified',
    'OTP verified successfully. Set your new password now.',
    { tone: 'success', loading: false, closable: true }
  );
  renderForgotOtpCooldown();
  log('Password reset OTP verified');
}

async function resetForgotPassword() {
  const email = normalizedForgotEmailInput();
  const token = String(authState.forgotResetToken || '').trim();
  if (!email || !token) {
    throw new Error('Verify reset OTP first.');
  }
  const newPassword = String(els.forgotNewPassword?.value || '');
  const confirmPassword = String(els.forgotConfirmPassword?.value || '');
  if (!newPassword || !confirmPassword) {
    throw new Error('Enter and confirm your new password.');
  }
  if (newPassword !== confirmPassword) {
    throw new Error('New password and confirm password do not match.');
  }
  validatePasswordStrengthOrThrow(newPassword, 'New password');

  await api('/auth/password/reset', {
    method: 'POST',
    body: JSON.stringify({
      email,
      reset_token: token,
      new_password: newPassword,
    }),
    skipAuth: true,
  });

  showOtpPopup(
    'Password Updated',
    'Password reset successful. Login using your new password.',
    { tone: 'success', loading: false, closable: true }
  );
  setAuthMode('login');
  setForgotPasswordPanel(false);
  resetForgotPasswordState({ clearFields: true });
  if (els.authEmail) {
    els.authEmail.value = email;
  }
  if (els.authPassword) {
    els.authPassword.value = '';
  }
  setAuthMessage('Password reset successful. Login with your new password.');
  log('Password reset completed');
}

async function requestOtp() {
  if (authState.otpRequestInFlight) {
    return;
  }
  const remaining = getOtpCooldownRemainingSeconds();
  if (remaining > 0) {
    showOtpPopup(
      'OTP Cooldown Active',
      `Please wait ${remaining} seconds before requesting OTP again.`,
      { tone: 'cooldown' }
    );
    throw new Error(`Please wait ${remaining} seconds before requesting a new OTP.`);
  }

  const email = els.authEmail.value.trim().toLowerCase();
  const password = els.authPassword.value;

  if (!email || !password) {
    throw new Error('Enter email and password first.');
  }
  if (!email.endsWith('@gmail.com')) {
    throw new Error('Email must end with @gmail.com');
  }

  setOtpRequestInFlight(true);
  showOtpPopup(
    'Sending OTP',
    'Generating secure OTP and delivering it to your email. This can take up to 60 seconds.',
    { tone: 'sending', loading: true, closable: false }
  );
  setAuthMessage('Sending OTP... please wait.');
  try {
    const data = await api('/auth/login/request-otp', {
      method: 'POST',
      timeoutMs: 60000,
      body: JSON.stringify({
        email,
        password,
        send_to_alternate: false,
      }),
      skipAuth: true,
    });

    authState.pendingEmail = email;
    const cooldownSeconds = Math.max(1, Number(data.cooldown_seconds || 30));
    startOtpCooldown(cooldownSeconds);

    const validityMinutes = Math.max(1, Number(data.validity_minutes || 10));
    showOtpPopup(
      'OTP Sent',
      `OTP sent successfully. It is valid for ${validityMinutes} minutes.`,
      { tone: 'success', loading: false, closable: true }
    );
    setAuthMessage(`OTP sent. Valid for ${validityMinutes} minutes.`);

    log('OTP requested');
  } catch (error) {
    showOtpPopup(
      'OTP Request Failed',
      String(error?.message || 'Unable to send OTP right now.'),
      { tone: 'danger', loading: false, closable: true }
    );
    throw error;
  } finally {
    setOtpRequestInFlight(false);
  }
}

async function registerAccount() {
  if (authState.registerInFlight) {
    return;
  }
  if (!isSignupMode()) {
    setAuthMode('signup');
    throw new Error('Switch to Signup mode to register a new account.');
  }

  const role = selectedAuthRole();
  const email = (els.authSignupEmail?.value || '').trim().toLowerCase();
  const password = els.authSignupPassword?.value || '';
  const name = normalizedAuthUppercaseInput(els.authName?.value || '');
  const department = normalizedAuthUppercaseInput(els.authDepartment?.value || '');
  const registrationNumber = normalizedRegistrationInput(els.authSignupRegistration?.value || '');
  const facultyIdentifier = normalizedRegistrationInput(els.authSignupFacultyId?.value || '');
  const section = (els.authSignupSection?.value || '').trim().toUpperCase().replace(/\s+/g, '');
  const semesterValue = els.authSemester.value.trim();
  const parentEmail = els.authParentEmail.value.trim();
  const adminPhotoDataUrl = authState.signupAdminPhotoDataUrl || '';

  if (!email || !password || !name || !department) {
    throw new Error('Role, email, password, name, and department are required.');
  }
  validatePasswordStrengthOrThrow(password, 'Password');

  if (!email.endsWith('@gmail.com')) {
    throw new Error('Email must end with @gmail.com');
  }
  if (role === 'student') {
    if (!email.endsWith('@gmail.com')) {
      throw new Error('Email must end with @gmail.com');
    }
    if (!registrationNumber) {
      throw new Error('Registration number is required for student registration.');
    }
    if (!section) {
      throw new Error('Section is required for student registration.');
    }
    if (!semesterValue) {
      throw new Error('Semester is required for student registration.');
    }
  }
  if (role === 'faculty' && !facultyIdentifier) {
    throw new Error('Faculty identifier is required for faculty registration.');
  }
  if (role === 'admin' && !adminPhotoDataUrl) {
    throw new Error('Admin profile photo is required for registration.');
  }

  const payload = {
    email,
    password,
    role,
    name,
    department,
    profile_photo_data_url: role === 'admin' ? adminPhotoDataUrl : null,
    registration_number: role === 'student' ? registrationNumber : null,
    faculty_identifier: role === 'faculty' ? facultyIdentifier : null,
    section: role === 'student' ? section : null,
    semester: role === 'student' ? Number(semesterValue) : null,
    parent_email: role === 'student' ? (parentEmail || null) : null,
  };

  setRegisterInFlight(true);
  try {
    await api('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
      skipAuth: true,
    });
  } finally {
    setRegisterInFlight(false);
  }

  authState.pendingEmail = email;
  if (els.authEmail) {
    els.authEmail.value = email;
  }
  if (els.authSignupEmail) {
    els.authSignupEmail.value = '';
  }
  if (els.authSignupPassword) {
    els.authSignupPassword.value = '';
  }
  if (els.authSignupRegistration) {
    els.authSignupRegistration.value = '';
  }
  if (els.authSignupFacultyId) {
    els.authSignupFacultyId.value = '';
  }
  if (els.authSignupSection) {
    els.authSignupSection.value = '';
  }
  resetSignupAdminPhoto();
  setAuthMode('login');
  els.authPassword.value = '';
  renderPasswordStrengthHint(els.authPasswordStrength, '');
  renderPasswordStrengthHint(els.authSignupPasswordStrength, '');
  setAuthMessage('Registration successful. Now request OTP in Login mode. Profile setup popup will appear right after login.');
  log(`Registered ${role} account: ${email}`);
}

async function verifyOtpAndLogin() {
  if (authState.otpVerifyInFlight) {
    return;
  }
  const email = (els.authEmail.value.trim() || authState.pendingEmail).toLowerCase();
  const otpCode = els.authOtp.value.trim();
  const mfaCode = String(els.authMfaCode?.value || '').trim().replace(/\s+/g, '');

  if (!email || !otpCode) {
    throw new Error('Email and OTP code are required.');
  }

  setOtpVerifyInFlight(true);
  let data;
  try {
    data = await api('/auth/login/verify-otp', {
      method: 'POST',
      body: JSON.stringify({
        email,
        otp_code: otpCode,
        mfa_code: mfaCode || undefined,
      }),
      skipAuth: true,
    });
  } catch (error) {
    if (isMfaEnrollmentRequiredMessage(error?.message)) {
      await maybePromptPrivilegedMfaSetup(error.message);
    } else if (isMfaCodeRequiredMessage(error?.message)) {
      setAuthMfaInputVisible(true, 'Enter current authenticator code (or backup code), then verify OTP again.');
      if (els.authMfaCode) {
        els.authMfaCode.focus();
      }
    }
    throw error;
  } finally {
    setOtpVerifyInFlight(false);
  }

  setSession(data.access_token, data.user);
  if (els.authMfaCode) {
    els.authMfaCode.value = '';
  }
  const blockedByMfaEnrollment = await maybePromptPrivilegedMfaSetup();
  if (blockedByMfaEnrollment) {
    return;
  }
  setForgotPasswordPanel(false);
  resetForgotPasswordState({ clearFields: true });
  setAuthMessage('Login successful.');
  els.authOtp.value = '';
  els.authPassword.value = '';
  renderPasswordStrengthHint(els.authPasswordStrength, '');

  log(`Authenticated as ${data.user.role}`);
  renderProfileSecurity();
  await refreshAll();
}

async function restoreSession() {
  try {
    const user = await api('/auth/me', { skipAuth: !authState.token });
    authState.user = user;
    resetStudentProfileState();
    resetFacultyProfileState();
    state.ui.activeModule = defaultModuleForRole(user?.role);
    if (authState.user?.role === 'student') {
      state.student.profileLoaded = false;
    }
    applyTheme(getInitialTheme(user?.email || ''), { persist: false, userEmail: user?.email || '' });
    updateAuthBadges();
    const hashModule = moduleFromHash();
    setActiveModule(hashModule || defaultModuleForRole(user?.role), { updateHash: true });
    renderProfileSecurity();
    closeAuthOverlay();
    const blockedByMfaEnrollment = await maybePromptPrivilegedMfaSetup();
    if (blockedByMfaEnrollment) {
      stopStudentRealtimeTicker();
      stopModuleRealtimeTicker();
      return true;
    }
    if (authState.user?.role === 'student') {
      state.student.viewDate = todayISO();
      if (els.weekStartDate) {
        els.weekStartDate.value = state.student.viewDate;
      }
      startStudentRealtimeTicker();
    } else {
      stopStudentRealtimeTicker();
    }
    startModuleRealtimeTicker();
    startSessionWatchdog();
    void syncRealtimeEventBus();
    return true;
  } catch (_error) {
    clearSession();
    openAuthOverlay('Register (once), then login with email, password, and OTP.');
    return false;
  }
}

async function saveAlternateEmail() {
  if (!authState.user) {
    throw new Error('Sign in first.');
  }

  const raw = (els.profileAlternateEmail.value || '').trim().toLowerCase();
  const payload = {
    alternate_email: raw || null,
  };

  const user = await api('/auth/me/alternate-email', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });

  authState.user = user;
  updateAuthBadges();
  applyRoleUI();
  renderProfileSecurity();
  log('Alternate OTP email updated');
}

async function logout(message = 'Logged out. Sign in again to continue.') {
  closeAccountDropdown();
  closeAttendanceDetailsModal();
  if (els.profileModal) {
    els.profileModal.classList.add('hidden');
  }
  clearSession();
  openAuthOverlay(message);
  try {
    await api('/auth/logout', { method: 'POST', skipAuth: true });
  } catch (_error) {
    // Ignore logout API failures and always clear client session state.
  }
  log('Logged out');
}

function initParallax() {
  const layers = [...document.querySelectorAll('.parallax-layer[data-depth]')];
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReducedMotion || !layers.length) {
    return;
  }

  let pointerX = 0;
  let pointerY = 0;

  window.addEventListener('mousemove', (event) => {
    pointerX = event.clientX / window.innerWidth - 0.5;
    pointerY = event.clientY / window.innerHeight - 0.5;
  });

  function tick() {
    for (const layer of layers) {
      const depth = Number(layer.dataset.depth || 10);
      const tx = pointerX * depth;
      const ty = pointerY * depth;
      layer.style.transform = `translate3d(${tx}px, ${ty}px, 0)`;
    }
    requestAnimationFrame(tick);
  }

  tick();
}

function initTiltCards() {
  const cards = document.querySelectorAll('[data-tilt]');
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (prefersReducedMotion) {
    return;
  }

  for (const card of cards) {
    card.addEventListener('mousemove', (event) => {
      const rect = card.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width;
      const y = (event.clientY - rect.top) / rect.height;
      const rotateY = (x - 0.5) * 7;
      const rotateX = (0.5 - y) * 7;
      card.style.transform = `perspective(1200px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(0)`;
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  }
}

function flashSection(target) {
  if (!(target instanceof HTMLElement)) {
    return;
  }
  target.classList.remove('section-flash');
  // Force reflow so repeated clicks re-trigger the animation.
  void target.offsetWidth;
  target.classList.add('section-flash');
  window.setTimeout(() => target.classList.remove('section-flash'), 750);
}

function spawnMicroRipple(target, pointerEvent) {
  if (!(target instanceof HTMLElement)) {
    return;
  }
  const rect = target.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height) * 1.15;
  const ripple = document.createElement('span');
  ripple.className = 'micro-ripple';
  ripple.style.width = `${size}px`;
  ripple.style.height = `${size}px`;

  const fallbackX = rect.left + rect.width / 2;
  const fallbackY = rect.top + rect.height / 2;
  const clientX = Number.isFinite(pointerEvent?.clientX) ? pointerEvent.clientX : fallbackX;
  const clientY = Number.isFinite(pointerEvent?.clientY) ? pointerEvent.clientY : fallbackY;
  ripple.style.left = `${clientX - rect.left}px`;
  ripple.style.top = `${clientY - rect.top}px`;

  target.appendChild(ripple);
  ripple.addEventListener('animationend', () => ripple.remove(), { once: true });
}

function initMicroInteractions() {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReducedMotion) {
    return;
  }

  document.addEventListener('pointerdown', (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }
    const target = event.target.closest('.btn, .ums-side-item, .dropdown-item, .account-trigger, .course-clickable');
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.hasAttribute('disabled') || target.getAttribute('aria-disabled') === 'true') {
      return;
    }
    spawnMicroRipple(target, event);
  });
}

function initSaarthiAvatarAura() {
  const avatar = document.querySelector('#student-saarthi-card .saarthi-welcome-icon');
  if (!(avatar instanceof HTMLElement)) {
    return;
  }
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReducedMotion) {
    return;
  }

  const clamp01 = (value) => {
    if (!Number.isFinite(value)) {
      return 0.5;
    }
    return Math.min(1, Math.max(0, value));
  };

  const applyAvatarPose = (xRatio, yRatio, engaged = false) => {
    const x = clamp01(xRatio);
    const y = clamp01(yRatio);
    const deltaX = x - 0.5;
    const deltaY = y - 0.5;
    const tiltY = deltaX * 20;
    const tiltX = -deltaY * 20;
    const distance = Math.min(1, Math.hypot(deltaX, deltaY) / 0.72);
    const auraScale = 1 + (1 - distance) * 0.16;
    const auraAlpha = 0.58 + (1 - distance) * 0.26;

    avatar.style.setProperty('--saarthi-tilt-x', `${tiltX.toFixed(2)}deg`);
    avatar.style.setProperty('--saarthi-tilt-y', `${tiltY.toFixed(2)}deg`);
    avatar.style.setProperty('--saarthi-aura-x', `${(x * 100).toFixed(2)}%`);
    avatar.style.setProperty('--saarthi-aura-y', `${(y * 100).toFixed(2)}%`);
    avatar.style.setProperty('--saarthi-aura-scale', auraScale.toFixed(3));
    avatar.style.setProperty('--saarthi-aura-alpha', auraAlpha.toFixed(3));
    avatar.classList.toggle('is-interacting', Boolean(engaged));
  };

  const applyFromPointer = (event, engaged = true) => {
    const rect = avatar.getBoundingClientRect();
    if (!rect.width || !rect.height) {
      return;
    }
    const xRatio = (event.clientX - rect.left) / rect.width;
    const yRatio = (event.clientY - rect.top) / rect.height;
    applyAvatarPose(xRatio, yRatio, engaged);
  };

  const resetAvatarPose = () => {
    applyAvatarPose(0.5, 0.5, false);
    avatar.classList.remove('is-pressed');
  };

  avatar.addEventListener('pointerenter', (event) => {
    applyFromPointer(event, true);
  });
  avatar.addEventListener('pointermove', (event) => {
    applyFromPointer(event, true);
  });
  avatar.addEventListener('pointerleave', () => {
    resetAvatarPose();
  });
  avatar.addEventListener('pointerdown', (event) => {
    avatar.classList.add('is-pressed');
    applyFromPointer(event, true);
  });
  avatar.addEventListener('pointerup', () => {
    avatar.classList.remove('is-pressed');
  });
  avatar.addEventListener('pointercancel', () => {
    resetAvatarPose();
  });
  window.addEventListener('blur', () => {
    resetAvatarPose();
  });

  resetAvatarPose();
}

async function refreshAll() {
  if (!authState.user) {
    return;
  }

  let failed = 0;

  try {
    await loadCoursesMap();
  } catch (error) {
    failed += 1;
    log(error.message || 'Failed to load course metadata');
  }

  const role = authState.user.role;

  if (role === 'student') {
    startStudentRealtimeTicker();
  } else {
    stopStudentRealtimeTicker();
  }

  if (role === 'student') {
    const studentSteps = [
      () => loadStudentProfilePhoto(),
      () => refreshStudentTimetableSurface({ forceNetwork: true }),
      () => loadStudentAttendanceInsights(),
      () => loadSaarthiStatus({ silent: true }),
      () => refreshRemedialMessages(),
      () => refreshSupportDeskContext({ silent: true, refreshThread: false }),
    ];

    for (const step of studentSteps) {
      try {
        await step();
      } catch (error) {
        failed += 1;
        log(error.message || 'A dashboard section failed to load');
      }
    }

    if (state.ui.activeModule !== 'attendance') {
      try {
        await refreshActiveModuleData();
      } catch (error) {
        failed += 1;
        log(error.message || 'The active module failed to load');
      }
    }

    if (failed === 0) {
      log('Dashboard telemetry refreshed');
    } else {
      log(`Dashboard refreshed with ${failed} section error(s)`);
    }
    return;
  } else {
    const tasks = [];
    if (role === 'admin') {
      tasks.push(refreshAdminLive({
        workDate: els.workDate?.value || todayISO(),
        mode: 'enrollment',
      }));
      if (!state.admin?.insights) {
        tasks.push(refreshAdminInsights({
          workDate: els.workDate?.value || todayISO(),
          mode: 'enrollment',
        }));
      }
    }
    tasks.push(refreshAttendanceData());
    tasks.push(refreshDemand());

    if (role === 'faculty' || role === 'admin') {
      if (role === 'faculty') {
        tasks.push(loadFacultyProfile());
      }
      tasks.push(loadFacultySchedules());
      if (role === 'faculty') {
        tasks.push(refreshSupportDeskContext({ silent: true, refreshThread: false }));
      }
    }

    const results = await Promise.allSettled(tasks);
    for (const result of results) {
      if (result.status === 'rejected') {
        failed += 1;
        log(result.reason?.message || 'A dashboard section failed to load');
      }
    }

    try {
      await refreshActiveModuleData();
    } catch (error) {
      failed += 1;
      log(error.message || 'The active module failed to load');
    }
  }

  if (failed === 0) {
    log('Dashboard telemetry refreshed');
  } else {
    log(`Dashboard refreshed with ${failed} section error(s)`);
  }
}

function bindEvents() {
  bindAdminSubmodulePickers();

  document.getElementById('refresh-btn').addEventListener('click', async () => {
    try {
      await refreshAll();
    } catch (error) {
      log(error.message);
    }
  });

  document.getElementById('ai-absent-btn').addEventListener('click', async () => {
    try {
      await aiAbsenceDraft();
    } catch (error) {
      log(error.message);
    }
  });

  document.getElementById('ai-rush-btn').addEventListener('click', async () => {
    try {
      await aiRushPlan();
    } catch (error) {
      log(error.message);
    }
  });

  document.getElementById('ai-remedial-btn').addEventListener('click', async () => {
    try {
      await aiRemedialPlan();
    } catch (error) {
      log(error.message);
    }
  });

  document.getElementById('request-otp-btn').addEventListener('click', async () => {
    try {
      await requestOtp();
    } catch (error) {
      if (error?.status === 429) {
        const retrySeconds = Math.max(1, Number(error.retryAfterSeconds || 30));
        startOtpCooldown(retrySeconds);
        showOtpPopup(
          'OTP Cooldown Active',
          `Please wait ${retrySeconds} seconds before requesting OTP again.`,
          { tone: 'cooldown', loading: false, closable: true }
        );
      }
      setAuthMessage(error.message, true);
      log(error.message);
    }
  });

  document.getElementById('verify-otp-btn').addEventListener('click', async () => {
    try {
      await verifyOtpAndLogin();
    } catch (error) {
      setAuthMessage(error.message, true);
      log(error.message);
    }
  });

  document.getElementById('register-btn').addEventListener('click', async () => {
    try {
      await registerAccount();
    } catch (error) {
      setAuthMessage(error.message, true);
      log(error.message);
    }
  });

  if (els.forgotPasswordToggleBtn) {
    els.forgotPasswordToggleBtn.addEventListener('click', () => {
      setForgotPasswordPanel(true);
    });
  }

  if (els.forgotCancelBtn) {
    els.forgotCancelBtn.addEventListener('click', () => {
      setForgotPasswordPanel(false);
      setForgotMessage('');
    });
  }

  if (els.forgotModalCloseBtn) {
    els.forgotModalCloseBtn.addEventListener('click', () => {
      setForgotPasswordPanel(false);
    });
  }

  if (els.forgotRequestOtpBtn) {
    els.forgotRequestOtpBtn.addEventListener('click', async () => {
      try {
        await requestForgotPasswordOtp();
      } catch (error) {
        if (error?.status === 429) {
          const retrySeconds = Math.max(1, Number(error.retryAfterSeconds || 30));
          startForgotOtpCooldown(retrySeconds);
        }
        setForgotMessage(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.forgotVerifyOtpBtn) {
    els.forgotVerifyOtpBtn.addEventListener('click', async () => {
      try {
        await verifyForgotPasswordOtp();
      } catch (error) {
        setForgotMessage(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.forgotResetBtn) {
    els.forgotResetBtn.addEventListener('click', async () => {
      try {
        await resetForgotPassword();
      } catch (error) {
        setForgotMessage(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.mfaEnrollBtn) {
    els.mfaEnrollBtn.addEventListener('click', async () => {
      try {
        await enrollMfaSetup();
      } catch (error) {
        log(error.message || 'MFA enrollment setup failed');
      }
    });
  }

  if (els.mfaActivateBtn) {
    els.mfaActivateBtn.addEventListener('click', async () => {
      try {
        await activateMfaSetup();
      } catch (error) {
        log(error.message || 'MFA activation failed');
      }
    });
  }

  if (els.mfaLogoutBtn) {
    els.mfaLogoutBtn.addEventListener('click', async () => {
      try {
        await logout('Logged out. Login again to continue MFA setup when ready.');
      } catch (error) {
        log(error.message || 'Logout failed');
      }
    });
  }

  if (els.mfaHelpOpenBtn) {
    els.mfaHelpOpenBtn.addEventListener('click', () => {
      const email = String(authState.user?.email || '').trim().toLowerCase();
      if (email) {
        markMfaGuidePromptSeen(email);
      }
      setMfaHelpModal(true);
    });
  }

  if (els.mfaHelpCloseBtn) {
    els.mfaHelpCloseBtn.addEventListener('click', () => {
      setMfaHelpModal(false);
    });
  }

  if (els.mfaHelpGotItBtn) {
    els.mfaHelpGotItBtn.addEventListener('click', () => {
      setMfaHelpModal(false);
      if (els.mfaEnrollBtn) {
        els.mfaEnrollBtn.focus({ preventScroll: true });
      }
    });
  }

  if (els.mfaCopySecretBtn) {
    els.mfaCopySecretBtn.addEventListener('click', async () => {
      const value = String(els.mfaSecret?.value || '').trim();
      if (!value) {
        setMfaSetupMessage('Generate MFA setup first to copy secret.', true);
        return;
      }
      const copied = await copyTextToClipboard(value);
      if (!copied) {
        setMfaSetupMessage('Copy failed. Please paste manually from this field.', true);
        return;
      }
      showMfaCopyButtonFeedback(els.mfaCopySecretBtn);
      setMfaSetupMessage('Authenticator secret copied. Paste it into Microsoft Authenticator setup key field.', false, 'success');
    });
  }

  if (els.mfaCopyUriBtn) {
    els.mfaCopyUriBtn.addEventListener('click', async () => {
      const value = String(els.mfaOtpauthUri?.value || '').trim();
      if (!value) {
        setMfaSetupMessage('Generate MFA setup first to copy OTPAuth URI.', true);
        return;
      }
      const copied = await copyTextToClipboard(value);
      if (!copied) {
        setMfaSetupMessage('Copy failed. Please paste manually from this field.', true);
        return;
      }
      showMfaCopyButtonFeedback(els.mfaCopyUriBtn);
      setMfaSetupMessage('OTPAuth URI copied. Use it in apps that support URI import.', false, 'success');
    });
  }

  if (els.mfaQrConfirm) {
    els.mfaQrConfirm.addEventListener('change', () => {
      setMfaActionBusyState();
    });
  }

  if (els.mfaTotpCode) {
    els.mfaTotpCode.addEventListener('input', () => {
      els.mfaTotpCode.value = String(els.mfaTotpCode.value || '').replace(/\D+/g, '').slice(0, 6);
      setMfaActionBusyState();
    });
    els.mfaTotpCode.addEventListener('keydown', async (event) => {
      if (event.key !== 'Enter') {
        return;
      }
      event.preventDefault();
      try {
        await activateMfaSetup();
      } catch (error) {
        log(error.message || 'MFA activation failed');
      }
    });
  }

  els.authModeLoginBtn.addEventListener('click', () => {
    setAuthMode('login');
    setForgotPasswordPanel(false);
  });

  els.authModeSignupBtn.addEventListener('click', () => {
    setAuthMode('signup');
  });

  if (els.otpPopupCloseBtn) {
    els.otpPopupCloseBtn.addEventListener('click', () => {
      hideOtpPopup();
    });
  }
  if (els.foodToastCloseBtn) {
    els.foodToastCloseBtn.addEventListener('click', () => {
      hideFoodToast();
    });
  }

  if (els.forgotPasswordPanel) {
    els.forgotPasswordPanel.addEventListener('click', (event) => {
      if (event.target === els.forgotPasswordPanel) {
        setForgotPasswordPanel(false);
      }
    });
  }

  if (els.mfaHelpModal) {
    els.mfaHelpModal.addEventListener('click', (event) => {
      if (event.target === els.mfaHelpModal) {
        setMfaHelpModal(false);
      }
    });
  }

  els.authRoleSelect.addEventListener('change', () => {
    syncAuthRoleForm();
  });

  if (els.authEmail) {
    els.authEmail.addEventListener('input', () => {
      const value = els.authEmail.value.trim().toLowerCase();
      if (els.forgotEmail && !els.forgotEmail.value.trim()) {
        els.forgotEmail.value = value;
      }
    });
  }

  if (els.authPassword) {
    els.authPassword.addEventListener('input', () => {
      renderPasswordStrengthHint(els.authPasswordStrength, els.authPassword.value || '');
    });
  }

  if (els.authSignupPassword) {
    els.authSignupPassword.addEventListener('input', () => {
      renderPasswordStrengthHint(els.authSignupPasswordStrength, els.authSignupPassword.value || '');
    });
  }

  if (els.authSignupRegistration) {
    els.authSignupRegistration.addEventListener('input', () => {
      els.authSignupRegistration.value = normalizedRegistrationInput(els.authSignupRegistration.value || '');
    });
  }

  if (els.authSignupFacultyId) {
    els.authSignupFacultyId.addEventListener('input', () => {
      els.authSignupFacultyId.value = normalizedRegistrationInput(els.authSignupFacultyId.value || '');
    });
  }

  if (els.authName) {
    els.authName.addEventListener('input', () => {
      els.authName.value = normalizedAuthUppercaseInput(els.authName.value || '');
    });
  }

  if (els.authDepartment) {
    els.authDepartment.addEventListener('input', () => {
      els.authDepartment.value = normalizedAuthUppercaseInput(els.authDepartment.value || '');
    });
  }

  if (els.authSignupSection) {
    els.authSignupSection.addEventListener('input', () => {
      els.authSignupSection.value = normalizedAuthUppercaseInput(els.authSignupSection.value || '', { compact: true });
    });
  }

  if (els.authSignupAdminPhoto) {
    els.authSignupAdminPhoto.addEventListener('change', async () => {
      const file = els.authSignupAdminPhoto.files?.[0];
      if (!file) {
        resetSignupAdminPhoto();
        return;
      }
      if (!file.type || !file.type.startsWith('image/')) {
        resetSignupAdminPhoto();
        setAuthMessage('Admin photo must be an image file.');
        return;
      }
      try {
        const dataUrl = await fileToDataUrl(file);
        authState.signupAdminPhotoDataUrl = dataUrl;
        setSignupAdminPhotoPreview(dataUrl);
      } catch (error) {
        resetSignupAdminPhoto();
        setAuthMessage(String(error?.message || 'Unable to read selected photo.'));
      }
    });
  }

  if (els.forgotRegistrationNumber) {
    els.forgotRegistrationNumber.addEventListener('input', () => {
      const value = normalizedRegistrationInput(els.forgotRegistrationNumber.value || '');
      els.forgotRegistrationNumber.value = value;
    });
  }

  if (els.forgotNewPassword) {
    els.forgotNewPassword.addEventListener('input', () => {
      renderPasswordStrengthHint(els.forgotPasswordStrength, els.forgotNewPassword.value || '');
    });
  }

  const navButtons = [els.navDashboardBtn, els.navCoursesBtn, els.navAttendanceBtn].filter(Boolean);
  for (const button of navButtons) {
    button.addEventListener('click', () => {
      navigateSidebar(button.dataset.nav || 'dashboard');
    });
  }

  const topModuleButtons = [
    els.topNavAttendanceBtn,
    els.topNavSaarthiBtn,
    els.topNavFoodBtn,
    els.topNavAdministrativeBtn,
    els.topNavRmsBtn,
    els.topNavRemedialBtn,
  ].filter(Boolean);
  for (const button of topModuleButtons) {
    button.addEventListener('click', async () => {
      if (!authState.user) {
        openAuthOverlay('Sign in to access modules.');
        return;
      }
      if (requiresRoleProfileSetup()) {
        openProfileModal({ required: true });
        return;
      }
      if (authState.user.role === 'student' && requiresStudentEnrollmentSetup()) {
        openEnrollmentModal({ required: true });
        return;
      }
      const requestedModule = button.dataset.module || 'attendance';
      setActiveModule(requestedModule, { updateHash: true });
      try {
        await refreshActiveModuleData();
      } catch (error) {
        log(error.message);
      }
    });
  }

  window.addEventListener('hashchange', async () => {
    if (!authState.user) {
      return;
    }
    if (requiresRoleProfileSetup()) {
      openProfileModal({ required: true });
      return;
    }
    if (authState.user.role === 'student' && requiresStudentEnrollmentSetup()) {
      openEnrollmentModal({ required: true });
      return;
    }
    const hashModule = moduleFromHash();
    if (!hashModule) {
      return;
    }
    setActiveModule(hashModule, { updateHash: false });
    try {
      await refreshActiveModuleData();
    } catch (error) {
      log(error.message);
    }
  });

  if (els.themeToggleBtn) {
    els.themeToggleBtn.addEventListener('click', () => {
      toggleTheme();
    });
  }

  if (els.accountMenuBtn) {
    els.accountMenuBtn.addEventListener('click', () => {
      if (!authState.user) {
        openAuthOverlay('Sign in to access account menu.');
        return;
      }
      const nextHidden = !els.accountMenuDropdown?.classList.contains('hidden');
      if (nextHidden) {
        closeAccountDropdown();
      } else {
        els.accountMenuDropdown?.classList.remove('hidden');
        els.accountMenuBtn.setAttribute('aria-expanded', 'true');
      }
    });
  }

  document.addEventListener('click', (event) => {
    if (!els.accountMenuDropdown || !els.accountMenuBtn) {
      return;
    }
    const target = event.target;
    if (!(target instanceof Node)) {
      return;
    }
    if (els.accountMenuDropdown.contains(target) || els.accountMenuBtn.contains(target)) {
      return;
    }
    closeAccountDropdown();
  });

  if (els.viewProfileBtn) {
    els.viewProfileBtn.addEventListener('click', () => {
      closeAccountDropdown();
      openProfileModal({ required: requiresRoleProfileSetup() });
    });
  }

  if (els.accountMfaSetupBtn) {
    els.accountMfaSetupBtn.addEventListener('click', async () => {
      closeAccountDropdown();
      try {
        await openMfaSetupFromAccountMenu();
      } catch (error) {
        const message = error?.message || 'Unable to open MFA setup right now.';
        openAuthOverlay(message);
        setAuthMessage(message, true);
        log(message);
      }
    });
  }

  els.authPassword.addEventListener('keydown', async (event) => {
    if (event.key !== 'Enter' || isSignupMode() || isForgotPasswordPanelOpen()) {
      return;
    }
    event.preventDefault();
    try {
      await requestOtp();
    } catch (error) {
      if (error?.status === 429) {
        const retrySeconds = Math.max(1, Number(error.retryAfterSeconds || 30));
        startOtpCooldown(retrySeconds);
        showOtpPopup(
          'OTP Cooldown Active',
          `Please wait ${retrySeconds} seconds before requesting OTP again.`,
          { tone: 'cooldown', loading: false, closable: true }
        );
      }
      setAuthMessage(error.message, true);
      log(error.message);
    }
  });

  els.authOtp.addEventListener('keydown', async (event) => {
    if (event.key !== 'Enter' || isSignupMode() || isForgotPasswordPanelOpen()) {
      return;
    }
    event.preventDefault();
    try {
      await verifyOtpAndLogin();
    } catch (error) {
      setAuthMessage(error.message, true);
      log(error.message);
    }
  });

  if (els.forgotOtp) {
    els.forgotOtp.addEventListener('keydown', async (event) => {
      if (event.key !== 'Enter' || !isForgotPasswordPanelOpen()) {
        return;
      }
      event.preventDefault();
      try {
        await verifyForgotPasswordOtp();
      } catch (error) {
        setForgotMessage(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.forgotConfirmPassword) {
    els.forgotConfirmPassword.addEventListener('keydown', async (event) => {
      if (event.key !== 'Enter' || !isForgotPasswordPanelOpen()) {
        return;
      }
      event.preventDefault();
      try {
        await resetForgotPassword();
      } catch (error) {
        setForgotMessage(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.authSignupPassword) {
    els.authSignupPassword.addEventListener('keydown', async (event) => {
      if (event.key !== 'Enter' || !isSignupMode()) {
        return;
      }
      event.preventDefault();
      try {
        await registerAccount();
      } catch (error) {
        setAuthMessage(error.message, true);
        log(error.message);
      }
    });
  }

  els.logoutBtn.addEventListener('click', () => {
    closeAccountDropdown();
    logout();
  });
  els.accountLogoutBtn.addEventListener('click', logout);
  els.saveAlternateEmailBtn.addEventListener('click', async () => {
    try {
      await saveAlternateEmail();
    } catch (error) {
      log(error.message);
      if (els.alternateEmailStatus) {
        els.alternateEmailStatus.textContent = error.message;
      }
    }
  });

  if (els.loadTimetableBtn) {
    els.loadTimetableBtn.addEventListener('click', async () => {
      try {
        await loadStudentTimetable({ forceNetwork: true });
        log('Student timetable refreshed');
      } catch (error) {
        log(error.message);
      }
    });
  }

  if (els.weekStartDate) {
    els.weekStartDate.addEventListener('change', async () => {
      try {
        await loadStudentTimetable();
        log('Timetable date updated');
      } catch (error) {
        log(error.message);
      }
    });
  }

  els.goCurrentWeekBtn.addEventListener('click', async () => {
    try {
      els.weekStartDate.value = todayISO();
      await loadStudentTimetable();
      log('Moved timetable to today');
    } catch (error) {
      log(error.message);
    }
  });

  if (els.prevWeekBtn) {
    els.prevWeekBtn.addEventListener('click', async () => {
      try {
        const current = els.weekStartDate.value || state.student.viewDate || todayISO();
        const minDate = state.student.minTimetableDate || STUDENT_TIMETABLE_START_DATE;
        const candidate = shiftISODate(current, -7);
        const clamped = clampStudentViewDate(candidate);
        if (clamped === current && weekStartISO(current) <= weekStartISO(minDate)) {
          log(`Cannot go before class start date (${parseISODateLocal(minDate).toLocaleDateString()}).`);
          return;
        }
        els.weekStartDate.value = clamped;
        await loadStudentTimetable();
        log('Moved timetable view to previous week');
      } catch (error) {
        log(error.message);
      }
    });
  }

  if (els.nextWeekBtn) {
    els.nextWeekBtn.addEventListener('click', async () => {
      try {
        const current = els.weekStartDate.value || state.student.viewDate || todayISO();
        els.weekStartDate.value = shiftISODate(current, 7);
        await loadStudentTimetable();
        log('Moved timetable view to next week');
      } catch (error) {
        log(error.message);
      }
    });
  }

  if (els.foodOrderDate) {
    const openNativeDatePicker = () => {
      const picker = els.foodOrderDate;
      if (!picker || typeof picker.showPicker !== 'function') {
        return;
      }
      try {
        picker.showPicker();
      } catch (_) {
        // Some browsers can throw if picker is blocked by user gesture policy.
      }
    };
    els.foodOrderDate.addEventListener('click', openNativeDatePicker);
    els.foodOrderDate.addEventListener('focus', openNativeDatePicker);
    els.foodOrderDate.addEventListener('change', async () => {
      try {
        if (authState.user?.role === 'student') {
          clampFoodOrderDateToToday({ showNotice: true });
        } else {
          state.food.orderDate = String(els.foodOrderDate.value || todayISO()).trim() || todayISO();
        }
        await refreshFoodModule();
      } catch (error) {
        setFoodStatus(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.foodItemSelect) {
    els.foodItemSelect.addEventListener('change', () => {
      syncFoodOrderActionState();
    });
  }

  if (els.foodSlotSelect) {
    els.foodSlotSelect.addEventListener('change', () => {
      const selectedHint = state.food.slotHintsById?.[String(els.foodSlotSelect.value || '')] || null;
      els.foodSlotSelect.dataset.hint = selectedHint?.kind || 'none';
      setFoodCheckoutPreviewOpen(false);
      const orderGate = getFoodRuntimeOrderGate({ slot: getSelectedFoodSlot() });
      if (!orderGate.canOrderNow) {
        setFoodStatus(orderGate.message, true);
      }
    });
  }

  if (els.foodOrdersTabCurrent) {
    els.foodOrdersTabCurrent.addEventListener('click', () => {
      state.food.ordersTab = 'current';
      renderFoodOrders();
    });
  }

  if (els.foodOrdersTabPrevious) {
    els.foodOrdersTabPrevious.addEventListener('click', () => {
      state.food.ordersTab = 'previous';
      renderFoodOrders();
    });
  }

  if (els.foodDemandLiveHotBtn) {
    els.foodDemandLiveHotBtn.addEventListener('click', () => {
      const hotSlotId = resolveFoodDemandHotSlotId(getFoodDemandRowsInDisplayOrder());
      if (hotSlotId <= 0) {
        return;
      }
      state.food.demandSelectedSlotId = hotSlotId;
      renderFoodDemandMinimalChart({ animate: true });
      showFoodToast('Hot Slot Focused', 'Showing the highest live activity slot right now.', { autoHideMs: 1400 });
    });
  }

  if (els.foodOpenCartBtn) {
    els.foodOpenCartBtn.addEventListener('click', () => {
      openFoodCartModal();
    });
  }

  if (els.foodCartTabCartBtn) {
    els.foodCartTabCartBtn.addEventListener('click', () => {
      setFoodCartModalTab('cart');
      syncFoodOrderActionState();
    });
  }

  if (els.foodCartTabReviewBtn) {
    els.foodCartTabReviewBtn.addEventListener('click', () => {
      try {
        openFoodCheckoutPreview();
      } catch (error) {
        setFoodStatus(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.foodEnableLocationBtn) {
    els.foodEnableLocationBtn.addEventListener('click', async () => {
      try {
        await verifyFoodLocationGate({ forcePrompt: true });
      } catch (error) {
        setFoodLocationStatus(error.message, 'error');
        log(error.message);
      }
    });
  }

  if (els.foodDemoToggleBtn) {
    els.foodDemoToggleBtn.addEventListener('click', () => {
      const nextEnabled = !isFoodDemoEnabled();
      setFoodDemoEnabled(nextEnabled);
      setFoodStatus(
        nextEnabled
          ? 'Food Hall demo bypass enabled. Orders can ignore normal constraints temporarily.'
          : 'Food Hall demo bypass disabled. Normal ordering rules are active again.',
        false,
      );
    });
  }

  if (els.foodCartCheckoutBtn) {
    els.foodCartCheckoutBtn.addEventListener('click', async () => {
      try {
        openFoodCheckoutPreview();
        showFoodPopup('Checkout Ready', 'Review items and delivery block, then complete payment.', { autoHideMs: 1400 });
      } catch (error) {
        setFoodStatus(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.foodDeliveryBlockSelect) {
    els.foodDeliveryBlockSelect.addEventListener('change', () => {
      state.food.checkoutDeliveryPoint = String(els.foodDeliveryBlockSelect.value || '').trim();
      renderFoodCheckoutPreview();
      syncFoodOrderActionState();
      void persistFoodCartUiState();
    });
  }

  if (els.foodCartPayBtn) {
    els.foodCartPayBtn.addEventListener('click', async () => {
      try {
        await placeFoodOrder();
      } catch (error) {
        setFoodStatus(error.message, true);
        showFoodPopup('Checkout Error', error.message || 'Payment checkout failed. Please retry.', { isError: true, autoHideMs: 2800 });
        log(error.message);
      }
    });
  }

  if (els.foodCartBackBtn) {
    els.foodCartBackBtn.addEventListener('click', () => {
      setFoodCartModalTab('cart');
      syncFoodOrderActionState();
    });
  }

  if (els.foodCartClearBtn) {
    els.foodCartClearBtn.addEventListener('click', async () => {
      try {
        await clearFoodCart();
        showFoodPopup('Cart Cleared', 'All items were removed from your cart.', { autoHideMs: 1300 });
      } catch (error) {
        setFoodStatus(error.message || 'Unable to clear cart right now.', true);
      }
    });
  }

  if (els.foodCreateItemBtn) {
    els.foodCreateItemBtn.addEventListener('click', async () => {
      try {
        await createFoodItem();
        log('Food item created');
      } catch (error) {
        setFoodStatus(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.foodCreateSlotBtn) {
    els.foodCreateSlotBtn.addEventListener('click', async () => {
      try {
        await createFoodSlot();
        log('Food slot created');
      } catch (error) {
        setFoodStatus(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.foodAdminUpdateStatusBtn) {
    els.foodAdminUpdateStatusBtn.addEventListener('click', async () => {
      try {
        await updateFoodOrderStatus();
        log('Food order status updated');
      } catch (error) {
        setFoodAdminStatus(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.foodShopModalCloseBtn) {
    els.foodShopModalCloseBtn.addEventListener('click', () => {
      closeFoodShopModal();
    });
  }

  if (els.foodAiSuggestBtn) {
    els.foodAiSuggestBtn.addEventListener('click', async () => {
      try {
        await askChotuFoodAssistant();
      } catch (error) {
        log(error.message || 'Chotu assistant request failed');
      }
    });
  }

  if (els.foodAiCravingInput) {
    els.foodAiCravingInput.addEventListener('keydown', async (event) => {
      if (event.key !== 'Enter') {
        return;
      }
      event.preventDefault();
      try {
        await askChotuFoodAssistant();
      } catch (error) {
        log(error.message || 'Chotu assistant request failed');
      }
    });
  }
  if (els.chotuToggleBtn) {
    els.chotuToggleBtn.addEventListener('click', () => {
      if (!authState.user) {
        return;
      }
      toggleChotuOpen();
    });
  }
  if (els.chotuMinimizeBtn) {
    els.chotuMinimizeBtn.addEventListener('click', () => {
      setChotuOpen(false);
    });
  }
  if (els.chotuWidget) {
    document.addEventListener('click', (event) => {
      if (!state.ui.chotuOpen || !authState.user) {
        return;
      }
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      if (els.chotuWidget.contains(target)) {
        return;
      }
      setChotuOpen(false);
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && state.ui.chotuOpen) {
        setChotuOpen(false);
      }
    });
  }

  if (els.verlynToggleBtn) {
    els.verlynToggleBtn.addEventListener('click', () => {
      toggleVerlynOpen();
      if (state.ui.verlynOpen) {
        setVerlynStatus('Ready.');
        renderVerlynQuickActions();
        if (els.verlynOutput) {
          els.verlynOutput.textContent = getVerlynDefaultOutput();
        }
        els.verlynInput?.focus();
      }
    });
  }
  if (els.verlynMinimizeBtn) {
    els.verlynMinimizeBtn.addEventListener('click', () => {
      setVerlynOpen(false);
    });
  }
  if (els.verlynAskBtn) {
    els.verlynAskBtn.addEventListener('click', () => {
      void askVerlyn();
    });
  }
  if (els.verlynQuickActions) {
    els.verlynQuickActions.addEventListener('click', async (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const actionButton = target.closest('button[data-verlyn-action]');
      if (!(actionButton instanceof HTMLButtonElement)) {
        return;
      }
      event.preventDefault();
      const action = String(actionButton.dataset.verlynAction || '').trim().toLowerCase();
      try {
        if (action === 'attendance_blocker') {
          await runVerlynCopilot({ query_text: "Why can't I mark attendance?" });
          return;
        }
        if (action === 'eligibility_risk') {
          await runVerlynCopilot({ query_text: 'What do I need to fix before I lose eligibility?' });
          return;
        }
        if (action === 'student_module_summary') {
          await runVerlynCopilot({ query_text: 'Summarize my pending tasks across attendance, food, Saarthi, and remedial.' });
          return;
        }
        if (action === 'owner_food_summary') {
          await runVerlynCopilot({ query_text: 'Summarize active food orders and delivery flow for my shops today.' });
          return;
        }
        if (action === 'focus_audit_timeline') {
          focusAdminCopilotAuditTimeline({ refresh: true });
        }
      } catch (error) {
        setVerlynStatus(error?.message || 'Quick action failed.', true, 'error');
      }
    });
    els.verlynQuickActions.addEventListener('submit', async (event) => {
      const form = event.target;
      if (!(form instanceof HTMLFormElement)) {
        return;
      }
      const action = String(form.dataset.verlynAction || '').trim().toLowerCase();
      event.preventDefault();
      try {
        if (action === 'flag_reason') {
          await runVerlynCopilot(buildVerlynFlagPayload());
          return;
        }
        if (action === 'create_remedial_plan') {
          await runVerlynCopilot(buildVerlynRemedialPayload());
        }
      } catch (error) {
        setVerlynStatus(error?.message || 'Quick action failed.', true, 'error');
      }
    });
    els.verlynQuickActions.addEventListener('change', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      if (target.id === 'verlyn-remedial-mode') {
        syncVerlynQuickActionFieldState();
      }
    });
    els.verlynQuickActions.addEventListener('input', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement)) {
        return;
      }
      if (target.id === 'verlyn-flag-registration' || target.id === 'verlyn-remedial-course-code') {
        target.value = normalizedRegistrationInput(target.value || '');
      }
      if (target.id === 'verlyn-remedial-section') {
        target.value = normalizeRemedialSections(target.value || '').join(', ');
      }
    });
  }
  if (els.verlynInput) {
    els.verlynInput.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter') {
        return;
      }
      event.preventDefault();
      void askVerlyn();
    });
  }
  if (els.verlynSidebarWidget) {
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && state.ui.verlynOpen) {
        setVerlynOpen(false);
      }
    });
  }
  window.addEventListener('resize', () => {
    updateVerlynVisibility();
    updateSupportDeskVisibility();
    updateChotuVisibility();
  });

  if (els.supportDeskToggleBtn) {
    els.supportDeskToggleBtn.addEventListener('click', async () => {
      if (!authState.user) {
        return;
      }
      const role = authState.user.role;
      if (role !== 'student' && role !== 'faculty') {
        return;
      }
      if (!state.ui.supportDeskOpen) {
        try {
          await refreshSupportDeskContext({ silent: true, refreshThread: true });
        } catch (error) {
          setSupportDeskStatus(error.message || 'Unable to load realtime messages right now.', true);
        }
      }
      toggleSupportDeskOpen();
    });
  }
  if (els.supportDeskMinimizeBtn) {
    els.supportDeskMinimizeBtn.addEventListener('click', () => {
      setSupportDeskOpen(false);
    });
  }
  if (els.supportDeskRecipientSelect) {
    els.supportDeskRecipientSelect.addEventListener('change', async () => {
      state.supportDesk.selectedCounterpartyId = Number(els.supportDeskRecipientSelect.value || 0) || null;
      state.supportDesk.messages = [];
      renderSupportDeskWidget();
      try {
        await refreshSupportDeskThread({ silent: true });
      } catch (error) {
        setSupportDeskStatus(error.message || 'Unable to open conversation.', true);
      }
    });
  }
  if (els.supportDeskCategorySelect) {
    els.supportDeskCategorySelect.addEventListener('change', async () => {
      state.supportDesk.selectedCategory = normalizeSupportDeskCategory(els.supportDeskCategorySelect.value);
      state.supportDesk.messages = [];
      renderSupportDeskWidget();
      try {
        await refreshSupportDeskThread({ silent: true });
      } catch (error) {
        setSupportDeskStatus(error.message || 'Unable to load category messages.', true);
      }
    });
  }
  if (els.supportDeskSendBtn) {
    els.supportDeskSendBtn.addEventListener('click', async () => {
      try {
        await sendSupportDeskMessage();
      } catch (error) {
        setSupportDeskStatus(error.message || 'Failed to send support message.', true);
      }
    });
  }
  if (els.supportDeskComposeInput) {
    els.supportDeskComposeInput.addEventListener('keydown', async (event) => {
      if (event.key !== 'Enter' || event.shiftKey) {
        return;
      }
      event.preventDefault();
      try {
        await sendSupportDeskMessage();
      } catch (error) {
        setSupportDeskStatus(error.message || 'Failed to send support message.', true);
      }
    });
  }
  if (els.supportDeskWidget) {
    document.addEventListener('click', (event) => {
      if (!state.ui.supportDeskOpen || !authState.user) {
        return;
      }
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      if (els.supportDeskWidget.contains(target)) {
        return;
      }
      setSupportDeskOpen(false);
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && state.ui.supportDeskOpen) {
        setSupportDeskOpen(false);
      }
    });
  }
  if (els.foodShopModal) {
    els.foodShopModal.addEventListener('click', (event) => {
      if (event.target === els.foodShopModal) {
        closeFoodShopModal();
      }
    });
  }

  if (els.foodCartModalCloseBtn) {
    els.foodCartModalCloseBtn.addEventListener('click', () => {
      closeFoodCartModal();
    });
  }

  if (els.foodCartModal) {
    els.foodCartModal.addEventListener('click', (event) => {
      if (event.target === els.foodCartModal) {
        closeFoodCartModal();
      }
    });
  }

  if (els.remedialCreateBtn) {
    els.remedialCreateBtn.addEventListener('click', async () => {
      try {
        await createRemedialClass();
      } catch (error) {
        setRemedialFacultyStatus(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.remedialModeSelect) {
    els.remedialModeSelect.addEventListener('change', () => {
      applyRemedialModeVisibility();
      syncVisibleVerlynQuickActions();
    });
  }

  if (els.remedialDemoInstantBtn) {
    els.remedialDemoInstantBtn.addEventListener('click', () => {
      state.remedial.demoBypassLeadTime = !state.remedial.demoBypassLeadTime;
      renderRemedialDemoToggle();
      if (state.remedial.demoBypassLeadTime) {
        setRemedialFacultyStatus('Demo instant scheduling enabled. 1-hour lead-time check is bypassed.');
        log('Demo instant scheduling enabled for remedial module');
      } else {
        setRemedialFacultyStatus('Demo instant scheduling disabled. 1-hour lead-time rule is active.');
        log('Demo instant scheduling disabled for remedial module');
      }
    });
  }

  if (els.remedialCourseCodeInput) {
    els.remedialCourseCodeInput.addEventListener('input', () => {
      els.remedialCourseCodeInput.value = normalizeRemedialCourseCode(els.remedialCourseCodeInput.value);
      syncVisibleVerlynQuickActions();
    });
  }

  if (els.remedialCourseSelect) {
    els.remedialCourseSelect.addEventListener('change', () => {
      syncRemedialManualCourseFromSelect();
      syncVisibleVerlynQuickActions();
    });
  }

  if (els.remedialSectionsInput) {
    els.remedialSectionsInput.addEventListener('input', () => {
      syncVisibleVerlynQuickActions();
    });
  }

  if (els.remedialDate) {
    els.remedialDate.addEventListener('change', () => {
      syncVisibleVerlynQuickActions();
    });
  }

  if (els.remedialStartTime) {
    els.remedialStartTime.addEventListener('change', () => {
      syncVisibleVerlynQuickActions();
    });
  }

  if (els.remedialRoomInput) {
    els.remedialRoomInput.addEventListener('input', () => {
      syncVisibleVerlynQuickActions();
    });
  }

  if (els.remedialClassSelect) {
    els.remedialClassSelect.addEventListener('change', async () => {
      try {
        state.remedial.selectedClassId = Number(els.remedialClassSelect.value || 0) || null;
        await refreshRemedialAttendanceForClass(state.remedial.selectedClassId);
      } catch (error) {
        setRemedialFacultyStatus(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.remedialClassesList) {
    els.remedialClassesList.addEventListener('click', async (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const sendBtn = target.closest('[data-remedial-send-code]');
      if (sendBtn instanceof HTMLElement) {
        const classId = Number(sendBtn.dataset.remedialSendCode || '0');
        if (!classId) {
          return;
        }
        const original = sendBtn.textContent || 'Send Code to Section(s)';
        sendBtn.disabled = true;
        sendBtn.textContent = 'Sending...';
        try {
          await sendRemedialCodeToSections(classId);
        } catch (error) {
          setRemedialFacultyStatus(error.message, true);
          log(error.message);
        } finally {
          sendBtn.disabled = false;
          sendBtn.textContent = original;
        }
        return;
      }
      const rejectBtn = target.closest('[data-remedial-cancel]');
      if (rejectBtn instanceof HTMLElement) {
        const classId = Number(rejectBtn.dataset.remedialCancel || '0');
        if (!classId) {
          return;
        }
        const original = rejectBtn.textContent || 'Reject Class';
        rejectBtn.disabled = true;
        rejectBtn.textContent = 'Rejecting...';
        try {
          await cancelRemedialClass(classId);
        } catch (error) {
          setRemedialFacultyStatus(error.message, true);
          log(error.message);
        } finally {
          rejectBtn.disabled = false;
          rejectBtn.textContent = original;
        }
      }
    });
  }

  if (els.remedialRefreshAttendanceBtn) {
    els.remedialRefreshAttendanceBtn.addEventListener('click', async () => {
      try {
        await refreshRemedialAttendanceForClass();
        setRemedialFacultyStatus('Remedial attendance refreshed.');
      } catch (error) {
        setRemedialFacultyStatus(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.remedialAttendanceList) {
    els.remedialAttendanceList.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const sectionCard = target.closest('[data-remedial-section]');
      if (!(sectionCard instanceof HTMLElement)) {
        return;
      }
      const sectionToken = String(sectionCard.dataset.remedialSection || '').trim().toUpperCase();
      if (!sectionToken) {
        return;
      }
      openRemedialAttendanceSectionModal(sectionToken);
    });

    els.remedialAttendanceList.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') {
        return;
      }
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const sectionCard = target.closest('[data-remedial-section]');
      if (!(sectionCard instanceof HTMLElement)) {
        return;
      }
      event.preventDefault();
      const sectionToken = String(sectionCard.dataset.remedialSection || '').trim().toUpperCase();
      if (!sectionToken) {
        return;
      }
      openRemedialAttendanceSectionModal(sectionToken);
    });
  }

  if (els.remedialRefreshMessagesBtn) {
    els.remedialRefreshMessagesBtn.addEventListener('click', async () => {
      try {
        await Promise.allSettled([
          refreshRemedialMessages(),
          refreshRemedialAttendanceLedger(),
        ]);
        setRemedialStudentStatus('Remedial feed refreshed.');
      } catch (error) {
        setRemedialStudentStatus(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.remedialValidateBtn) {
    els.remedialValidateBtn.addEventListener('click', async () => {
      try {
        await validateRemedialCode();
      } catch (error) {
        setRemedialStudentStatus(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.remedialMessagesList) {
    els.remedialMessagesList.addEventListener('click', async (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const button = target.closest('[data-remedial-use-code]');
      if (!(button instanceof HTMLElement)) {
        return;
      }
      const code = String(button.dataset.remedialUseCode || '').trim().toUpperCase();
      if (!code) {
        return;
      }
      const original = button.textContent || `Use Code ${code}`;
      button.disabled = true;
      button.textContent = 'Validating...';
      try {
        await applyRemedialCodeFromMessage(code);
      } catch (error) {
        setRemedialStudentStatus(error.message, true);
        log(error.message);
      } finally {
        button.disabled = false;
        button.textContent = original;
      }
    });
  }

  if (els.remedialStudentLedgerList) {
    els.remedialStudentLedgerList.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const card = target.closest('.course-clickable[data-remedial-course-key]');
      if (!(card instanceof HTMLElement)) {
        return;
      }
      const courseKey = String(card.dataset.remedialCourseKey || '');
      if (!courseKey) {
        return;
      }
      openRemedialStudentAttendanceModal(courseKey);
    });

    els.remedialStudentLedgerList.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') {
        return;
      }
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const card = target.closest('.course-clickable[data-remedial-course-key]');
      if (!(card instanceof HTMLElement)) {
        return;
      }
      event.preventDefault();
      const courseKey = String(card.dataset.remedialCourseKey || '');
      if (!courseKey) {
        return;
      }
      openRemedialStudentAttendanceModal(courseKey);
    });
  }

  if (els.facultyMessageSendBtn) {
    els.facultyMessageSendBtn.addEventListener('click', async () => {
      const button = els.facultyMessageSendBtn;
      const original = button.textContent || 'Send Message';
      button.disabled = true;
      button.textContent = 'Sending...';
      setFacultyMessageStatus('');
      try {
        await sendFacultyBroadcastMessage();
      } catch (error) {
        setFacultyMessageStatus(error.message, true);
        log(error.message);
      } finally {
        button.disabled = false;
        button.textContent = original;
      }
    });
  }

  if (els.directEmailSendBtn) {
    els.directEmailSendBtn.addEventListener('click', async () => {
      const button = els.directEmailSendBtn;
      const original = button.textContent || 'Send Email';
      button.disabled = true;
      button.textContent = 'Sending...';
      setDirectEmailStatus('Sending email. This can take up to a minute.');
      try {
        await sendDirectStudentEmail();
      } catch (error) {
        setDirectEmailStatus(error.message, true);
        log(error.message);
      } finally {
        button.disabled = false;
        button.textContent = original;
      }
    });
  }

  if (els.remedialCodeDetails) {
    els.remedialCodeDetails.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const button = target.closest('[data-remedial-open-online-link]');
      if (!(button instanceof HTMLElement)) {
        return;
      }
      const link = normalizedRemedialOnlineLink(button.dataset.remedialOpenOnlineLink || '');
      window.location.href = link;
    });
  }

  if (els.studentMessagesOpenRemedialBtn) {
    els.studentMessagesOpenRemedialBtn.addEventListener('click', async () => {
      if (!authState.user) {
        return;
      }
      setActiveModule('remedial', { updateHash: true });
      try {
        await refreshActiveModuleData();
      } catch (error) {
        log(error.message);
      }
    });
  }

  if (els.studentMessagesList) {
    els.studentMessagesList.addEventListener('click', async (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const openBtn = target.closest('[data-student-open-remedial]');
      if (openBtn instanceof HTMLElement) {
        setActiveModule('remedial', { updateHash: true });
        try {
          await refreshActiveModuleData();
        } catch (error) {
          log(error.message);
        }
        return;
      }
      const button = target.closest('[data-student-use-remedial-code]');
      if (!(button instanceof HTMLElement)) {
        return;
      }
      const code = String(button.dataset.studentUseRemedialCode || '').trim().toUpperCase();
      if (!code) {
        return;
      }
      const original = button.textContent || `Use Code ${code}`;
      button.disabled = true;
      button.textContent = 'Opening...';
      try {
        setActiveModule('remedial', { updateHash: true });
        await refreshActiveModuleData();
        await applyRemedialCodeFromMessage(code);
      } catch (error) {
        setRemedialStudentStatus(error.message, true);
        log(error.message);
      } finally {
        button.disabled = false;
        button.textContent = original;
      }
    });
  }

  if (els.remedialCodeInput) {
    els.remedialCodeInput.addEventListener('input', () => {
      els.remedialCodeInput.value = String(els.remedialCodeInput.value || '').toUpperCase().replace(/\s+/g, '');
      state.remedial.validatedClass = null;
      state.remedial.markedClassId = null;
      state.remedial.markedOnlineLink = '';
      renderRemedialCodeDetails();
    });
    els.remedialCodeInput.addEventListener('keydown', async (event) => {
      if (event.key !== 'Enter') {
        return;
      }
      event.preventDefault();
      try {
        await validateRemedialCode();
      } catch (error) {
        setRemedialStudentStatus(error.message, true);
        log(error.message);
      }
    });
  }

  if (els.remedialMarkBtn) {
    els.remedialMarkBtn.addEventListener('click', async () => {
      const originalText = els.remedialMarkBtn.textContent || 'Mark Attendance';
      els.remedialMarkBtn.disabled = true;
      els.remedialMarkBtn.textContent = 'Verifying...';
      try {
        await markRemedialAttendance();
      } catch (error) {
        setRemedialStudentStatus(error.message, true);
        log(error.message);
      } finally {
        els.remedialMarkBtn.disabled = false;
        els.remedialMarkBtn.textContent = originalText;
      }
    });
  }

  els.timetableGrid.addEventListener('click', (event) => {
    const card = event.target.closest('.calendar-class');
    if (card?.dataset.scheduleId) {
      selectStudentSchedule(Number(card.dataset.scheduleId));
    }
  });

  els.timetableGrid.addEventListener('keydown', async (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') {
      return;
    }

    const card = event.target.closest('.calendar-class');
    if (!card?.dataset.scheduleId) {
      return;
    }
    event.preventDefault();

    const scheduleId = Number(card.dataset.scheduleId);
    if (!scheduleId) {
      return;
    }
    selectStudentSchedule(scheduleId);

    if (event.shiftKey) {
      try {
        await handleStudentMarkAttendanceAction();
      } catch (error) {
        log(error.message);
        setStudentResult(error.message);
      }
    }
  });

  els.takeSelfieBtn.addEventListener('click', async () => {
    try {
      await handleStudentMarkAttendanceAction();
    } catch (error) {
      log(error.message);
      setStudentResult(error.message);
    }
  });

  if (els.studentAttendanceDemoBtn) {
    els.studentAttendanceDemoBtn.addEventListener('click', () => {
      state.student.demoAttendanceEnabled = !state.student.demoAttendanceEnabled;
      updateSelectedClassState();
      if (state.student.demoAttendanceEnabled) {
        setStudentResult('Demo attendance enabled. You can run full live verification anytime. Nothing will be saved.');
        log('Student attendance demo mode enabled');
      } else {
        setStudentResult('Demo attendance disabled. Official first-10-minute attendance window is active again.');
        log('Student attendance demo mode disabled');
      }
    });
  }

  if (els.saarthiSendBtn) {
    els.saarthiSendBtn.addEventListener('click', async () => {
      try {
        await sendSaarthiMessage();
      } catch (error) {
        setSaarthiStatus(error.message || 'Failed to send message to Saarthi.', 'error');
      }
    });
  }

  if (els.saarthiNewChatBtn) {
    els.saarthiNewChatBtn.addEventListener('click', async () => {
      try {
        await startNewSaarthiChat();
      } catch (error) {
        setSaarthiStatus(error.message || 'Failed to start a new Saarthi chat.', 'error');
      }
    });
  }

  if (els.saarthiComposeInput) {
    els.saarthiComposeInput.addEventListener('keydown', async (event) => {
      if (event.key !== 'Enter' || event.shiftKey) {
        return;
      }
      event.preventDefault();
      try {
        await sendSaarthiMessage();
      } catch (error) {
        setSaarthiStatus(error.message || 'Failed to send message to Saarthi.', 'error');
      }
    });
  }

  if (els.studentAggregateCourses) {
    els.studentAggregateCourses.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const card = target.closest('.course-clickable[data-course-key]');
      if (!(card instanceof HTMLElement)) {
        return;
      }
      const courseKey = String(card.dataset.courseKey || '');
      if (!courseKey) {
        return;
      }
      renderAttendanceDetailsModal(courseKey);
    });

    els.studentAggregateCourses.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') {
        return;
      }
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const card = target.closest('.course-clickable[data-course-key]');
      if (!(card instanceof HTMLElement)) {
        return;
      }
      event.preventDefault();
      const courseKey = String(card.dataset.courseKey || '');
      if (!courseKey) {
        return;
      }
      renderAttendanceDetailsModal(courseKey);
    });
  }

  if (els.studentRecoveryPlans) {
    els.studentRecoveryPlans.addEventListener('click', async (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const button = target.closest('[data-recovery-action-command]');
      if (!(button instanceof HTMLButtonElement)) {
        return;
      }
      const actionId = Number(button.dataset.recoveryActionId || '0');
      const command = String(button.dataset.recoveryActionCommand || '').trim().toLowerCase();
      if (!actionId || !command) {
        return;
      }
      const original = button.textContent || 'Update';
      button.disabled = true;
      button.textContent = command === 'complete' ? 'Saving...' : 'Updating...';
      try {
        await submitStudentRecoveryAction(actionId, command);
      } catch (error) {
        log(error.message || 'Recovery action update failed.');
      } finally {
        button.disabled = false;
        button.textContent = original;
      }
    });
  }

  if (els.attendanceDetailsCloseBtn) {
    els.attendanceDetailsCloseBtn.addEventListener('click', () => {
      closeAttendanceDetailsModal();
    });
  }

  if (els.attendanceDetailsModal) {
    els.attendanceDetailsModal.addEventListener('click', (event) => {
      if (event.target === els.attendanceDetailsModal) {
        closeAttendanceDetailsModal();
      }
    });
  }

  if (els.attendanceDetailsList) {
    els.attendanceDetailsList.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const button = target.closest('[data-open-rectification]');
      if (!(button instanceof HTMLElement)) {
        return;
      }
      openAttendanceRectificationModal({
        courseId: Number(button.dataset.rectificationCourseId || 0),
        scheduleId: Number(button.dataset.rectificationScheduleId || 0),
        classDate: String(button.dataset.rectificationClassDate || ''),
        startTime: String(button.dataset.rectificationStartTime || ''),
        endTime: String(button.dataset.rectificationEndTime || ''),
        courseCode: String(button.dataset.rectificationCourseCode || ''),
        courseTitle: String(button.dataset.rectificationCourseTitle || ''),
      });
    });
  }

  if (els.attendanceRectificationProofPhotoInput) {
    els.attendanceRectificationProofPhotoInput.addEventListener('change', async () => {
      const file = els.attendanceRectificationProofPhotoInput.files?.[0];
      if (!file) {
        setAttendanceRectificationProofPreview('');
        return;
      }
      try {
        const dataUrl = await fileToDataUrl(file);
        if (!String(dataUrl || '').startsWith('data:image/')) {
          throw new Error('Select a valid image file for proof.');
        }
        setAttendanceRectificationProofPreview(dataUrl);
      } catch (error) {
        setAttendanceRectificationProofPreview('');
        log(error.message);
      }
    });
  }

  if (els.attendanceRectificationCancelBtn) {
    els.attendanceRectificationCancelBtn.addEventListener('click', () => {
      closeAttendanceRectificationModal();
    });
  }

  if (els.attendanceRectificationSubmitBtn) {
    els.attendanceRectificationSubmitBtn.addEventListener('click', async () => {
      els.attendanceRectificationSubmitBtn.disabled = true;
      try {
        await submitStudentRectificationRequest();
      } catch (error) {
        if (els.attendanceRectificationStatus) {
          els.attendanceRectificationStatus.textContent = error.message;
        }
        log(error.message);
      } finally {
        els.attendanceRectificationSubmitBtn.disabled = false;
      }
    });
  }

  if (els.attendanceRectificationModal) {
    els.attendanceRectificationModal.addEventListener('click', (event) => {
      if (event.target === els.attendanceRectificationModal) {
        closeAttendanceRectificationModal();
      }
    });
  }

  if (els.remedialAttendanceModalCloseBtn) {
    els.remedialAttendanceModalCloseBtn.addEventListener('click', () => {
      closeRemedialAttendanceModal();
    });
  }

  if (els.remedialAttendanceModal) {
    els.remedialAttendanceModal.addEventListener('click', (event) => {
      if (event.target === els.remedialAttendanceModal) {
        closeRemedialAttendanceModal();
      }
    });
  }

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') {
      return;
    }
    if (els.mfaHelpModal && !els.mfaHelpModal.classList.contains('hidden')) {
      setMfaHelpModal(false);
      return;
    }
    if (isForgotPasswordPanelOpen()) {
      setForgotPasswordPanel(false);
      return;
    }
    if (els.remedialAttendanceModal && !els.remedialAttendanceModal.classList.contains('hidden')) {
      closeRemedialAttendanceModal();
      return;
    }
    if (els.attendanceRectificationModal && !els.attendanceRectificationModal.classList.contains('hidden')) {
      closeAttendanceRectificationModal();
      return;
    }
    if (els.attendanceDetailsModal && !els.attendanceDetailsModal.classList.contains('hidden')) {
      closeAttendanceDetailsModal();
    }
  });
  els.profilePhotoInput.addEventListener('change', async () => {
    const role = authState.user?.role;
    if (role !== 'student' && role !== 'faculty') {
      els.profilePhotoInput.value = '';
      return;
    }
    const file = els.profilePhotoInput.files?.[0];
    if (!file) {
      if (role === 'faculty') {
        state.facultyProfile.pendingProfilePhotoDataUrl = '';
      } else {
        state.student.pendingProfilePhotoDataUrl = '';
      }
      renderProfileStatusByRole();
      if (role === 'student') {
        renderEnrollmentSummary();
      }
      return;
    }

    const hasExistingPhoto = role === 'faculty'
      ? Boolean(state.facultyProfile.profilePhotoDataUrl)
      : Boolean(state.student.profilePhotoDataUrl);
    const canUpdateNow = role === 'faculty'
      ? state.facultyProfile.profilePhotoCanUpdateNow
      : state.student.profilePhotoCanUpdateNow;
    if (hasExistingPhoto && !canUpdateNow) {
      if (role === 'faculty') {
        state.facultyProfile.pendingProfilePhotoDataUrl = '';
      } else {
        state.student.pendingProfilePhotoDataUrl = '';
      }
      els.profilePhotoInput.value = '';
      showActiveProfilePhotoLockPopup();
      renderProfileStatusByRole();
      if (role === 'student') {
        renderEnrollmentSummary();
      }
      return;
    }

    try {
      const dataUrl = await fileToDataUrl(file);
      if (role === 'faculty') {
        state.facultyProfile.pendingProfilePhotoDataUrl = dataUrl;
        renderFacultyProfilePreview(dataUrl);
      } else {
        state.student.pendingProfilePhotoDataUrl = dataUrl;
        renderStudentProfilePreview(dataUrl);
        renderEnrollmentSummary();
      }
      renderProfileStatusByRole();
      if (els.profileStatus) {
        els.profileStatus.textContent = 'Photo selected. Click Save Profile to complete setup.';
      }
    } catch (error) {
      log(error.message);
    }
  });

  els.saveProfilePhotoBtn.addEventListener('click', async () => {
    try {
      if (authState.user?.role === 'faculty') {
        await saveFacultyProfile();
      } else if (authState.user?.role === 'student') {
        await saveStudentProfilePhoto();
      } else {
        return;
      }
    } catch (error) {
      const message = String(error?.message || 'Failed to save profile.');
      log(message);
      if (els.profileStatus) {
        if (/profile photo locked until/i.test(message)) {
          els.profileStatus.textContent = 'Profile photo update is currently locked. Please try after unlock time.';
        } else {
          els.profileStatus.textContent = message;
        }
      }
      updateProfileSaveState();
    }
  });

  if (els.profileCloseBtn) {
    els.profileCloseBtn.addEventListener('click', () => {
      closeProfileModal();
    });
  }

  if (els.profileTabDetailsBtn) {
    els.profileTabDetailsBtn.addEventListener('click', () => {
      setProfileTab('details');
    });
  }

  if (els.profileTabEnrollmentBtn) {
    els.profileTabEnrollmentBtn.addEventListener('click', () => {
      setProfileTab('enrollment');
      renderEnrollmentSummary();
    });
  }

  if (els.openProfilePhotoUpdateBtn) {
    els.openProfilePhotoUpdateBtn.addEventListener('click', () => {
      openEnrollmentPhotoUpdateFlow();
    });
  }

  if (els.openEnrollmentModalBtn) {
    els.openEnrollmentModalBtn.addEventListener('click', () => {
      if (authState.user?.role !== 'student') {
        return;
      }
      if (state.student.hasEnrollmentVideo && !state.student.enrollmentCanUpdateNow) {
        showEnrollmentLockPopup();
        return;
      }
      openEnrollmentModal({ required: requiresStudentEnrollmentSetup() });
    });
  }

  if (els.enrollmentStartBtn) {
    els.enrollmentStartBtn.addEventListener('click', async () => {
      try {
        await startEnrollmentGuidedCapture();
      } catch (error) {
        const message = error?.message || 'Failed to start enrollment capture';
        if (els.enrollmentStatus) {
          els.enrollmentStatus.textContent = message;
        }
        log(message);
      }
    });
  }

  if (els.enrollmentSaveBtn) {
    els.enrollmentSaveBtn.addEventListener('click', async () => {
      try {
        await saveStudentEnrollmentVideo();
      } catch (error) {
        const message = error?.message || 'Failed to save enrollment video';
        if (els.enrollmentStatus) {
          els.enrollmentStatus.textContent = message;
        }
        log(message);
      }
    });
  }

  if (els.enrollmentCloseBtn) {
    els.enrollmentCloseBtn.addEventListener('click', () => {
      closeEnrollmentModal();
    });
  }

  if (els.enrollmentLogoutBtn) {
    els.enrollmentLogoutBtn.addEventListener('click', () => {
      logout();
    });
  }

  if (els.profileRegistrationNumber) {
    els.profileRegistrationNumber.addEventListener('input', () => {
      const raw = els.profileRegistrationNumber.value || '';
      els.profileRegistrationNumber.value = raw.toUpperCase().replace(/\s+/g, '');
      renderProfileStatusByRole();
    });
  }

  if (els.profileFullName) {
    els.profileFullName.addEventListener('input', () => {
      els.profileFullName.value = normalizeProfileName(els.profileFullName.value || '');
      renderProfileStatusByRole();
    });
  }

  if (els.profileSectionInput) {
    els.profileSectionInput.addEventListener('input', () => {
      const raw = els.profileSectionInput.value || '';
      els.profileSectionInput.value = raw.toUpperCase().replace(/\s+/g, '');
      renderProfileStatusByRole();
    });
  }

  els.facultyScheduleSelect.addEventListener('change', async () => {
    try {
      state.faculty.selectedSubmissionIds.clear();
      await refreshFacultyDashboard();
    } catch (error) {
      log(error.message);
    }
  });

  els.facultyClassDate.addEventListener('change', async () => {
    try {
      state.faculty.selectedSubmissionIds.clear();
      await refreshFacultyDashboard();
    } catch (error) {
      log(error.message);
    }
  });

  els.facultyRefreshBtn.addEventListener('click', async () => {
    try {
      await refreshFacultyDashboard();
      log('Faculty dashboard refreshed');
    } catch (error) {
      log(error.message);
    }
  });

  if (els.adminCreateScheduleBtn) {
    els.adminCreateScheduleBtn.addEventListener('click', async () => {
      try {
        await createAdminAttendanceSchedule();
      } catch (error) {
        const message = String(error?.message || 'Failed to create schedule.');
        setAdminCreateScheduleStatus(message, true);
        log(message);
      }
    });
  }

  if (els.adminTimetableOverrideSection) {
    els.adminTimetableOverrideSection.addEventListener('input', () => {
      const raw = String(els.adminTimetableOverrideSection.value || '');
      els.adminTimetableOverrideSection.value = raw.toUpperCase().replace(/\s+/g, '');
    });
  }

  if (els.adminTimetableOverrideBtn) {
    els.adminTimetableOverrideBtn.addEventListener('click', async () => {
      try {
        await saveAdminTimetableOverride();
      } catch (error) {
        const message = String(error?.message || 'Failed to save timetable override.');
        setAdminTimetableOverrideStatus(message, true);
        log(message);
      }
    });
  }

  if (els.adminUpdateStudentSection) {
    els.adminUpdateStudentSection.addEventListener('input', () => {
      const raw = String(els.adminUpdateStudentSection.value || '');
      els.adminUpdateStudentSection.value = raw.toUpperCase().replace(/\s+/g, '');
    });
  }

  if (els.adminUpdateStudentSectionBtn) {
    els.adminUpdateStudentSectionBtn.addEventListener('click', async () => {
      try {
        await approveAdminStudentSectionUpdate();
      } catch (error) {
        const message = String(error?.message || 'Failed to update student section.');
        setAdminSectionUpdateStatus(message, true);
        log(message);
      }
    });
  }

  if (els.adminSearchStudentRegistration) {
    els.adminSearchStudentRegistration.addEventListener('input', () => {
      els.adminSearchStudentRegistration.value = normalizedRegistrationInput(els.adminSearchStudentRegistration.value || '');
      syncVisibleVerlynQuickActions();
    });
  }

  if (els.adminSearchFacultyIdentifier) {
    els.adminSearchFacultyIdentifier.addEventListener('input', () => {
      els.adminSearchFacultyIdentifier.value = normalizedRegistrationInput(els.adminSearchFacultyIdentifier.value || '');
    });
  }

  if (els.adminGradeStudentRegistration) {
    els.adminGradeStudentRegistration.addEventListener('input', () => {
      els.adminGradeStudentRegistration.value = normalizedRegistrationInput(els.adminGradeStudentRegistration.value || '');
    });
  }

  if (els.adminGradeCourseCode) {
    els.adminGradeCourseCode.addEventListener('input', () => {
      els.adminGradeCourseCode.value = normalizedRegistrationInput(els.adminGradeCourseCode.value || '');
    });
  }

  if (els.adminRecoveryIncludeResolved) {
    els.adminRecoveryIncludeResolved.addEventListener('change', async () => {
      try {
        state.admin.recoveryIncludeResolved = Boolean(els.adminRecoveryIncludeResolved.checked);
        await refreshAdminRecoveryPlans({
          includeResolved: state.admin.recoveryIncludeResolved,
        });
      } catch (error) {
        const message = String(error?.message || 'Failed to refresh recovery desk.');
        setAdminRecoveryStatus(message, true);
        log(message);
      }
    });
  }

  if (els.adminRecoveryRefreshBtn) {
    els.adminRecoveryRefreshBtn.addEventListener('click', async () => {
      try {
        await refreshAdminRecoveryPlans({
          includeResolved: state.admin?.recoveryIncludeResolved,
        });
      } catch (error) {
        const message = String(error?.message || 'Failed to refresh recovery desk.');
        setAdminRecoveryStatus(message, true);
        log(message);
      }
    });
  }

  if (els.adminRecoveryRecomputeAllBtn) {
    els.adminRecoveryRecomputeAllBtn.addEventListener('click', async () => {
      try {
        await recomputeAdminRecoveryScope();
      } catch (error) {
        const message = String(error?.message || 'Failed to recompute attendance recovery scope.');
        setAdminRecoveryStatus(message, true);
        log(message);
      }
    });
  }

  if (els.adminRecoveryList) {
    els.adminRecoveryList.addEventListener('click', async (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const button = target.closest('[data-admin-recovery-command]');
      if (!button) {
        return;
      }
      event.preventDefault();
      const command = String(button.dataset.adminRecoveryCommand || '').trim().toLowerCase();
      try {
        if (command === 'recompute-plan') {
          await recomputeAdminRecoveryScope({
            studentId: Number(button.dataset.adminRecoveryStudentId || 0),
            courseId: Number(button.dataset.adminRecoveryCourseId || 0),
            limit: 1,
          });
          return;
        }
        if (command === 'open-rms') {
          await openRecoveryPlanInRms(Number(button.dataset.adminRecoveryPlanId || 0));
        }
      } catch (error) {
        const message = String(error?.message || 'Recovery action failed.');
        setAdminRecoveryStatus(message, true);
        log(message);
      }
    });
  }

  if (els.adminSearchStudentBtn) {
    els.adminSearchStudentBtn.addEventListener('click', async () => {
      try {
        await adminSearchStudentByRegistration();
      } catch (error) {
        const message = String(error?.message || 'Failed to search student.');
        setAdminSearchStatus(message, true);
        log(message);
      }
    });
  }

  if (els.adminSearchFacultyBtn) {
    els.adminSearchFacultyBtn.addEventListener('click', async () => {
      try {
        await adminSearchFacultyByIdentifier();
      } catch (error) {
        const message = String(error?.message || 'Failed to search faculty.');
        setAdminSearchStatus(message, true);
        log(message);
      }
    });
  }

  if (els.adminGlobalSearchBtn) {
    els.adminGlobalSearchBtn.addEventListener('click', async () => {
      try {
        await adminSearchEverything();
      } catch (error) {
        const message = String(error?.message || 'Failed to run global search.');
        setAdminSearchStatus(message, true);
        log(message);
      }
    });
  }

  if (els.adminGradeSubmitBtn) {
    els.adminGradeSubmitBtn.addEventListener('click', async () => {
      try {
        await adminUpsertStudentGrade();
      } catch (error) {
        const message = String(error?.message || 'Failed to save student grade.');
        setAdminGradeStatus(message, true);
        log(message);
      }
    });
  }

  if (els.adminIdentityStudentId) {
    els.adminIdentityStudentId.addEventListener('keydown', async (event) => {
      if (event.key !== 'Enter') {
        return;
      }
      event.preventDefault();
      try {
        await refreshAdminIdentityCases();
      } catch (error) {
        const message = String(error?.message || 'Failed to load identity cases.');
        setAdminIdentityShieldStatus(message, true);
        log(message);
      }
    });
  }

  if (els.adminIdentityScreenBtn) {
    els.adminIdentityScreenBtn.addEventListener('click', async () => {
      try {
        await runAdminEnrollmentIdentityScreening();
      } catch (error) {
        const message = String(error?.message || 'Failed to run identity screening.');
        setAdminIdentityShieldStatus(message, true);
        log(message);
      }
    });
  }

  if (els.adminIdentityRefreshBtn) {
    els.adminIdentityRefreshBtn.addEventListener('click', async () => {
      try {
        await refreshAdminIdentityCases();
      } catch (error) {
        const message = String(error?.message || 'Failed to load identity cases.');
        setAdminIdentityShieldStatus(message, true);
        log(message);
      }
    });
  }

  if (els.adminCopilotAuditSearch) {
    els.adminCopilotAuditSearch.addEventListener('keydown', async (event) => {
      if (event.key !== 'Enter') {
        return;
      }
      event.preventDefault();
      try {
        await refreshCopilotAuditTimeline({ force: true });
      } catch (error) {
        setAdminCopilotAuditStatus(error?.message || 'Failed to load copilot timeline.', true, 'error');
      }
    });
  }

  if (els.adminCopilotAuditActorUserId) {
    els.adminCopilotAuditActorUserId.addEventListener('keydown', async (event) => {
      if (event.key !== 'Enter') {
        return;
      }
      event.preventDefault();
      try {
        await refreshCopilotAuditTimeline({ force: true });
      } catch (error) {
        setAdminCopilotAuditStatus(error?.message || 'Failed to load copilot timeline.', true, 'error');
      }
    });
  }

  if (els.adminCopilotAuditSearchBtn) {
    els.adminCopilotAuditSearchBtn.addEventListener('click', async () => {
      try {
        await refreshCopilotAuditTimeline({ force: true });
      } catch (error) {
        setAdminCopilotAuditStatus(error?.message || 'Failed to load copilot timeline.', true, 'error');
      }
    });
  }

  if (els.adminCopilotAuditClearBtn) {
    els.adminCopilotAuditClearBtn.addEventListener('click', async () => {
      resetCopilotAuditFilters();
      try {
        await refreshCopilotAuditTimeline({ force: true });
      } catch (error) {
        setAdminCopilotAuditStatus(error?.message || 'Failed to load copilot timeline.', true, 'error');
      }
    });
  }

  if (els.rmsSearchRegistration) {
    els.rmsSearchRegistration.addEventListener('input', () => {
      els.rmsSearchRegistration.value = normalizedRegistrationInput(els.rmsSearchRegistration.value || '');
      syncVisibleVerlynQuickActions();
    });
  }

  if (els.rmsUpdateRegistration) {
    els.rmsUpdateRegistration.addEventListener('input', () => {
      els.rmsUpdateRegistration.value = normalizedRegistrationInput(els.rmsUpdateRegistration.value || '');
    });
  }

  if (els.rmsUpdateSection) {
    els.rmsUpdateSection.addEventListener('input', () => {
      const raw = String(els.rmsUpdateSection.value || '');
      els.rmsUpdateSection.value = raw.toUpperCase().replace(/\s+/g, '');
    });
  }

  if (els.rmsAttendanceRegistration) {
    els.rmsAttendanceRegistration.addEventListener('input', () => {
      els.rmsAttendanceRegistration.value = normalizedRegistrationInput(els.rmsAttendanceRegistration.value || '');
      state.rms.attendanceContext = null;
      state.rms.attendanceSelectedCourseCode = '';
      state.rms.attendanceSelectedScheduleId = null;
      renderRmsAttendanceStudentSummary(null);
      renderRmsAttendanceSubjectOptions(null);
      syncVisibleVerlynQuickActions();
    });
  }

  if (els.rmsAttendanceSearchBtn) {
    els.rmsAttendanceSearchBtn.addEventListener('click', async () => {
      try {
        await searchRmsAttendanceStudentContext();
      } catch (error) {
        const message = String(error?.message || 'Failed to load RMS attendance subjects.');
        setRmsAttendanceStatus(message, true);
        log(message);
      }
    });
  }

  if (els.rmsAttendanceSubjectSelect) {
    els.rmsAttendanceSubjectSelect.addEventListener('change', () => {
      state.rms.attendanceSelectedCourseCode = String(els.rmsAttendanceSubjectSelect.value || '')
        .trim()
        .toUpperCase();
      state.rms.attendanceSelectedScheduleId = null;
      renderRmsAttendanceSlotOptions();
      syncRmsAttendanceCurrentStatus();
    });
  }

  if (els.rmsAttendanceSlotSelect) {
    els.rmsAttendanceSlotSelect.addEventListener('change', () => {
      const selectedScheduleId = Number(String(els.rmsAttendanceSlotSelect.value || '').trim() || 0) || null;
      state.rms.attendanceSelectedScheduleId = selectedScheduleId;
      syncRmsAttendanceCurrentStatus();
    });
  }

  if (els.rmsAttendanceDate) {
    els.rmsAttendanceDate.addEventListener('change', async () => {
      if (!normalizedRegistrationInput(els.rmsAttendanceRegistration?.value || '')) {
        return;
      }
      try {
        await searchRmsAttendanceStudentContext({ silent: true });
      } catch (error) {
        const message = String(error?.message || 'Failed to refresh attendance status for selected date.');
        setRmsAttendanceStatus(message, true);
        log(message);
      }
    });
  }

  if (els.rmsRefreshBtn) {
    els.rmsRefreshBtn.addEventListener('click', async () => {
      try {
        await refreshRmsModule();
      } catch (error) {
        const message = String(error?.message || 'Failed to refresh RMS.');
        setRmsStatus(message, true);
        log(message);
      }
    });
  }

  if (els.rmsQueryCategory) {
    els.rmsQueryCategory.addEventListener('change', async () => {
      try {
        await refreshRmsModule();
      } catch (error) {
        const message = String(error?.message || 'Failed to apply RMS category filter.');
        setRmsStatus(message, true);
        log(message);
      }
    });
  }

  if (els.rmsQueryStatus) {
    els.rmsQueryStatus.addEventListener('change', async () => {
      try {
        await refreshRmsModule();
      } catch (error) {
        const message = String(error?.message || 'Failed to apply RMS status filter.');
        setRmsStatus(message, true);
        log(message);
      }
    });
  }

  if (els.rmsThreadAction) {
    els.rmsThreadAction.addEventListener('change', () => {
      syncRmsThreadActionForm();
    });
  }

  if (els.rmsApplyThreadActionBtn) {
    els.rmsApplyThreadActionBtn.addEventListener('click', async () => {
      try {
        await applyRmsQueryWorkflowAction();
      } catch (error) {
        const message = String(error?.message || 'Failed to apply RMS workflow action.');
        setRmsThreadActionStatus(message, true);
        log(message);
      }
    });
  }

  if (els.rmsStudentSearchBtn) {
    els.rmsStudentSearchBtn.addEventListener('click', async () => {
      try {
        await searchRmsStudentByRegistration();
      } catch (error) {
        const message = String(error?.message || 'Failed to search student.');
        setRmsStatus(message, true);
        log(message);
      }
    });
  }

  if (els.rmsApplyUpdateBtn) {
    els.rmsApplyUpdateBtn.addEventListener('click', async () => {
      try {
        await applyRmsStudentApprovalUpdate();
      } catch (error) {
        const message = String(error?.message || 'Failed to apply RMS student update.');
        setRmsStudentUpdateStatus(message, true);
        log(message);
      }
    });
  }

  if (els.rmsAttendanceApplyBtn) {
    els.rmsAttendanceApplyBtn.addEventListener('click', async () => {
      try {
        await applyRmsAttendanceStatusUpdate();
      } catch (error) {
        const message = String(error?.message || 'Failed to apply RMS attendance update.');
        setRmsAttendanceStatus(message, true);
        log(message);
      }
    });
  }

  if (els.rmsQueryList) {
    els.rmsQueryList.addEventListener('click', async (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const threadButton = target.closest('[data-rms-select-thread]');
      if (threadButton instanceof HTMLElement) {
        const studentId = Number(threadButton.dataset.rmsThreadStudentId || 0);
        const facultyId = Number(threadButton.dataset.rmsThreadFacultyId || 0);
        const category = String(threadButton.dataset.rmsThreadCategory || '').trim();
        const selectedThread = findRmsThreadInDashboard({
          student_id: studentId,
          faculty_id: facultyId,
          category,
        });
        if (!selectedThread) {
          setRmsThreadActionStatus('Thread not available in current filter result.', true);
          return;
        }
        state.rms.selectedThread = selectedThread;
        if (els.rmsThreadAction) {
          const inferredAction = String(selectedThread.action_state || '').trim().toLowerCase();
          if (inferredAction === 'scheduled') {
            state.rms.threadAction = 'schedule';
            els.rmsThreadAction.value = 'schedule';
          }
        }
        if (els.rmsThreadScheduledFor) {
          if (selectedThread.scheduled_for) {
            const asDate = new Date(selectedThread.scheduled_for);
            if (!Number.isNaN(asDate.getTime())) {
              const localValue = new Date(asDate.getTime() - (asDate.getTimezoneOffset() * 60000))
                .toISOString()
                .slice(0, 16);
              els.rmsThreadScheduledFor.value = localValue;
            }
          } else {
            els.rmsThreadScheduledFor.value = '';
          }
        }
        if (els.rmsThreadNote) {
          els.rmsThreadNote.value = String(selectedThread.action_note || '');
        }
        syncRmsThreadActionForm();
        renderRmsSelectedThreadSummary();
        setRmsThreadActionStatus('Thread selected. Choose workflow action and apply.', false);
      }
      const regButton = target.closest('[data-rms-use-reg]');
      if (!(regButton instanceof HTMLElement)) {
        return;
      }
      const registration = normalizedRegistrationInput(regButton.dataset.rmsUseReg || '');
      if (!registration || !els.rmsSearchRegistration) {
        return;
      }
      els.rmsSearchRegistration.value = registration;
      syncVisibleVerlynQuickActions();
      try {
        await searchRmsStudentByRegistration({ silent: true });
        setRmsStatus(`Loaded student with registration ${registration}.`, false);
      } catch (error) {
        const message = String(error?.message || 'Failed to load student for this RMS thread.');
        setRmsStatus(message, true);
        log(message);
      }
    });
  }

  els.facultySubmissionsBody.addEventListener('change', (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement) || !target.classList.contains('submission-check')) {
      return;
    }

    const submissionId = Number(target.dataset.submissionId);
    if (!submissionId) {
      return;
    }

    if (target.checked) {
      state.faculty.selectedSubmissionIds.add(submissionId);
    } else {
      state.faculty.selectedSubmissionIds.delete(submissionId);
    }

    syncReviewSelectionUI();
  });

  els.reviewSelectAll.addEventListener('change', () => {
    const shouldCheck = els.reviewSelectAll.checked;
    const boxes = [...els.facultySubmissionsBody.querySelectorAll('input.submission-check')];

    state.faculty.selectedSubmissionIds.clear();
    for (const box of boxes) {
      box.checked = shouldCheck;
      const id = Number(box.dataset.submissionId);
      if (shouldCheck && id) {
        state.faculty.selectedSubmissionIds.add(id);
      }
    }

    syncReviewSelectionUI();
  });

  els.facultyApproveBtn.addEventListener('click', async () => {
    try {
      await submitFacultyBatchReview('approve');
    } catch (error) {
      log(error.message);
    }
  });

  els.facultyRejectBtn.addEventListener('click', async () => {
    try {
      await submitFacultyBatchReview('reject');
    } catch (error) {
      log(error.message);
    }
  });

  if (els.facultyRectificationBody) {
    els.facultyRectificationBody.addEventListener('click', async (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const actionBtn = target.closest('[data-rectification-action]');
      if (!(actionBtn instanceof HTMLElement)) {
        return;
      }
      const requestId = Number(actionBtn.dataset.rectificationId || 0);
      const action = String(actionBtn.dataset.rectificationAction || '').trim().toLowerCase();
      if (!requestId || (action !== 'approve' && action !== 'reject')) {
        return;
      }
      actionBtn.setAttribute('disabled', 'disabled');
      try {
        await submitFacultyRectificationReview(requestId, action);
      } catch (error) {
        log(error.message);
      } finally {
        actionBtn.removeAttribute('disabled');
      }
    });
  }

  els.classroomPhotoInput.addEventListener('change', async () => {
    const file = els.classroomPhotoInput.files?.[0];
    if (!file) {
      return;
    }

    try {
      state.faculty.classroomPhotoDataUrl = await fileToDataUrl(file);
      renderClassroomPhotoPreview(state.faculty.classroomPhotoDataUrl);
      els.classroomAnalysisOutput.textContent = 'Classroom photo loaded. Click Analyze & Save.';
    } catch (error) {
      log(error.message);
    }
  });

  els.captureClassroomBtn.addEventListener('click', async () => {
    try {
      await startClassroomCaptureFlow();
    } catch (error) {
      log(error.message);
    }
  });

  els.analyzeClassroomBtn.addEventListener('click', async () => {
    try {
      await analyzeAndSaveClassroom();
    } catch (error) {
      log(error.message);
      els.classroomAnalysisOutput.textContent = error.message;
    }
  });

  els.cameraCaptureBtn.addEventListener('click', async () => {
    try {
      await captureFromCamera();
    } catch (error) {
      log(error.message);
      els.cameraMessage.textContent = error.message;
    }
  });

  els.cameraCloseBtn.addEventListener('click', () => {
    closeCameraModal();
  });
}

async function init() {
  els.workDate.value = todayISO();
  els.facultyClassDate.value = todayISO();
  els.weekStartDate.value = todayISO();
  if (els.rmsQueryCategory) {
    els.rmsQueryCategory.value = state.rms.selectedCategory;
  }
  if (els.rmsQueryStatus) {
    els.rmsQueryStatus.value = state.rms.selectedStatus;
  }
  if (els.rmsThreadAction) {
    els.rmsThreadAction.value = state.rms.threadAction;
  }
  if (els.rmsAttendanceDate) {
    els.rmsAttendanceDate.value = todayISO();
  }
  if (els.rmsAttendanceStatus) {
    els.rmsAttendanceStatus.value = 'present';
  }
  if (els.rmsAttendanceCurrentStatus) {
    els.rmsAttendanceCurrentStatus.value = 'Not marked';
  }
  if (els.rmsAttendanceSlotSelect) {
    els.rmsAttendanceSlotSelect.innerHTML = '<option value="">Select time slot</option>';
    els.rmsAttendanceSlotSelect.value = '';
  }
  syncRmsThreadActionForm();
  renderRmsSelectedThreadSummary(null);
  renderRmsStudentSummary(null);
  renderRmsAttendanceStudentSummary(null);
  renderRmsAttendanceSubjectOptions(null);
  renderRmsAttendanceResult(null);
  renderRmsDashboard();
  if (els.foodOrderDate) {
    els.foodOrderDate.value = todayISO();
  }
  if (els.remedialDate) {
    els.remedialDate.value = todayISO();
  }
  state.student.viewDate = els.weekStartDate.value;
  state.food.orderDate = els.foodOrderDate?.value || todayISO();
  state.ui.activeModule = normalizeModuleKey(moduleFromHash() || state.ui.activeModule);
  applyTheme(getInitialTheme(''), { persist: false, userEmail: '' });
  restoreFoodDemoEnabled();
  bindStaticAssetFallbacks();
  startLiveDateTimeTicker();
  setAuthMode('login');
  if (ENABLE_DECORATIVE_MOTION) {
    initParallax();
    initTiltCards();
  }
  initMicroInteractions();
  initSaarthiAvatarAura();
  bindSessionActivityWatchdog();
  bindEvents();
  initModalFocusTrapObserver();
  renderFoodDemoToggle();
  syncFoodOrderActionState();
  renderWorkloadChart();
  renderMongoStatus();
  renderPasswordStrengthHint(els.authPasswordStrength, els.authPassword?.value || '');
  renderPasswordStrengthHint(els.authSignupPasswordStrength, els.authSignupPassword?.value || '');
  renderPasswordStrengthHint(els.forgotPasswordStrength, els.forgotNewPassword?.value || '');
  renderOtpCooldown();
  renderForgotOtpCooldown();
  setMfaActionBusyState();
  syncMfaCopyButtonsState();
  renderStudentAttendanceDemoToggle();
  setRegisterInFlight(false);
  setForgotPasswordPanel(false);
  updateAuthBadges();
  applyRoleUI();
  setTopNavActive(state.ui.activeModule);
  renderProfileSecurity();

  const restored = await restoreSession();
  if (restored && !authState.mfaSetupRequired) {
    try {
      await refreshAll();
    } catch (error) {
      log(error.message);
    }
  }
}

init();
