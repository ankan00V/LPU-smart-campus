const EXPLAIN_HINT_RE = /\b(explain|detailed|detail|elaborate|full|why|how|step|walkthrough|in depth)\b/i;

const HELP_TOPICS = [
  {
    title: 'Attendance Module',
    keywords: ['attendance', 'mark', 'camera', 'selfie', 'timetable', 'ledger', 'present', 'absent'],
    concise: [
      'Open Attendance module and check your current class from Weekly Timetable.',
      'Students can mark attendance only in the live opening window for that class.',
      'Faculty can review pending submissions and approve/reject in the Faculty section.',
      'Use Attendance Ledger for subject-wise percentage and class history.',
    ],
    detailed: [
      'Students: go to Attendance -> verify active class -> click "Open Camera & Mark Attendance" in the allowed window.',
      'If camera is blocked, enable browser camera permission and retry once the class is still open.',
      'Faculty: pick schedule + class date -> refresh queue -> batch review pending AI rows.',
      'Attendance percentages update in ledger cards; click a subject card to see date-wise records.',
      'If class tiles look stale, use Refresh controls or module switch to force data reload.',
      'Only valid enrolled schedule slots are considered for attendance totals.',
    ],
  },
  {
    title: 'Remedial Workflow',
    keywords: ['remedial', 'makeup', 'make-up', 'code', 'section', 'rejected', 'scheduled'],
    concise: [
      'Faculty schedules remedial class, generates code, then sends it to target sections.',
      'Students validate the remedial code, then mark attendance during the live window.',
      'Completed remedial classes move out of active list and remain in remedial attendance records.',
      'Reject class is time-limited for faculty and follows module policy.',
    ],
    detailed: [
      'Faculty: fill course/section/date/time/mode -> click "Schedule + Generate Code" to create a session.',
      'Use "Send Code to Section(s)" so students receive the valid code for that specific class.',
      'Students: open Remedial tab -> enter code exactly -> validate -> then mark attendance in live window.',
      'Active class cards are shown only for ongoing/upcoming eligible classes; ended classes shift to history/ledger.',
      'Remedial attendance is tracked separately from normal timetable attendance as configured.',
      'If a code fails, verify class time, section, and whether the class is still active.',
    ],
  },
  {
    title: 'Food Hall',
    keywords: ['food', 'canteen', 'order', 'cart', 'shop', 'slot', 'delivery', 'location', 'payment'],
    concise: [
      'Pick date + break slot, then select one shop and add items to cart.',
      'Location access is required for delivery flow and campus restriction checks.',
      'Use Open Cart to review items, fees, and checkout.',
      'Order tracking appears in current/previous tabs with payment recovery support.',
    ],
    detailed: [
      'Select a valid break slot first; unavailable slots block ordering for that time.',
      'Enable location access to pass campus delivery checks before checkout.',
      'Cart supports one-shop-at-a-time ordering to keep fulfillment consistent.',
      'Review tab shows subtotal, platform fee, and delivery fee before payment.',
      'Live order states move from placed -> preparing -> ready/out-for-delivery -> delivered/collected.',
      'If data partially fails, module now falls back and still renders available sections.',
    ],
  },
  {
    title: 'Messages & Help',
    keywords: ['message', 'query', 'support', 'faculty', 'student', 'discrepancy', 'realtime', 'real time'],
    concise: [
      'Message Desk in Attendance module supports realtime student-faculty issue communication.',
      'Use categories like Attendance, Academics, Discrepancy, or Other for cleaner tracking.',
      'Unread counts update automatically; open a thread to sync latest replies.',
      'Verlyn provides quick usage help for all modules irrespective of role.',
    ],
    detailed: [
      'Open Message Desk and pick recipient + category before sending your query.',
      'Thread updates stream in realtime so replies appear without manual refresh.',
      'Conversation scope is role-aware (student-faculty context checks are enforced).',
      'Support threads mark unread replies and clear them when thread is opened.',
      'Use concise prompts for quick answers; ask Verlyn with "explain" for detailed steps.',
      'For section-wide announcements, faculty should use Faculty Messages inside Remedial.',
    ],
  },
  {
    title: 'Profile & Access',
    keywords: ['profile', 'photo', 'registration', 'login', 'otp', 'password', 'account', 'security'],
    concise: [
      'Use top-right avatar menu to open profile and update allowed fields.',
      'OTP-based login is required for secure access flows.',
      'Registration/section/profile updates follow lock rules shown in profile notes.',
      'If login fails, verify email format, OTP validity, and password policy.',
    ],
    detailed: [
      'Login flow: credentials -> request OTP -> verify OTP to complete secure session.',
      'Profile panel shows what can be edited now vs locked until a given time.',
      'Photo updates and section edits may be rate-limited by policy for consistency.',
      'Forgot password flow requires registered email + registration number + reset OTP.',
      'Use hard refresh after role/profile changes so all module permissions resync.',
      'If session expires, re-authenticate and reopen the required module.',
    ],
  },
  {
    title: 'Troubleshooting',
    keywords: ['not working', 'error', 'bug', 'issue', 'fail', 'timeout', 'loading', 'stuck', 'blank'],
    concise: [
      'Run a hard refresh first to reload latest JS/CSS assets.',
      'Check required permissions (camera/location) for attendance or food actions.',
      'Use module Refresh controls to pull latest server state.',
      'If issue persists, capture exact action + timestamp and share with faculty/support.',
    ],
    detailed: [
      'Hard refresh the page (Cmd+Shift+R) to clear stale cached frontend bundles.',
      'Check browser permissions: camera for attendance, location for delivery/order validation.',
      'Confirm server is running without startup errors and Mongo/DB connectivity is healthy.',
      'Reproduce once with exact steps and note module, role, and class/time context.',
      'If a specific API action fails, retry once after 5-10 seconds to bypass transient timeouts.',
      'Escalate with screenshot + command log entries for fastest backend diagnosis.',
    ],
  },
];

