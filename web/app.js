const DAY_LABELS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const AI_MODEL = 'gemini-3-flash-preview';
const PUTER_SDK_URL = 'https://js.puter.com/v2/';
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
const FOOD_SERVICE_START_MINUTES = 10 * 60;
const FOOD_SERVICE_END_MINUTES = 21 * 60;
const FOOD_SERVICE_HOURS_LABEL = '10:00 AM - 9:00 PM';
const FOOD_DEMAND_LIVE_REFRESH_MS = 10000;
const SESSION_IDLE_LOGOUT_MS = 15 * 60 * 1000;
const SESSION_MAX_LOGOUT_MS = 30 * 60 * 1000;
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
const FOOD_POPULAR_SPOT_IDS = ['oven-express', 'kitchen-ette-block41', 'nk-food-court-bh2-6'];
const FOOD_SHOP_GROUPS = [
  { key: 'popular', title: 'Popular Spots', subtitle: 'Most loved by students right now' },
  { key: 'unimall17', title: 'UniMall — Block 17', subtitle: 'Branded chains' },
  { key: 'bh1', title: 'BH-1 Food Kiosk Area', subtitle: 'Quick meals and snacks' },
  { key: 'bh2to6', title: 'BH-2 to BH-6 Kiosk Cluster', subtitle: 'High variety cluster' },
  { key: 'block41', title: 'Block-41 Food Court Zone', subtitle: 'Tea + snack hub' },
  { key: 'block34', title: 'Block-34 Kiosk Area', subtitle: 'Hidden popular picks' },
];
const FOOD_AI_QUICK_CRAVINGS = [
  'Spicy snacks under INR 150',
  'Healthy juice and light meal',
  'Coffee + dessert combo',
  'North Indian full meal',
  'Fast pizza pickup',
];
const FOOD_DELIVERY_POINTS = [
  ['01', 'LIM'],
  ['02', 'Campus Cafe'],
  ['03', 'Auditorium'],
  ['04', 'LIT Engineering'],
  ['05', 'LIT Pharmacy'],
  ['06', 'LIT Architecture'],
  ['07', 'LIT Pharmacy'],
  ['08', 'Shri Baldev Raj Mittal Hospital'],
  ['09', 'Girls Hostel 1'],
  ['10', 'Girls Hostel 2'],
  ['11', 'Girls Hostel 3'],
  ['12', 'Girls Hostel 4'],
  ['13', 'LIT Polytechnic'],
  ['14', 'Business Block'],
  ['15', 'Lovely Mall'],
  ['16', 'Hotel Mgt'],
  ['17', 'Mall - II'],
  ['18', 'Education'],
  ['19', 'Auditorium'],
  ['20', 'LSB'],
  ['21', 'Girl Hostel 5'],
  ['22', 'Girl Hostel 6'],
  ['23', 'Auditorium'],
  ['24', 'Auditorium'],
  ['25', 'Engineering'],
  ['26', 'Engineering'],
  ['27', 'Engineering'],
  ['28', 'Engineering'],
  ['29', 'Engineering'],
  ['30', 'Chancellor Office'],
  ['31', 'Administrative Block'],
  ['32', 'Administrative Block'],
  ['33', 'Engineering'],
  ['34', 'Engineering'],
  ['35', 'Engineering'],
  ['36', 'Engineering'],
  ['37', 'Engineering'],
  ['38', 'Engineering'],
  ['39', 'STP'],
  ['40', 'Store'],
  ['41', 'Staff Residence'],
  ['42', 'Staff Residence'],
  ['43', 'Boys Hostel 1'],
  ['45', 'Boys Hostel 2'],
  ['46', 'Boys Hostel 3'],
  ['47', 'Boys Hostel 4'],
  ['51', 'Boys Hostel 5'],
  ['52', 'Boys Hostel 6'],
  ['53', 'Academic Block 1'],
  ['54', 'Academic Block 2'],
  ['55', 'Academic Block 3'],
  ['71', 'Boys Studios 8'],
  ['72', 'Boys Studios 9'],
  ['73', 'Boys Studios 10'],
];
const FOOD_SHOP_DIRECTORY = [
  { id: 'dominos', name: "Domino's Pizza", block: 'UniMall — Block 17', group: 'unimall17', cover: 'https://www.dominos.co.in/theme2/front/assets/banner2.webp' },
  { id: 'wow-momo', name: 'Wow! Momo', block: 'UniMall — Block 17', group: 'unimall17', cover: 'https://marinamallchennai.com/wp-content/uploads/2020/08/rsz_elv02242-min.jpg' },
  { id: 'chicago-pizza', name: 'Chicago Pizza', block: 'UniMall — Block 17', group: 'unimall17', cover: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTBZ3sJ3rGxFwTen7xou80brkNAi2U3v4yN5Q&s' },
  { id: 'ccd', name: 'Café Coffee Day', block: 'UniMall — Block 17', group: 'unimall17', cover: 'https://www.shutterstock.com/image-photo/mumbai-india-feb-23-cafe-600nw-2605028205.jpg' },
  { id: 'andhra-food-house', name: 'Andhra Food House', block: 'BH-1', group: 'bh1', cover: 'https://lpubeyondclasses.weebly.com/uploads/5/9/7/7/59774945/1234924.jpg?250' },
  { id: 'ab-juice-bar-bh1', name: 'AB Juice Bar', block: 'BH-1', group: 'bh1', cover: 'https://happenings.lpu.in/wp-content/uploads/2018/02/7.2-1.jpg' },
  { id: 'telugu-vantillu', name: 'Telugu Vantillu', block: 'BH-1', group: 'bh1', cover: 'https://b.zmtcdn.com/data/pictures/4/20876424/72e4680b9c9a66c3d157c1ceac1e5ceb.jpg' },
  { id: 'campus-fusion-bh1', name: 'Campus Fusion', block: 'BH-1', group: 'bh1', cover: 'https://b.zmtcdn.com/data/pictures/chains/7/20402557/7c9fe2b6a8ae9d14736d68d1f11e18be_featured_v2.jpg' },
  { id: 'havmor-ice-cream', name: 'Havmor Ice Cream', block: 'BH-1', group: 'bh1', cover: 'https://content.jdmagicbox.com/v2/comp/delhi/l6/011pxx11.xx11.221228184909.u2l6/catalogue/-1qb99pzzka.jpg' },
  { id: 'nk-food-court-bh2-6', name: 'NK Food Court', block: 'BH-2–6', group: 'bh2to6', cover: 'https://rajasthancab.b-cdn.net/uploads/blog/1747049704-blog-image.webp' },
  { id: 'pizza-express', name: 'Pizza Express', block: 'BH-2–6', group: 'bh2to6', cover: 'https://pizzaexpress.in/wp-content/uploads/2025/02/Lulu2-1024x683.jpg' },
  { id: 'juice-world', name: 'Juice World', block: 'BH-2–6', group: 'bh2to6', cover: 'https://b.zmtcdn.com/data/pictures/9/19235239/b4e9bc5386c4242cc71516a02664d38a.jpg?fit=around%7C960:500&crop=960:500;*,*' },
  { id: 'chinese-eatery', name: 'Chinese Eatery', block: 'BH-2–6', group: 'bh2to6', cover: 'https://dynamic-media-cdn.tripadvisor.com/media/photo-o/1a/b0/43/c4/traditional-chinese-restaurant.jpg?w=1200&h=1200&s=1' },
  { id: 'nand-juice-bh2-6', name: 'Nand Juice', block: 'BH-2–6', group: 'bh2to6', cover: 'https://content.jdmagicbox.com/v2/comp/phagwara/u2/9999p1824.1824.251108083345.v2u2/catalogue/nand-juice-corner-phagwara-juice-centres-zw6zkfkvyn.jpg' },
  { id: 'campus-fusion-bh2-6', name: 'Campus Fusion', block: 'BH-2–6', group: 'bh2to6', cover: 'https://b.zmtcdn.com/data/pictures/chains/7/20402557/7c9fe2b6a8ae9d14736d68d1f11e18be_featured_v2.jpg' },
  { id: 'kannu-ki-chai', name: 'Kannu Ki Chai', block: 'Block-41', group: 'block41', cover: 'https://kannukichai.com/wp-content/uploads/2024/01/2023.jpg' },
  { id: 'yippee', name: 'Yippee', block: 'Block-41', group: 'block41', cover: 'https://www.retail4growth.com/public/uploads/editor/2024-07-10/1720614018.jpeg' },
  { id: 'kitchen-ette-block41', name: 'Kitchen Ette', block: 'Block-41', group: 'block41', cover: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSmbgumgEId2NhiLJru_xhGeGI8tU1PxzQLfg&s' },
  { id: 'ab-juice-bar-block41', name: 'AB Juice Bar', block: 'Block-41', group: 'block41', cover: 'https://content.jdmagicbox.com/v2/comp/undefined/w3/0141px141.x141.230203182338.v9w3/catalogue/ab-juice-club-mansarovar-jaipur-juice-centres-gr4f661o1u.jpg' },
  { id: 'basant-ice-cream-corner', name: 'Basant Ice Cream Corner', block: 'Block-41', group: 'block41', cover: 'https://content.jdmagicbox.com/comp/ludhiana/y3/0161px161.x161.120521093214.l4y3/catalogue/basant-ice-cream-ferozepur-road-ludhiana-ice-cream-distributors-gw5p0o36b2.jpg' },
  { id: 'northern-delights', name: 'Northern Delights', block: 'Block-34', group: 'block34', cover: 'https://static.where-e.com/India/Uttar_Pradesh_State/Northern-Delights_8fdc73f2560fa6ab3e05f456a769dd54.jpg' },
  { id: 'bengali-bawarchi', name: 'Bengali Bawarchi', block: 'Block-34', group: 'block34', cover: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSKKktniVK5RYKu_34CySDu6wACHGex2XAq0g&s' },
  { id: 'tandoor-hub', name: 'Tandoor Hub', block: 'Block-34', group: 'block34', cover: 'https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy,f_auto,q_auto,w_366/RX_THUMBNAIL/IMAGES/VENDOR/2024/10/17/0335aa92-1e2e-45d5-8f57-b3fe9dcc9482_410561.jpg' },
  { id: 'nand-juice-block34', name: 'Nand Juice', block: 'Block-34', group: 'block34', cover: 'https://content.jdmagicbox.com/v2/comp/phagwara/u2/9999p1824.1824.251108083345.v2u2/catalogue/nand-juice-corner-phagwara-juice-centres-zw6zkfkvyn.jpg' },
  { id: 'oven-express', name: 'Oven Express', block: 'Campus-wide', group: 'campus', cover: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTyxtuHgUZkBkQbEe1FqMNEM0kapS4Lqgwz6g&s' },
];

let puterSdkPromise = null;
let liveDateTimeTimer = null;
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
let sessionIdleTimer = null;
let sessionMaxTimer = null;
let sessionActivityBound = false;
let lastSessionActivityPingMs = 0;
const runtimeUiStore = {
  profilePromptSeenByUser: new Set(),
  themeByUser: new Map(),
};

const state = {
  absentees: [],
  demand: [],
  capacity: [],
  attendanceSummary: [],
  peakTimes: [],
  overview: { blocks: 0, classrooms: 0, courses: 0, faculty: 0, students: 0 },
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
    orderDate: '',
    shops: [],
    menuByShop: {},
    selectedShopId: '',
    cart: {
        shopId: '',
        items: [],
    },
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
  },
  remedial: {
    classes: [],
    selectedClassId: null,
    selectedClassAttendance: [],
  },
  student: {
    weekStart: '',
    minTimetableDate: '2026-01-21',
    viewDate: '',
    timetable: [],
    kpiTimetable: [],
    timetableCache: {},
    timetablePrefetching: new Set(),
    timetableRequestToken: 0,
    timetableRepairInFlight: false,
    kpiRefreshInFlight: false,
    selectedScheduleId: null,
    registrationNumber: '',
    profilePhotoDataUrl: '',
    profilePhotoLockedUntil: null,
    profilePhotoCanUpdateNow: true,
    profilePhotoLockDaysRemaining: 0,
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
    selfieDataUrl: '',
    attendanceAggregate: null,
    attendanceHistory: [],
    attendanceHistoryByCourse: {},
    attendanceDetailsCourseKey: '',
    kpiScheduleId: null,
  },
  faculty: {
    schedules: [],
    selectedScheduleId: null,
    classDate: '',
    dashboard: null,
    selectedSubmissionIds: new Set(),
    analysisHistory: [],
    classroomPhotoDataUrl: '',
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
    chotuOpen: false,
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
  forgotOtpCooldownUntilMs: 0,
  forgotOtpRequestInFlight: false,
  forgotResetToken: '',
  forgotResetTokenExpiresAt: '',
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
  authSendAltWrap: document.getElementById('auth-send-alt-wrap'),
  authOtpWrap: document.getElementById('auth-otp-wrap'),
  authSendAltOtp: document.getElementById('auth-send-alt-otp'),
  authName: document.getElementById('auth-name'),
  authDepartment: document.getElementById('auth-department'),
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
  otpDebug: document.getElementById('otp-debug'),
  accountMenuBtn: document.getElementById('account-menu-btn'),
  accountMenuDropdown: document.getElementById('account-menu-dropdown'),
  accountMenuAvatar: document.getElementById('account-menu-avatar'),
  accountMenuInitial: document.getElementById('account-menu-initial'),
  accountDropdownPhoto: document.getElementById('account-dropdown-photo'),
  accountDropdownEmail: document.getElementById('account-dropdown-email'),
  accountDropdownReg: document.getElementById('account-dropdown-reg'),
  viewProfileBtn: document.getElementById('view-profile-btn'),
  logoutBtn: document.getElementById('logout-btn'),
  navDashboardBtn: document.getElementById('nav-dashboard-btn'),
  navCoursesBtn: document.getElementById('nav-courses-btn'),
  navAttendanceBtn: document.getElementById('nav-attendance-btn'),
  topNavAttendanceBtn: document.getElementById('top-nav-attendance'),
  topNavFoodBtn: document.getElementById('top-nav-food'),
  topNavAdministrativeBtn: document.getElementById('top-nav-administrative'),
  topNavRemedialBtn: document.getElementById('top-nav-remedial'),
  modulePanels: document.querySelectorAll('.module-panel[data-module]'),
  accountSection: document.getElementById('account-section'),
  profilePrimaryEmail: document.getElementById('profile-primary-email'),
  profileAlternateEmail: document.getElementById('profile-alternate-email'),
  saveAlternateEmailBtn: document.getElementById('save-alternate-email-btn'),
  accountLogoutBtn: document.getElementById('account-logout-btn'),
  alternateEmailStatus: document.getElementById('alternate-email-status'),

  executiveSection: document.getElementById('executive-section'),
  studentSection: document.getElementById('student-section'),
  facultySection: document.getElementById('faculty-section'),
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
  foodEnableLocationBtn: document.getElementById('food-enable-location-btn'),
  foodLocationStatus: document.getElementById('food-location-status'),
  foodStatusMsg: document.getElementById('food-status-msg'),
  foodDemandChartModule: document.getElementById('food-demand-chart-module'),
  foodDemandFreshness: document.getElementById('food-demand-freshness'),
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
  remedialDate: document.getElementById('remedial-date'),
  remedialStartTime: document.getElementById('remedial-start-time'),
  remedialEndTime: document.getElementById('remedial-end-time'),
  remedialTopic: document.getElementById('remedial-topic'),
  remedialCreateBtn: document.getElementById('remedial-create-btn'),
  remedialFacultyStatus: document.getElementById('remedial-faculty-status'),
  remedialClassesList: document.getElementById('remedial-classes-list'),
  remedialClassSelect: document.getElementById('remedial-class-select'),
  remedialRefreshAttendanceBtn: document.getElementById('remedial-refresh-attendance-btn'),
  remedialAttendanceList: document.getElementById('remedial-attendance-list'),
  remedialCodeInput: document.getElementById('remedial-code-input'),
  remedialMarkBtn: document.getElementById('remedial-mark-btn'),
  remedialStudentStatus: document.getElementById('remedial-student-status'),

  weekStartDate: document.getElementById('week-start-date'),
  prevWeekBtn: document.getElementById('prev-week-btn'),
  goCurrentWeekBtn: document.getElementById('go-current-week-btn'),
  nextWeekBtn: document.getElementById('next-week-btn'),
  loadTimetableBtn: document.getElementById('load-timetable-btn'),
  timetableViewInfo: document.getElementById('timetable-view-info'),
  timetableGrid: document.getElementById('timetable-grid'),
  themeToggleBtn: document.getElementById('theme-toggle-btn'),
  selectedClassLabel: document.getElementById('selected-class-label'),
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
  studentAggregatePercent: document.getElementById('student-aggregate-percent'),
  studentAttendedDelivered: document.getElementById('student-attended-delivered'),
  studentAggregateCourses: document.getElementById('student-aggregate-courses'),
  attendanceDetailsModal: document.getElementById('attendance-details-modal'),
  attendanceDetailsTitle: document.getElementById('attendance-details-title'),
  attendanceDetailsMeta: document.getElementById('attendance-details-meta'),
  dashboardTitle: document.getElementById('dashboard-title'),
  dashboardSubtitle: document.getElementById('dashboard-subtitle'),
  attendanceDetailsList: document.getElementById('attendance-details-list'),
  attendanceDetailsCloseBtn: document.getElementById('attendance-details-close-btn'),

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
  const line = document.createElement('div');
  line.className = 'log-line';
  line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  els.statusLog.prepend(line);
}

function setAuthMessage(message, isError = false) {
  const isLight = document.body.classList.contains('ums-theme');
  els.authMessage.textContent = message;
  els.authMessage.style.color = isError
    ? (isLight ? '#b23322' : '#ffaf93')
    : (isLight ? '#4b6783' : '#c0dbf3');
}

function setForgotMessage(message, isError = false) {
  if (!els.forgotMessage) {
    return;
  }
  const isLight = document.body.classList.contains('ums-theme');
  els.forgotMessage.textContent = message || '';
  els.forgotMessage.style.color = isError
    ? (isLight ? '#b23322' : '#ffaf93')
    : (isLight ? '#4b6783' : '#c0dbf3');
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
  els.otpDebug.classList.add('hidden');
  els.otpDebug.textContent = '';
  hideOtpPopup();
  setAuthMode('login');
  setForgotPasswordPanel(false);
  resetForgotPasswordState({ clearFields: true });
  setAuthMessage(message);
}

function closeAuthOverlay() {
  document.body.classList.remove('auth-open');
  els.authOverlay.classList.add('hidden');
  els.otpDebug.classList.add('hidden');
  els.otpDebug.textContent = '';
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

function hasSeenProfileSetupPrompt(userEmail = '') {
  return runtimeUiStore.profilePromptSeenByUser.has(profilePromptStorageKey(userEmail));
}

function markProfileSetupPromptSeen(userEmail = '') {
  runtimeUiStore.profilePromptSeenByUser.add(profilePromptStorageKey(userEmail));
}

function getInitialTheme(userEmail = '') {
  const scoped = normalizeTheme(runtimeUiStore.themeByUser.get(themeStorageKey(userEmail)));
  if (scoped) {
    return scoped;
  }
  return 'light';
}

function applyTheme(theme, options = {}) {
  const { persist = true, userEmail = authState.user?.email || '' } = options;
  const resolved = theme === 'light' ? 'light' : 'dark';
  state.ui.theme = resolved;
  document.body.classList.toggle('ums-theme', resolved === 'light');
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
}

function toggleTheme() {
  applyTheme(state.ui.theme === 'dark' ? 'light' : 'dark', {
    persist: true,
    userEmail: authState.user?.email || '',
  });
}

function renderLiveDateTime() {
  if (!els.liveDateTime) {
    return;
  }
  const now = new Date();
  const formatted = new Intl.DateTimeFormat(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  }).format(now);
  els.liveDateTime.textContent = `${formatted} (Local Time)`;
  renderFoodFreshnessIndicators();
  renderFoodDemandFreshnessIndicator();
  applyFoodRealtimeAvailability({ showStatusOnTransition: true });
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
  if (studentRealtimeTimer) {
    return;
  }

  studentRealtimeTimer = setInterval(async () => {
    if (!authState.user || authState.user.role !== 'student') {
      return;
    }
    if (document.body.classList.contains('auth-open')) {
      return;
    }
    if (state.student.autoRefreshBusy) {
      return;
    }

    state.student.autoRefreshBusy = true;
    try {
      await refreshStudentKpiTimetable({ forceNetwork: true });
      await loadStudentTimetable({ forceNetwork: true });
      await loadStudentAttendanceInsights();
    } catch (error) {
      log(error.message || 'Student realtime refresh failed');
    } finally {
      state.student.autoRefreshBusy = false;
    }
  }, 45000);
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
  if (moduleRealtimeTimer) {
    return;
  }
  moduleRealtimeTimer = setInterval(async () => {
    if (!authState.user || moduleRealtimeBusy) {
      return;
    }
    if (document.body.classList.contains('auth-open')) {
      return;
    }
    if (authState.user.role === 'student' && state.ui.activeModule === 'attendance') {
      return;
    }
    moduleRealtimeBusy = true;
    try {
      await refreshActiveModuleData();
    } catch (error) {
      log(error.message || 'Module realtime refresh failed');
    } finally {
      moduleRealtimeBusy = false;
    }
  }, 45000);
}

function renderAccountMenuProfile() {
  const photo = state.student.profilePhotoDataUrl || '';
  const email = authState.user?.email || 'guest@example.com';
  const regNo = state.student.registrationNumber || 'Not set';

  if (els.accountDropdownEmail) {
    els.accountDropdownEmail.textContent = email;
  }
  if (els.accountDropdownReg) {
    const prefix = authState.user?.role === 'student' ? 'Reg No' : 'Role';
    const value = authState.user?.role === 'student' ? regNo : (authState.user?.role || 'unauthenticated');
    els.accountDropdownReg.textContent = `${prefix}: ${value}`;
  }

  if (els.accountMenuInitial) {
    els.accountMenuInitial.textContent = email.charAt(0).toUpperCase() || 'G';
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
    if (els.logoutBtn) {
      els.logoutBtn.classList.add('hidden');
    }
    closeAccountDropdown();
    renderAccountMenuProfile();
    return;
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

function updateChotuVisibility() {
  if (!els.chotuWidget) {
    return;
  }
  const visible = Boolean(
    authState.user && getSanitizedModuleKey(state.ui.activeModule) === 'food'
  );
  setHidden(els.chotuWidget, !visible);
  if (!visible) {
    setChotuOpen(false);
    return;
  }
  renderFoodAiQuickChips();
}

function setHidden(element, hidden) {
  if (!element) {
    return;
  }
  element.classList.toggle('hidden', hidden);
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
  if (role === 'faculty' || role === 'owner') {
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
    setAuthMessage('Login first with email/password, request OTP, then verify to continue.');
  }
  renderOtpCooldown();
  renderForgotOtpCooldown();
}

function syncAuthRoleForm() {
  if (!isSignupMode()) {
    setHidden(els.authSemesterWrap, true);
    setHidden(els.authParentEmailWrap, true);
    return;
  }
  const role = selectedAuthRole();
  const isStudent = role === 'student';
  setHidden(els.authSemesterWrap, !isStudent);
  setHidden(els.authParentEmailWrap, !isStudent);
}

const MODULE_KEYS = new Set(['attendance', 'food', 'administrative', 'remedial']);

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
    return 'administrative';
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
  if (key === 'attendance') {
    return role === 'student' || role === 'faculty';
  }
  if (key === 'food') {
    return role === 'student' || role === 'faculty' || role === 'owner';
  }
  if (key === 'administrative') {
    return role === 'student' || role === 'faculty' || role === 'admin';
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
    els.topNavFoodBtn,
    els.topNavAdministrativeBtn,
    els.topNavRemedialBtn,
  ].filter(Boolean);

  for (const button of topButtons) {
    const isActive = button.dataset.module === active;
    button.classList.toggle('active', isActive);
    button.setAttribute('aria-current', isActive ? 'page' : 'false');
  }
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
  const role = authState.user?.role;
  if (role === 'admin') {
    return 'administrative';
  }
  return 'attendance';
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
}

function updateDashboardHeroByRole() {
  if (!els.dashboardTitle || !els.dashboardSubtitle) {
    return;
  }
  const role = authState.user?.role;
  if (role === 'faculty') {
    els.dashboardTitle.textContent = 'Faculty Dashboard';
  } else if (role === 'owner') {
    els.dashboardTitle.textContent = 'Vendor Dashboard';
  } else {
    els.dashboardTitle.textContent = 'Vertos Dashboard';
  }
  els.dashboardSubtitle.textContent = 'Your all in one Uni-need.';
}

function applyRoleUI() {
  const role = authState.user?.role;
  const isFaculty = role === 'faculty';
  const isOwner = role === 'owner';
  const isStudent = role === 'student';
  const isFoodOperator = isFaculty || isOwner;
  const activeModule = getSanitizedModuleKey(state.ui.activeModule);
  state.ui.activeModule = activeModule;

  setHidden(els.accountSection, true);
  setHidden(els.executiveSection, !authState.user || activeModule !== 'administrative');
  setHidden(els.studentSection, !isStudent || activeModule !== 'attendance');
  setHidden(els.facultySection, !isFaculty || activeModule !== 'attendance');
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

  setTopNavActive(activeModule);
  const moduleButtons = [
    els.topNavAttendanceBtn,
    els.topNavFoodBtn,
    els.topNavAdministrativeBtn,
    els.topNavRemedialBtn,
  ].filter(Boolean);
  for (const button of moduleButtons) {
    button.disabled = !authState.user;
  }

  if (isStudent) {
    startStudentTimetableStatusTicker();
  } else {
    stopStudentTimetableStatusTicker();
    closeAttendanceDetailsModal();
  }

  if (!authState.user) {
    setSidebarActive('dashboard');
  }
  updateDashboardHeroByRole();
  renderEnrollmentSummary();
  syncFoodLocationMonitoringByModule();
  updateChotuVisibility();
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
    return els.executiveSection;
  }
  if (navKey === 'attendance') {
    return document.getElementById('absentee-card') || els.executiveSection;
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

  if (authState.user.role === 'student' && requiresStudentProfileSetup()) {
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
    els.alternateEmailStatus.textContent = 'Login once using your primary email to enable alternate Gmail OTP.';
    return;
  }
  if (authState.user.alternate_email) {
    els.alternateEmailStatus.textContent = `Alternate OTP email active: ${authState.user.alternate_email}`;
    return;
  }
  els.alternateEmailStatus.textContent = 'No alternate Gmail configured.';
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

function showProfilePhotoLockPopup() {
  const lockedUntil = formatLockDateTime(state.student.profilePhotoLockedUntil);
  const remaining = Math.max(0, Number(state.student.profilePhotoLockDaysRemaining || 0));
  showOtpPopup(
    'Profile Photo Locked',
    `Profile photo locked until ${lockedUntil}. Remaining: ${remaining} day(s).`,
    { tone: 'cooldown', loading: false, closable: true }
  );
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
  const showEnrollment = String(tabKey || '').toLowerCase() === 'enrollment';
  if (els.profileTabDetailsBtn && els.profileTabEnrollmentBtn) {
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
  state.student.profileSetupRequired = Boolean(required);
  els.profileModal.classList.remove('hidden');
  if (els.profileModalTitle) {
    els.profileModalTitle.textContent = required ? 'Complete Profile Setup' : 'Profile Settings';
  }
  if (els.profileModalSubtitle) {
    els.profileModalSubtitle.textContent = required
      ? 'Upload your profile photo and set registration number before using the portal.'
      : 'Manage profile photo, registration number, and alternate OTP email.';
  }
  if (els.profileCloseBtn) {
    els.profileCloseBtn.disabled = required;
    setHidden(els.profileCloseBtn, required);
  }
  setProfileTab('details');
  renderEnrollmentSummary();
}

function closeProfileModal() {
  if (!els.profileModal) {
    return;
  }
  if (state.student.profileSetupRequired) {
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
  return !state.student.registrationNumber || !state.student.profilePhotoDataUrl;
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
    if (els.profileRegistrationNumber) {
      els.profileRegistrationNumber.value = '';
      els.profileRegistrationNumber.disabled = false;
    }
    if (els.profileAlternateEmail) {
      els.profileAlternateEmail.value = '';
      els.profileAlternateEmail.disabled = true;
    }
    if (els.saveAlternateEmailBtn) {
      els.saveAlternateEmailBtn.disabled = true;
    }
    if (els.authSendAltOtp) {
      els.authSendAltOtp.checked = false;
      els.authSendAltOtp.disabled = false;
    }
    if (els.alternateEmailStatus) {
      els.alternateEmailStatus.textContent = '';
    }
    setProfileTab('details');
    renderEnrollmentSummary();
    closeAccountDropdown();
    return;
  }

  if (els.profilePrimaryEmail) {
    els.profilePrimaryEmail.value = authState.user.email || '';
  }
  const isStudent = authState.user.role === 'student';
  if (els.profileRegistrationNumber) {
    els.profileRegistrationNumber.value = state.student.registrationNumber || '';
    els.profileRegistrationNumber.disabled = !isStudent || Boolean(state.student.registrationNumber);
  }
  if (els.profileAlternateEmail) {
    els.profileAlternateEmail.value = authState.user.alternate_email || '';
    els.profileAlternateEmail.disabled = !authState.user.primary_login_verified;
  }
  if (els.profilePhotoInput) {
    els.profilePhotoInput.disabled = !isStudent;
  }
  if (els.saveAlternateEmailBtn) {
    els.saveAlternateEmailBtn.disabled = !authState.user.primary_login_verified;
  }
  if (els.saveProfilePhotoBtn) {
    els.saveProfilePhotoBtn.disabled = !isStudent;
  }
  if (els.authSendAltOtp) {
    els.authSendAltOtp.disabled = false;
  }
  renderAlternateEmailStatus();
  renderEnrollmentSummary();

  if (requiresStudentProfileSetup()) {
    if (state.student.profileSetupRequired) {
      openProfileModal({ required: true });
    }
  } else if (els.profileModal && state.student.profileSetupRequired) {
    state.student.profileSetupRequired = false;
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
  state.food.selectedShopId = '';
  state.food.menuByShop = {};
  state.food.cart.shopId = '';
  state.food.cart.items = [];
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
  state.ui.chotuOpen = false;
  if (user?.role === 'student') {
    state.student.minTimetableDate = '2026-01-21';
    state.student.profileLoaded = false;
    state.student.enrollmentLoaded = false;
    state.student.hasEnrollmentVideo = false;
    state.student.enrollmentRequired = false;
    state.student.enrollmentFrames = [];
    state.student.enrollmentCaptureRunning = false;
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
    void ensureCurrentWeekTimetableVisible({ forceNetwork: true }).catch((error) => {
      log(error.message || 'Failed to auto-load current week timetable');
    });
  } else {
    stopStudentRealtimeTicker();
  }
  startModuleRealtimeTicker();
  syncFoodDemandLiveTicker();
  startSessionWatchdog();
}

function clearSession() {
  stopFoodLocationMonitoring();
  stopFoodDemandLiveTicker();
  authState.token = '';
  authState.user = null;
  authState.pendingEmail = '';
  authState.otpCooldownUntilMs = 0;
  authState.otpRequestInFlight = false;
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
  applyTheme(getInitialTheme(''), { persist: false, userEmail: '' });
  persistToken('');
  state.ui.activeModule = 'attendance';
  state.student.selectedScheduleId = null;
  state.student.minTimetableDate = '2026-01-21';
  state.student.viewDate = '';
  state.student.timetable = [];
  state.student.kpiTimetable = [];
  state.student.timetableCache = {};
  state.student.timetablePrefetching.clear();
  state.student.timetableRequestToken = 0;
  state.student.kpiRefreshInFlight = false;
  state.student.kpiScheduleId = null;
  state.student.registrationNumber = '';
  state.student.profilePhotoDataUrl = '';
  state.student.profilePhotoLockedUntil = null;
  state.student.profilePhotoCanUpdateNow = true;
  state.student.profilePhotoLockDaysRemaining = 0;
  state.student.profileLoaded = false;
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
  state.faculty.selectedScheduleId = null;
  state.faculty.selectedSubmissionIds.clear();
  state.student.pendingProfilePhotoDataUrl = '';
  state.student.profileSetupRequired = false;
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
  state.food.orderDate = '';
  state.food.shops = [];
  state.food.menuByShop = {};
  state.food.selectedShopId = '';
  state.food.cart.shopId = '';
  state.food.cart.items = [];
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
  state.food.location.monitorBusy = false;
  state.food.location.latitude = null;
  state.food.location.longitude = null;
  state.food.location.accuracyM = null;
  state.food.location.lastVerifiedAtMs = 0;
  state.food.location.message = '';
  state.ui.chotuOpen = false;
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
  setChotuOpen(false);
  stopEnrollmentCameraStream();
  stopStudentRealtimeTicker();
  stopStudentTimetableStatusTicker();
  stopModuleRealtimeTicker();
  stopFoodDemandLiveTicker();
}

async function api(path, options = {}) {
  const { skipAuth = false, ...requestOptions } = options;
  const method = String(requestOptions.method || 'GET').toUpperCase();
  const headers = {
    'Content-Type': 'application/json',
    ...(requestOptions.headers || {}),
  };

  if (!skipAuth && authState.token) {
    headers.Authorization = `Bearer ${authState.token}`;
  }

  const response = await fetch(path, {
    ...requestOptions,
    headers,
    credentials: requestOptions.credentials || 'same-origin',
    cache: requestOptions.cache || (method === 'GET' || method === 'HEAD' ? 'no-store' : undefined),
  });

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
  const minDate = String(state.student.minTimetableDate || '2026-01-21');
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
  const enrolled = state.attendanceSummary.length;
  const absent = state.absentees.length;
  const present = Math.max(enrolled - absent, 0);
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

  column.append(wrap, value, label, delta);
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
    if (!bar || !value || !label || !delta) {
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

    column.dataset.orders = String(nextOrders);
    column.dataset.utilization = String(nextUtilization);
    container.appendChild(column);
  }

  for (const [slotKey, column] of existingColumns.entries()) {
    if (!activeKeys.has(slotKey)) {
      if (column._demandPulseTimer) {
        window.clearTimeout(column._demandPulseTimer);
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
  renderDemandChartIn(els.foodDemandChartModule, { animate });
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

    const meta = document.createElement('div');
    meta.className = 'hbar-meta';
    meta.innerHTML = `<span>${item.course_code} • ${item.classroom}</span><span>${item.utilization_percent}%</span>`;

    const track = document.createElement('div');
    track.className = 'hbar-track';

    const fill = document.createElement('div');
    fill.className = 'hbar-fill';
    fill.style.setProperty('--w', String(Math.max(3, Math.min(item.utilization_percent, 100))));

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
  const enrolled = Array.isArray(state.attendanceSummary) ? state.attendanceSummary.length : 0;
  const absent = Array.isArray(state.absentees) ? state.absentees.length : 0;
  const present = Math.max(0, enrolled - absent);
  const attendanceHealth = enrolled ? clampPercent((present / enrolled) * 100) : 0;

  const capacityRows = Array.isArray(state.capacity) ? state.capacity : [];
  const capacityAverage = capacityRows.length
    ? clampPercent(
      capacityRows.reduce((sum, row) => sum + Number(row.utilization_percent || 0), 0) / capacityRows.length
    )
    : 0;
  const capacityBalance = capacityRows.length
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
  const workloadIndex = workloadRows.length
    ? clampPercent(100 - Math.max(0, avgStudentsPerFaculty - 40) * 1.1)
    : 0;

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
  state.overview = await api('/resources/overview');
  updateMetrics();
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
  if (!shouldRunFoodDemandLiveTicker()) {
    stopFoodDemandLiveTicker();
    return;
  }
  if (foodDemandLiveTimer) {
    return;
  }
  foodDemandLiveTimer = window.setInterval(() => {
    void refreshFoodDemandLiveTick();
  }, FOOD_DEMAND_LIVE_REFRESH_MS);
}

async function refreshCapacity() {
  state.capacity = await api('/resources/capacity-utilization');
  renderCapacityChart();
}

function setFoodStatus(message, isError = false) {
  if (!els.foodStatusMsg) {
    return;
  }
  els.foodStatusMsg.textContent = String(message || '');
  els.foodStatusMsg.classList.toggle('error-text', Boolean(isError));
}

function setFoodLocationStatus(message, tone = 'warn') {
  if (!els.foodLocationStatus) {
    return;
  }
  els.foodLocationStatus.textContent = String(message || '');
  els.foodLocationStatus.dataset.tone = tone;
}

function setFoodAdminStatus(message, isError = false) {
  if (!els.foodAdminStatusMsg) {
    return;
  }
  els.foodAdminStatusMsg.textContent = String(message || '');
  els.foodAdminStatusMsg.classList.toggle('error-text', Boolean(isError));
}

function normalizeFoodKey(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function shopAliasKey(name, block) {
  return `${normalizeFoodKey(name)}|${normalizeFoodKey(block)}`;
}

const FOOD_SHOP_COVER_BY_ALIAS = new Map(
  FOOD_SHOP_DIRECTORY.map((shop) => [shopAliasKey(shop.name, shop.block), shop.cover || ''])
);
const FOOD_SHOP_COVER_BY_NAME = new Map(
  FOOD_SHOP_DIRECTORY.map((shop) => [normalizeFoodKey(shop.name), shop.cover || ''])
);

function resolveShopCover(name, block) {
  const byAlias = FOOD_SHOP_COVER_BY_ALIAS.get(shopAliasKey(name, block));
  if (byAlias) {
    return byAlias;
  }
  return FOOD_SHOP_COVER_BY_NAME.get(normalizeFoodKey(name)) || '';
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
    return {
      id: String(shop.id),
      apiShopId: Number(shop.id),
      name,
      block,
      group: deriveFoodShopGroup(block),
      cover: resolveShopCover(name, block),
      isPopular: Boolean(shop?.is_popular) || popularNameSet.has(normalizedName),
      rating: Number(shop?.rating || 0),
      averagePrepMinutes: Number(shop?.average_prep_minutes || 18),
    };
  });
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
  const rows = await api(`/food/shops/${shop.apiShopId}/menu-items?active_only=true`);
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
      addOneBtn.disabled = Boolean(menuItem.soldOut) || Number(menuItem.stockQuantity) === 0;
      addOneBtn.addEventListener('click', () => {
        void addMenuItemToCart(shop.id, menuItem, 1, buildItemNote()).catch((error) => {
          setFoodStatus(error.message || 'Failed to update cart.', true);
        });
      });
      const addTwoBtn = document.createElement('button');
      addTwoBtn.className = 'btn';
      addTwoBtn.type = 'button';
      addTwoBtn.textContent = 'Add x2';
      addTwoBtn.disabled = Boolean(menuItem.soldOut) || Number(menuItem.stockQuantity) === 0;
      addTwoBtn.addEventListener('click', () => {
        void addMenuItemToCart(shop.id, menuItem, 2, buildItemNote()).catch((error) => {
          setFoodStatus(error.message || 'Failed to update cart.', true);
        });
      });
      if (menuItem.soldOut || Number(menuItem.stockQuantity) === 0) {
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
      card.innerHTML = `
        <div class="food-shop-cover-wrap">
          <img class="food-shop-cover" src="${escapeHtml(shop.cover || '')}" alt="${escapeHtml(shop.name)} cover" loading="lazy" referrerpolicy="no-referrer">
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

function applyFoodCartPayload(cartPayload, { syncSelectedShop = true } = {}) {
  const raw = (cartPayload && typeof cartPayload === 'object') ? cartPayload : {};
  const parsedShopId = Number(raw.shop_id || 0);
  state.food.cart.shopId = parsedShopId > 0 ? String(parsedShopId) : '';

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
  const locationText = locationOk ? 'Campus location verified' : 'Location not verified yet';
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
  if (!Number(els.foodSlotSelect?.value || 0)) {
    throw new Error('Select break slot before checkout.');
  }
  const selectedSlot = getSelectedFoodSlot();
  if (!selectedSlot) {
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
  if (activeShopId && String(activeShopId) !== normalizedShopId) {
    const message = 'Orders are accepted only from a single shop at a time. Clear or checkout the current cart first.';
    showFoodPopup('Single Shop Rule', message, { isError: true, autoHideMs: 2600 });
    throw new Error(message);
  }
  const menuItemId = Number(menuItem.id);
  const addedLabel = cleanNote ? `${menuItem.name} (${cleanNote})` : menuItem.name;
  const payload = await api('/food/cart/items', {
    method: 'POST',
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
  els.foodAiOutput.textContent = String(message || '');
  els.foodAiOutput.classList.toggle('error-text', Boolean(isError));
}

function renderFoodAiQuickChips() {
  if (!els.foodAiQuickChips) {
    return;
  }
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

function buildChotuCatalogText() {
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
      buildChotuCatalogText(),
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

function setRemedialFacultyStatus(message, isError = false) {
  if (!els.remedialFacultyStatus) {
    return;
  }
  els.remedialFacultyStatus.textContent = String(message || '');
  els.remedialFacultyStatus.classList.toggle('error-text', Boolean(isError));
}

function setRemedialStudentStatus(message, isError = false) {
  if (!els.remedialStudentStatus) {
    return;
  }
  els.remedialStudentStatus.textContent = String(message || '');
  els.remedialStudentStatus.classList.toggle('error-text', Boolean(isError));
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
      const payload = await api(`/attendance/student/timetable?week_start=${weekStart}`);
      cacheTimetableWeekPayload(payload.week_start || weekStart, payload);
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
    const slotElapsed = isTodaySelected && Number.isFinite(slotEndMinutes) && slotEndMinutes <= nowMinutes;
    if (slotElapsed) {
      option.disabled = true;
      option.textContent = `${baseLabel} • Closed`;
    } else {
      option.textContent = hint?.label ? `${baseLabel} • ${hint.label}` : baseLabel;
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
      const shops = await api('/food/shops?active_only=true');
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
      setFoodStatus(`Payment recovered successfully for ${shopName}.`, false);
    } else if (result.status === 'dismissed') {
      setFoodStatus('Payment window closed. Recovery remains available.', true);
    } else {
      setFoodStatus(result.message || 'Payment retry failed. Please retry.', true);
    }
    await refreshFoodModule();
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
  const hasSlot = Boolean(Number(els.foodSlotSelect?.value || 0));
  const orderGate = getFoodRuntimeOrderGate({ slot: selectedSlot });
  const canReview = Boolean(canOrder && hasCartItems && hasSlot && orderGate.canOrderNow);
  const hasDeliveryPoint = Boolean(String(state.food.checkoutDeliveryPoint || els.foodDeliveryBlockSelect?.value || '').trim());
  const locationFresh = isFoodLocationFresh();
  const locationOk = state.food.location.verified && state.food.location.allowed && locationFresh;
  const canCheckout = Boolean(canReview && state.food.checkoutPreviewOpen && hasDeliveryPoint);
  let actionBlockMessage = '';
  if (canOrder && hasCartItems && hasSlot && !orderGate.canOrderNow) {
    actionBlockMessage = orderGate.message;
  }
  if (!canReview && state.food.cartModalTab === 'review') {
    setFoodCartModalTab('cart');
  }
  if (els.foodCartCheckoutBtn) {
    els.foodCartCheckoutBtn.disabled = !canReview;
    if (actionBlockMessage) {
      els.foodCartCheckoutBtn.title = actionBlockMessage;
    } else {
      els.foodCartCheckoutBtn.removeAttribute('title');
    }
  }
  if (els.foodCartTabReviewBtn) {
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

async function refreshFoodModule() {
  if (!authState.user) {
    return;
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
  let [items, slots, ordersForDate, orderHistory, peaks, shops, cartPayload, paymentRecovery] = await Promise.all([
    api('/food/items'),
    api('/food/slots'),
    api(`/food/orders?order_date=${orderDate}&limit=180`),
    api('/food/orders?limit=200'),
    api('/food/peak-times?lookback_days=14'),
    api('/food/shops?active_only=true'),
    shouldLoadCart ? api('/food/cart') : Promise.resolve(null),
    shouldLoadCart ? api('/food/payments/recovery').catch(() => []) : Promise.resolve([]),
  ]);

  if ((!Array.isArray(shops) || !shops.length || !Array.isArray(slots) || !slots.length) && authState.user) {
    try {
      await api('/food/bootstrap/ensure', { method: 'POST' });
      [items, slots, ordersForDate, orderHistory, peaks, shops, cartPayload, paymentRecovery] = await Promise.all([
        api('/food/items'),
        api('/food/slots'),
        api(`/food/orders?order_date=${orderDate}&limit=180`),
        api('/food/orders?limit=200'),
        api('/food/peak-times?lookback_days=14'),
        api('/food/shops?active_only=true'),
        shouldLoadCart ? api('/food/cart') : Promise.resolve(null),
        shouldLoadCart ? api('/food/payments/recovery').catch(() => []) : Promise.resolve([]),
      ]);
    } catch (_) {
      // Keep existing response handling; status banner below will surface configuration issues.
    }
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
  state.food.slots = Array.isArray(slots) ? slots : [];
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
  } else {
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
  renderFoodAiQuickChips();
  renderFoodCart();
  renderFoodOrderStatusTimeline();
  renderFoodAdminOrderOptions();
  syncFoodOrderActionState();
  applyFoodRealtimeAvailability();
  updateFoodLocationActionState();

  if (els.workDate && !els.workDate.value) {
    els.workDate.value = orderDate;
  }
  await refreshDemand(orderDate);

  if (authState.user.role === 'student' && (!state.food.shops.length || !state.food.slots.length)) {
    setFoodStatus('Shops or pickup slots are not configured yet. Please contact faculty/admin.', true);
    return;
  }

  if (authState.user.role !== 'student') {
    stopFoodLocationMonitoring();
    if (authState.user.role === 'owner') {
      setFoodStatus('Owner panel refreshed. You can manage orders for your assigned shop only.');
    } else {
      setFoodStatus('Food module refreshed. You can monitor demand and manage setup.');
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
    const orderGate = getFoodRuntimeOrderGate({ slot: getSelectedFoodSlot(), orderDate });
    if (!orderGate.canBrowseShops || !orderGate.canOrderNow) {
      setFoodStatus(orderGate.message, true);
    } else {
      setFoodStatus('Select one shop, add items, then open cart to checkout. Orders are accepted from one shop at a time.');
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

  let config = null;
  try {
    config = await api('/food/payments/config');
  } catch (error) {
    throw new Error(resolveFoodPaymentError(error, 'Unable to load payment configuration.'));
  }
  if (!config?.key_id) {
    throw new Error('Payments are not configured on server. Razorpay key is missing.');
  }

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

  if (!window.Razorpay) {
    throw new Error('Razorpay checkout failed to load. Refresh the page and retry.');
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
  const slotId = Number(els.foodSlotSelect?.value || 0);
  const orderDate = String(els.foodOrderDate?.value || todayISO()).trim() || todayISO();
  const slot = getSelectedFoodSlot();
  const orderGate = getFoodRuntimeOrderGate({ slot, orderDate });
  const cartItems = Array.isArray(state.food.cart.items) ? state.food.cart.items : [];
  const shop = getShopById(state.food.cart.shopId);

  if (!slotId) {
    throw new Error('Select break slot before checkout.');
  }
  if (!slot || Number(slot.id) !== slotId) {
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
  const deliveryPoint = String(state.food.checkoutDeliveryPoint || els.foodDeliveryBlockSelect?.value || '').trim();
  if (!deliveryPoint) {
    throw new Error('Select delivery block before payment.');
  }
  state.food.checkoutDeliveryPoint = deliveryPoint;

  const locationAllowed = await verifyFoodLocationGate({
    forcePrompt: !state.food.location.verified || !isFoodLocationFresh(),
    silent: false,
  });
  if (!locationAllowed) {
    throw new Error(state.food.location.message || 'Delivery is allowed only inside LPU campus.');
  }

  const checkoutBtn = els.foodCartPayBtn;
  if (checkoutBtn) {
    checkoutBtn.disabled = true;
    checkoutBtn.textContent = 'Processing Payment...';
  }

  try {
    const checkoutIdempotencyKey = [
      studentId,
      orderDate,
      slotId,
      Date.now(),
      Math.random().toString(36).slice(2, 10),
    ].join('-');
    let placedOrders = null;
    try {
      placedOrders = await api('/food/orders/checkout', {
        method: 'POST',
        headers: { 'X-Idempotency-Key': checkoutIdempotencyKey },
        body: JSON.stringify({
          student_id: studentId,
          shop_id: Number(shop.apiShopId || shop.id || 0) || null,
          slot_id: slotId,
          order_date: orderDate,
          idempotency_key: checkoutIdempotencyKey,
          shop_name: shop.name,
          shop_block: shop.block,
          pickup_point: deliveryPoint,
          location_latitude: state.food.location.latitude,
          location_longitude: state.food.location.longitude,
          location_accuracy_m: state.food.location.accuracyM,
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
      setFoodStatus(`Payment successful. Order confirmed with ${shop.name}.`, false);
      log(`Food order paid (${shop.name})`);
      await clearFoodCart({ silent: true });
      closeFoodCartModal();
    } else if (paymentResult.status === 'dismissed') {
      setFoodStatus('Payment window closed. You can retry from Payment Recovery.', true);
    } else {
      setFoodStatus(`Payment failed: ${paymentResult.message || 'Please retry.'}`, true);
    }
    await refreshFoodModule();
  } finally {
    if (checkoutBtn) {
      checkoutBtn.textContent = 'Pay & Place Order';
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

async function refreshAdministrativeModule() {
  if (!authState.user) {
    return;
  }
  if (els.workDate && !els.workDate.value) {
    els.workDate.value = todayISO();
  }
  await Promise.all([
    refreshOverview(),
    refreshCapacity(),
    refreshDemand(els.workDate?.value || todayISO()),
    refreshAttendanceData(),
  ]);
  if (authState.user.role === 'faculty' || authState.user.role === 'admin') {
    const [workload, mongoStatus] = await Promise.all([
      api('/resources/workload-distribution'),
      api('/resources/mongo/status'),
    ]);
    state.resources.workload = Array.isArray(workload) ? workload : [];
    state.resources.mongoStatus = mongoStatus || null;
  } else {
    state.resources.workload = [];
    state.resources.mongoStatus = null;
  }
  renderWorkloadChart();
  renderMongoStatus();
  const healthMetrics = computeAdministrativeHealthMetrics();
  renderAdministrativeHealthMetrics(healthMetrics);
  pushAdministrativeTelemetry(healthMetrics);
  renderAdministrativeTelemetryChart();
}

function renderRemedialCourseOptions() {
  if (!els.remedialCourseSelect) {
    return;
  }
  const role = authState.user?.role;
  const facultyId = Number(authState.user?.faculty_id || 0);
  const courses = Object.values(state.coursesById || {}).filter((course) => {
    if (role === 'faculty') {
      return Number(course.faculty_id || 0) === facultyId;
    }
    return true;
  });

  els.remedialCourseSelect.innerHTML = '';
  if (!courses.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'No eligible courses';
    els.remedialCourseSelect.appendChild(option);
    els.remedialCourseSelect.disabled = true;
    return;
  }

  for (const course of courses) {
    const option = document.createElement('option');
    option.value = String(course.id);
    option.textContent = `${course.code} - ${course.title}`;
    els.remedialCourseSelect.appendChild(option);
  }
  els.remedialCourseSelect.disabled = false;
}

function renderRemedialClassesList() {
  if (!els.remedialClassesList) {
    return;
  }
  els.remedialClassesList.innerHTML = '';
  if (!state.remedial.classes.length) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'No remedial classes scheduled yet.';
    els.remedialClassesList.appendChild(row);
    return;
  }
  for (const entry of state.remedial.classes) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.innerHTML = `
      <span>${escapeHtml(getCourseLabel(entry.course_id))} • ${escapeHtml(String(entry.topic || 'Remedial Session'))}</span>
      <span>${escapeHtml(parseISODateLocal(entry.class_date).toLocaleDateString('en-GB'))} • ${escapeHtml(formatTime(entry.start_time))}-${escapeHtml(formatTime(entry.end_time))} • CODE ${escapeHtml(entry.remedial_code)}</span>
    `;
    els.remedialClassesList.appendChild(row);
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
    option.textContent = `${parseISODateLocal(entry.class_date).toLocaleDateString('en-GB')} • ${getCourseLabel(entry.course_id)} • ${entry.remedial_code}`;
    els.remedialClassSelect.appendChild(option);
  }
  els.remedialClassSelect.disabled = false;
  if (previous && state.remedial.classes.some((entry) => entry.id === previous)) {
    els.remedialClassSelect.value = String(previous);
  }
  state.remedial.selectedClassId = Number(els.remedialClassSelect.value || 0) || null;
}

function renderRemedialAttendanceList() {
  if (!els.remedialAttendanceList) {
    return;
  }
  els.remedialAttendanceList.innerHTML = '';
  const rows = Array.isArray(state.remedial.selectedClassAttendance) ? state.remedial.selectedClassAttendance : [];
  if (!rows.length) {
    const row = document.createElement('div');
    row.className = 'list-item';
    row.textContent = 'No remedial attendance entries for selected class.';
    els.remedialAttendanceList.appendChild(row);
    return;
  }
  for (const student of rows) {
    const row = document.createElement('div');
    row.className = 'list-item good';
    const markedAt = student.marked_at ? new Date(student.marked_at).toLocaleString() : '--';
    row.innerHTML = `
      <span>${escapeHtml(student.student_name || `Student #${student.student_id}`)}</span>
      <span>${escapeHtml(markedAt)} • ${escapeHtml(asTitleCase(student.source))}</span>
    `;
    els.remedialAttendanceList.appendChild(row);
  }
}

async function refreshRemedialClasses() {
  if (!authState.user || (authState.user.role !== 'faculty' && authState.user.role !== 'admin')) {
    state.remedial.classes = [];
    state.remedial.selectedClassAttendance = [];
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

async function refreshRemedialAttendanceForClass(classId = null) {
  const targetClassId = Number(classId || state.remedial.selectedClassId || els.remedialClassSelect?.value || 0);
  if (!targetClassId) {
    state.remedial.selectedClassAttendance = [];
    renderRemedialAttendanceList();
    return;
  }
  state.remedial.selectedClassId = targetClassId;
  const payload = await api(`/makeup/classes/${targetClassId}/attendance`);
  state.remedial.selectedClassAttendance = Array.isArray(payload?.students) ? payload.students : [];
  renderRemedialAttendanceList();
}

async function refreshRemedialModule() {
  if (!authState.user) {
    return;
  }
  if (!Object.keys(state.coursesById).length) {
    await loadCoursesMap();
  }
  renderRemedialCourseOptions();
  if (authState.user.role === 'student') {
    setRemedialStudentStatus('Enter remedial code to mark make-up attendance.');
    return;
  }
  await refreshRemedialClasses();
  if (state.remedial.selectedClassId) {
    await refreshRemedialAttendanceForClass(state.remedial.selectedClassId);
  } else {
    state.remedial.selectedClassAttendance = [];
    renderRemedialAttendanceList();
  }
}

async function createRemedialClass() {
  if (!authState.user || (authState.user.role !== 'faculty' && authState.user.role !== 'admin')) {
    throw new Error('Only faculty/admin can schedule remedial classes.');
  }
  const courseId = Number(els.remedialCourseSelect?.value || 0);
  const facultyId = Number(authState.user.faculty_id || 0);
  const classDate = String(els.remedialDate?.value || '').trim();
  const startTime = String(els.remedialStartTime?.value || '').trim();
  const endTime = String(els.remedialEndTime?.value || '').trim();
  const topic = String(els.remedialTopic?.value || '').trim();
  if (!courseId || !facultyId || !classDate || !startTime || !endTime || !topic) {
    throw new Error('Select course/date/time and enter topic to create remedial class.');
  }

  const payload = await api('/makeup/classes', {
    method: 'POST',
    body: JSON.stringify({
      course_id: courseId,
      faculty_id: facultyId,
      class_date: classDate,
      start_time: startTime,
      end_time: endTime,
      topic,
    }),
  });
  setRemedialFacultyStatus(`Remedial class scheduled. Generated code: ${payload.remedial_code}`);
  log(`Remedial class created (${payload.remedial_code})`);
  if (els.remedialTopic) {
    els.remedialTopic.value = '';
  }
  await refreshRemedialModule();
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
  const payload = await api('/makeup/attendance/mark', {
    method: 'POST',
    body: JSON.stringify({
      remedial_code: remedialCode,
      student_id: studentId,
    }),
  });
  setRemedialStudentStatus(String(payload?.message || 'Remedial attendance marked.'));
  log(`Remedial attendance marked using code ${remedialCode}`);
}

async function refreshActiveModuleData() {
  if (!authState.user) {
    return;
  }
  const moduleKey = getSanitizedModuleKey(state.ui.activeModule);
  if (moduleKey === 'food') {
    await refreshFoodModule();
    return;
  }
  if (moduleKey === 'administrative') {
    await refreshAdministrativeModule();
    return;
  }
  if (moduleKey === 'remedial') {
    await refreshRemedialModule();
    return;
  }
  if (authState.user.role === 'student') {
    await refreshStudentKpiTimetable({ forceNetwork: true });
    await loadStudentTimetable({ forceNetwork: true });
    await loadStudentAttendanceInsights();
  }
  if (authState.user.role === 'faculty') {
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

  const windowEnd = new Date(classStart.getTime() + (10 * 60 * 1000));

  if (now < classStart) {
    return { key: 'upcoming', label: 'Upcoming' };
  }

  if (markedPresent) {
    return { key: 'present', label: 'Present' };
  }

  if (now <= windowEnd) {
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

  const timeline = source
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
        windowEnd: new Date(start.getTime() + (10 * 60 * 1000)),
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.start.getTime() - b.start.getTime());

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
    return {
      mode: 'mark',
      schedule: selected,
      headline: `Mark Attendance | ${selected.course_code}`,
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

function renderStudentProfilePreview(photoDataUrl) {
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

function updateProfileSaveState() {
  if (!els.saveProfilePhotoBtn) {
    return;
  }
  if (authState.user?.role !== 'student') {
    els.saveProfilePhotoBtn.disabled = true;
    return;
  }

  const draftRegistration = (els.profileRegistrationNumber?.value || '').trim().toUpperCase().replace(/\s+/g, '');
  const hasRegistration = Boolean(state.student.registrationNumber || draftRegistration);
  const hasPhoto = Boolean(state.student.profilePhotoDataUrl || state.student.pendingProfilePhotoDataUrl);
  const hasNewReg = Boolean(draftRegistration) && draftRegistration !== (state.student.registrationNumber || '');
  const hasNewPhoto = Boolean(state.student.pendingProfilePhotoDataUrl)
    && state.student.pendingProfilePhotoDataUrl !== (state.student.profilePhotoDataUrl || '');
  const setupRequired = state.student.profileSetupRequired || requiresStudentProfileSetup();

  if (setupRequired) {
    els.saveProfilePhotoBtn.disabled = !(hasRegistration && hasPhoto);
    return;
  }

  els.saveProfilePhotoBtn.disabled = !(hasNewReg || hasNewPhoto);
}

function renderStudentProfileStatus() {
  if (!els.profileStatus) {
    return;
  }

  const draftRegistration = (els.profileRegistrationNumber?.value || '').trim().toUpperCase().replace(/\s+/g, '');
  const hasRegistration = Boolean(state.student.registrationNumber || draftRegistration);
  const hasPhoto = Boolean(state.student.profilePhotoDataUrl || state.student.pendingProfilePhotoDataUrl);

  if (!hasRegistration && !hasPhoto) {
    els.profileStatus.textContent = 'Registration number and profile photo are required before continuing.';
    updateProfileSaveState();
    return;
  }
  if (!hasRegistration) {
    els.profileStatus.textContent = 'Registration number is required and becomes permanent after save.';
    updateProfileSaveState();
    return;
  }
  if (!hasPhoto) {
    els.profileStatus.textContent = 'Profile photo is mandatory. Upload once to enable facial attendance.';
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

function resolveFoodPaymentError(error, fallback = 'Payment checkout failed. Please retry.') {
  const raw = String(error?.message || '').trim();
  if (!raw) {
    return fallback;
  }
  const lowered = raw.toLowerCase();
  if (lowered.includes('razorpay configuration is missing') || lowered.includes('razorpay is not configured')) {
    return 'Payments are not configured on server. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in backend .env, then restart server.';
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
  state.student.registrationNumber = data.registration_number || '';
  state.student.profilePhotoDataUrl = data.photo_data_url || '';
  state.student.profilePhotoCanUpdateNow = Boolean(data.can_update_photo_now);
  state.student.profilePhotoLockedUntil = data.photo_locked_until || null;
  state.student.profilePhotoLockDaysRemaining = Number(data.photo_lock_days_remaining || 0);
  state.student.profileLoaded = true;
  state.student.pendingProfilePhotoDataUrl = '';

  renderStudentProfilePreview(state.student.profilePhotoDataUrl);
  renderStudentProfileStatus();
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

async function saveStudentProfilePhoto() {
  const registrationNumber = (els.profileRegistrationNumber?.value || '').trim().toUpperCase().replace(/\s+/g, '');
  const existingRegistration = state.student.registrationNumber || '';
  const hasNewReg = Boolean(registrationNumber) && registrationNumber !== existingRegistration;
  const nextPhotoDataUrl = state.student.pendingProfilePhotoDataUrl || '';
  const hasNewPhoto = Boolean(nextPhotoDataUrl) && nextPhotoDataUrl !== state.student.profilePhotoDataUrl;
  const setupRequired = state.student.profileSetupRequired || requiresStudentProfileSetup();
  const hasRegistrationAfterSave = Boolean(existingRegistration || registrationNumber);
  const hasPhotoAfterSave = Boolean(state.student.profilePhotoDataUrl || nextPhotoDataUrl);

  if (setupRequired) {
    if (!hasRegistrationAfterSave) {
      throw new Error('Enter your registration number before saving profile.');
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

  const payload = {};
  if (hasNewReg || (!existingRegistration && registrationNumber)) {
    payload.registration_number = registrationNumber;
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
      throw new Error('Add registration number and profile photo before continuing.');
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
  state.student.profilePhotoDataUrl = saved.photo_data_url || '';
  state.student.profilePhotoCanUpdateNow = Boolean(saved.can_update_photo_now);
  state.student.profilePhotoLockedUntil = saved.photo_locked_until || null;
  state.student.profilePhotoLockDaysRemaining = Number(saved.photo_lock_days_remaining || 0);
  state.student.pendingProfilePhotoDataUrl = '';
  if (els.profilePhotoInput) {
    els.profilePhotoInput.value = '';
  }
  renderStudentProfilePreview(state.student.profilePhotoDataUrl);
  renderStudentProfileStatus();
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
  const hasProfileReady = Boolean(state.student.profilePhotoDataUrl) && Boolean(state.student.registrationNumber);
  const kpi = findAttendanceManagementState();
  const scheduleId = Number(kpi.schedule?.schedule_id || 0);
  state.student.kpiScheduleId = scheduleId || null;

  if (els.selectedClassLabel) {
    els.selectedClassLabel.textContent = kpi.headline;
  }
  if (els.attendanceKpiSubtitle) {
    if (!hasProfileReady) {
      els.attendanceKpiSubtitle.textContent = `${kpi.subtitle} Complete profile setup to enable official marking.`;
    } else {
      els.attendanceKpiSubtitle.textContent = kpi.subtitle;
    }
  }

  els.takeSelfieBtn.disabled = !(kpi.mode === 'mark' && scheduleId && hasProfileReady);
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
  const minWeekStartRaw = weekStartISO(String(state.student.minTimetableDate || '2026-01-21'));
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
    const payload = await api(`/attendance/student/timetable?week_start=${weekStart}`);
    cacheTimetableWeekPayload(weekStart, payload);
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
  const minWeekStart = weekStartISO(state.student.minTimetableDate || '2026-01-21');
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
    const payload = await api(`/attendance/student/timetable?week_start=${currentWeekStart}`);
    cacheTimetableWeekPayload(payload.week_start || currentWeekStart, payload);
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
    payload = await api(`/attendance/student/timetable?week_start=${weekStart}`);
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
      const repairedPayload = await api(`/attendance/student/timetable?week_start=${weekStart}`);
      if (requestToken !== state.student.timetableRequestToken) {
        return;
      }
      cacheTimetableWeekPayload(repairedPayload.week_start || weekStart, repairedPayload);
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

  cacheTimetableWeekPayload(payload.week_start || weekStart, payload);
  applyStudentTimetablePayload(payload);
  prefetchAdjacentStudentWeeks(state.student.weekStart || weekStart);
  if (weekStart !== currentWeekStart) {
    void refreshStudentKpiTimetable({ forceNetwork: true }).then(() => {
      updateSelectedClassState();
    });
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

function attendanceCourseKey(courseCode, courseTitle) {
  return `${String(courseCode || '').trim().toUpperCase()}::${String(courseTitle || '').trim().toUpperCase()}`;
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

function closeAttendanceDetailsModal() {
  state.student.attendanceDetailsCourseKey = '';
  if (els.attendanceDetailsModal) {
    els.attendanceDetailsModal.classList.add('hidden');
  }
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
    const rowsMarkup = records
      .map((row) => {
        const statusRaw = String(row.status || '').toLowerCase();
        const isPresent = statusRaw === 'present';
        const statusClass = isPresent ? 'present' : 'absent';
        const statusLabelText = isPresent ? 'Present' : 'Absent';
        const classDate = parseISODateLocal(row.class_date).toLocaleDateString('en-GB');
        const timeRange = `${formatTime24(row.start_time)}-${formatTime24(row.end_time)}`;
        return `
          <article class="attendance-detail-row ${statusClass}">
            <div class="attendance-detail-main">
              <strong>${escapeHtml(classDate)}</strong>
              <small>${escapeHtml(timeRange)}</small>
            </div>
            <span class="attendance-detail-status ${statusClass}">${statusLabelText}</span>
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

  const [aggregate, history] = await Promise.all([
    api('/attendance/student/attendance-aggregate'),
    api('/attendance/student/attendance-history?limit=80'),
  ]);

  state.student.attendanceAggregate = aggregate;
  state.student.attendanceHistory = history.records || [];
  state.student.attendanceHistoryByCourse = indexAttendanceHistoryByCourse(state.student.attendanceHistory);
  renderStudentAttendanceAggregate();
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

async function buildAttendanceVerificationPayload(selectedScheduleId, selfieDataUrl, selfieFrames = []) {
  const payload = {
    schedule_id: selectedScheduleId,
    selfie_photo_data_url: selfieDataUrl,
  };
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

async function submitStudentAttendanceAttempt(selectedScheduleId, selfieDataUrl, selfieFrames = []) {
  const payload = await buildAttendanceVerificationPayload(selectedScheduleId, selfieDataUrl, selfieFrames);
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

async function startLiveAttendanceVerification() {
  const kpi = findAttendanceManagementState();
  const selectedScheduleId = Number(kpi.schedule?.schedule_id || 0);
  if (kpi.mode !== 'mark' || !selectedScheduleId) {
    throw new Error('Attendance window is closed right now. Wait for the next class.');
  }
  state.student.kpiScheduleId = selectedScheduleId;
  state.student.selectedScheduleId = selectedScheduleId;
  if (!state.student.profilePhotoDataUrl) {
    throw new Error('Upload profile photo before marking attendance.');
  }
  if (state.camera.liveVerificationActive) {
    throw new Error('Live verification is already running.');
  }

  setStudentResult('Live attendance verification started...');

  await openCameraModal({
    title: 'Live Realtime Attendance Verification',
    facingMode: 'user',
    referencePhotoDataUrl: state.student.profilePhotoDataUrl,
    burstFrames: LIVE_VERIFICATION_BURST_FRAMES,
    captureEnabled: false,
    messageOverride: 'OpenCV live verification running. Keep one face centered, look straight, then move head slightly left/right/up/down.',
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
      const timeoutMsg = 'Verification took too long. Use bright front light, keep one centered face, then retry.';
      setStudentResult(timeoutMsg, {
        showRetry: true,
        retryAction: () => startStudentSelfieFlow(),
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

      const response = await submitStudentAttendanceAttempt(selectedScheduleId, selfieDataUrl, selfieFrames);
      const status = String(response.status || '').toLowerCase();
      const confidencePct = (Number(response.verification_confidence || 0) * 100).toFixed(1);
      const verified = ['verified', 'approved', 'present'].includes(status);

      if (verified) {
        const lines = [
          `Status: ${statusLabel(response.status)}`,
          `Message: ${response.message}`,
        ];
        setStudentResult(lines.join('\n'));
        if (els.cameraMessage) {
          els.cameraMessage.textContent = 'Attendance verified. Closing camera...';
        }
        log(`Attendance marked with confidence: ${confidencePct}%`);
        await loadStudentTimetable({ forceNetwork: true });
        await loadStudentAttendanceInsights();
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
        const livenessTimeoutMessage = 'Liveness check still failing. Keep front light on face, center your face, and move head slowly left/right/up/down, then retry.';
        setStudentResult(livenessTimeoutMessage, {
          showRetry: true,
          retryAction: () => startStudentSelfieFlow(),
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
  if (!authState.user || authState.user.role !== 'faculty') {
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
  if (!authState.user || authState.user.role !== 'faculty') {
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

  const data = await api(`/attendance/faculty/dashboard?schedule_id=${scheduleId}&class_date=${classDate}`);
  state.faculty.dashboard = data;

  const validPendingIds = new Set(
    (data.submissions || [])
      .filter((item) => item.status === 'pending_review')
      .map((item) => item.id)
  );
  state.faculty.selectedSubmissionIds = new Set(
    [...state.faculty.selectedSubmissionIds].filter((id) => validPendingIds.has(id))
  );

  renderFacultyDashboard(data);
  syncReviewSelectionUI();
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
  if (!authState.user || authState.user.role !== 'faculty') {
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
    const width = Math.max(640, els.enrollmentVideo.videoWidth || 1280);
    const height = Math.max(360, els.enrollmentVideo.videoHeight || 720);
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
        state.student.enrollmentFrames.push(els.enrollmentCanvas.toDataURL('image/jpeg', 0.9));
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
    'Validating account and delivering OTP to your email...',
    { tone: 'sending', loading: true, closable: false }
  );
  try {
    const data = await api('/auth/password/request-otp', {
      method: 'POST',
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
    'Generating secure OTP and delivering it to your email...',
    { tone: 'sending', loading: true, closable: false }
  );
  setAuthMessage('Sending OTP... please wait.');
  try {
    const data = await api('/auth/login/request-otp', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        send_to_alternate: Boolean(els.authSendAltOtp?.checked),
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

    els.otpDebug.classList.add('hidden');
    els.otpDebug.textContent = '';
    if (data.otp_debug_code) {
      els.otpDebug.classList.remove('hidden');
      els.otpDebug.textContent = `Demo OTP: ${data.otp_debug_code}`;
    }

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
  const name = els.authName.value.trim();
  const department = els.authDepartment.value.trim();
  const semesterValue = els.authSemester.value.trim();
  const parentEmail = els.authParentEmail.value.trim();

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
    if (!semesterValue) {
      throw new Error('Semester is required for student registration.');
    }
  }

  const payload = {
    email,
    password,
    role,
    name,
    department,
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
  els.otpDebug.classList.add('hidden');
  els.otpDebug.textContent = '';
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

  if (!email || !otpCode) {
    throw new Error('Email and OTP code are required.');
  }

  setOtpVerifyInFlight(true);
  let data;
  try {
    data = await api('/auth/login/verify-otp', {
      method: 'POST',
      body: JSON.stringify({ email, otp_code: otpCode }),
      skipAuth: true,
    });
  } finally {
    setOtpVerifyInFlight(false);
  }

  setSession(data.access_token, data.user);
  setForgotPasswordPanel(false);
  resetForgotPasswordState({ clearFields: true });
  setAuthMessage('Login successful.');
  els.otpDebug.classList.add('hidden');
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
    if (authState.user?.role === 'student') {
      state.student.viewDate = todayISO();
      if (els.weekStartDate) {
        els.weekStartDate.value = state.student.viewDate;
      }
      startStudentRealtimeTicker();
      try {
        await ensureCurrentWeekTimetableVisible({ forceNetwork: true });
      } catch (error) {
        log(error.message || 'Failed to auto-load current week timetable');
      }
    } else {
      stopStudentRealtimeTicker();
    }
    startModuleRealtimeTicker();
    startSessionWatchdog();
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
  try {
    await api('/auth/logout', { method: 'POST', skipAuth: true });
  } catch (_error) {
    // Ignore logout API failures and always clear client session state.
  }
  clearSession();
  openAuthOverlay(message);
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
      () => refreshStudentKpiTimetable({ forceNetwork: true }),
      () => loadStudentTimetable({ forceNetwork: true }),
      () => loadStudentAttendanceInsights(),
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
    tasks.push(refreshOverview());
    tasks.push(refreshAttendanceData());
    tasks.push(refreshDemand());
    tasks.push(refreshCapacity());

    if (role === 'faculty') {
      tasks.push(loadFacultySchedules());
    }
    if (role === 'faculty' || role === 'admin') {
      tasks.push(
        api('/resources/workload-distribution').then((rows) => {
          state.resources.workload = Array.isArray(rows) ? rows : [];
          renderWorkloadChart();
        })
      );
      tasks.push(
        api('/resources/mongo/status').then((payload) => {
          state.resources.mongoStatus = payload || null;
          renderMongoStatus();
        })
      );
    } else {
      state.resources.workload = [];
      state.resources.mongoStatus = null;
      renderWorkloadChart();
      renderMongoStatus();
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
    els.topNavFoodBtn,
    els.topNavAdministrativeBtn,
    els.topNavRemedialBtn,
  ].filter(Boolean);
  for (const button of topModuleButtons) {
    button.addEventListener('click', async () => {
      if (!authState.user) {
        openAuthOverlay('Sign in to access modules.');
        return;
      }
      if (authState.user.role === 'student' && requiresStudentProfileSetup()) {
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
    if (authState.user.role === 'student' && requiresStudentProfileSetup()) {
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
      openProfileModal({ required: requiresStudentProfileSetup() });
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
        const minDate = state.student.minTimetableDate || '2026-01-21';
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

  if (els.remedialMarkBtn) {
    els.remedialMarkBtn.addEventListener('click', async () => {
      try {
        await markRemedialAttendance();
      } catch (error) {
        setRemedialStudentStatus(error.message, true);
        log(error.message);
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
        await startStudentSelfieFlow();
      } catch (error) {
        log(error.message);
        setStudentResult(error.message);
      }
    }
  });

  els.takeSelfieBtn.addEventListener('click', async () => {
    try {
      await startStudentSelfieFlow();
    } catch (error) {
      log(error.message);
      setStudentResult(error.message);
    }
  });

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

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') {
      return;
    }
    if (isForgotPasswordPanelOpen()) {
      setForgotPasswordPanel(false);
      return;
    }
    if (!els.attendanceDetailsModal || els.attendanceDetailsModal.classList.contains('hidden')) {
      return;
    }
    closeAttendanceDetailsModal();
  });

  els.profilePhotoInput.addEventListener('change', async () => {
    const file = els.profilePhotoInput.files?.[0];
    if (!file) {
      state.student.pendingProfilePhotoDataUrl = '';
      renderStudentProfileStatus();
      renderEnrollmentSummary();
      return;
    }

    if (state.student.profilePhotoDataUrl && !state.student.profilePhotoCanUpdateNow) {
      state.student.pendingProfilePhotoDataUrl = '';
      els.profilePhotoInput.value = '';
      showProfilePhotoLockPopup();
      renderStudentProfileStatus();
      renderEnrollmentSummary();
      return;
    }

    try {
      const dataUrl = await fileToDataUrl(file);
      state.student.pendingProfilePhotoDataUrl = dataUrl;
      renderStudentProfilePreview(dataUrl);
      renderEnrollmentSummary();
      renderStudentProfileStatus();
      if (els.profileStatus) {
        els.profileStatus.textContent = 'Photo selected. Click Save Profile to complete setup.';
      }
    } catch (error) {
      log(error.message);
    }
  });

  els.saveProfilePhotoBtn.addEventListener('click', async () => {
    try {
      await saveStudentProfilePhoto();
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
      renderStudentProfileStatus();
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
  startLiveDateTimeTicker();
  setAuthMode('login');
  if (ENABLE_DECORATIVE_MOTION) {
    initParallax();
    initTiltCards();
  }
  initMicroInteractions();
  bindSessionActivityWatchdog();
  bindEvents();
  syncFoodOrderActionState();
  renderWorkloadChart();
  renderMongoStatus();
  renderPasswordStrengthHint(els.authPasswordStrength, els.authPassword?.value || '');
  renderPasswordStrengthHint(els.authSignupPasswordStrength, els.authSignupPassword?.value || '');
  renderPasswordStrengthHint(els.forgotPasswordStrength, els.forgotNewPassword?.value || '');
  renderOtpCooldown();
  renderForgotOtpCooldown();
  setRegisterInFlight(false);
  setForgotPasswordPanel(false);
  updateAuthBadges();
  applyRoleUI();
  setTopNavActive(state.ui.activeModule);
  renderProfileSecurity();

  const restored = await restoreSession();
  if (restored) {
    try {
      await refreshAll();
    } catch (error) {
      log(error.message);
    }
  }
}

init();