function resolveTopic(queryText = '') {
  const input = String(queryText || '').trim().toLowerCase();
  if (!input) {
    return HELP_TOPICS[0];
  }
  let bestTopic = HELP_TOPICS[0];
  let bestScore = 0;
  for (const topic of HELP_TOPICS) {
    let score = 0;
    for (const token of topic.keywords) {
      if (input.includes(token)) {
        score += 1;
      }
    }
    if (score > bestScore) {
      bestTopic = topic;
      bestScore = score;
    }
  }
  if (bestScore === 0) {
    const fallback = HELP_TOPICS.find((topic) => topic.title === 'Troubleshooting');
    return fallback || bestTopic;
  }
  return bestTopic;
}

export function buildReply({ queryText = '', roleLabel = 'Guest' } = {}) {
  const trimmed = String(queryText || '').trim();
  if (!trimmed) {
    return [
      'Quick Help',
      '1. Ask your question in one line.',
      '2. Include module name (Attendance, Food Hall, Remedial, Administrative) for better answer.',
      '3. Add "explain" if you need detailed step-by-step guidance.',
    ].join('\n');
  }

  const detailed = EXPLAIN_HINT_RE.test(trimmed);
  const topic = resolveTopic(trimmed);
  const points = (detailed ? topic.detailed : topic.concise)
    .map((line) => String(line || '').replaceAll('{role}', roleLabel))
    .filter(Boolean);
  const numbered = points.map((line, index) => `${index + 1}. ${line}`);
  const footer = detailed
    ? 'Need examples for your exact screen? Ask with your module + role + issue.'
    : 'Tip: ask with "explain" for detailed steps.';

  return [`${topic.title} (${detailed ? 'Detailed' : 'Quick'})`, ...numbered, '', footer].join('\n');
}
