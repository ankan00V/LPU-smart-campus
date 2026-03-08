import { test, expect } from '@playwright/test';

const APP_ORIGIN = new URL(process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:8001/web').origin;

const STUDENT_USER = {
  id: 11,
  email: 'student@example.com',
  name: 'Aarav Student',
  role: 'student',
  registration_number: '22BCS101',
  section: 'P132',
};

const FACULTY_USER = {
  id: 21,
  email: 'faculty@example.com',
  name: 'Dr Faculty',
  role: 'faculty',
  faculty_id: 501,
  faculty_identifier: 'FAC501',
  section: 'P132',
};

const ADMIN_USER = {
  id: 31,
  email: 'admin@example.com',
  name: 'Admin Ops',
  role: 'admin',
};

function json(route, payload, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(payload),
  });
}

function parseJson(request) {
  const raw = request.postData() || '';
  return raw ? JSON.parse(raw) : {};
}

function isStaticRequest(pathname) {
  return pathname === '/'
    || pathname.startsWith('/web/')
    || pathname.startsWith('/assets/')
    || pathname === '/favicon.ico'
    || pathname === '/apple-touch-icon.png';
}

function buildAdminLivePayload() {
  return {
    summary: {
      blocks: 12,
      classrooms: 180,
      courses: 640,
      faculty: 280,
      students: 32000,
      active_today: 220,
      present_today: 201,
      absent_today: 19,
      attendance_rate_today: 91,
      capacity_utilization_percent: 68,
      workload_distribution_percent: 74,
      data_quality_score: 98,
      last_updated_at: '2026-03-08T09:00:00Z',
      stale_after_seconds: 60,
      mongo_status: {
        connected: true,
        database: 'campus',
      },
    },
    alerts: [],
    capacity: [],
    workload: [],
  };
}

function buildAdminInsightsPayload() {
  return {
    highlights: ['Audit governance baseline is healthy.'],
    campus_profile: {
      active_students: {
        estimated: 32000,
        min: 31500,
        max: 32500,
      },
      discipline_distribution: [],
      year_distribution: [],
      residency_split: [],
      origin_split: [],
      classroom_utilization_model: {
        time_slots: [],
      },
      placement_model: {
        overall: {
          placement_rate_percent: 89,
        },
      },
      mobility_model: {
        daily_shuttle_riders: 0,
      },
      library_model: {
        daily_usage_range: '--',
        peak_late_night_occupancy: 0,
        exam_surge_midsem_percent: 0,
        exam_surge_endterm_percent: 0,
      },
    },
  };
}

function filterAuditRows(rows, searchParams) {
  const limit = Number(searchParams.get('limit') || 50) || 50;
  const q = String(searchParams.get('q') || '').trim().toLowerCase();
  const intent = String(searchParams.get('intent') || '').trim().toLowerCase();
  const outcome = String(searchParams.get('outcome') || '').trim().toLowerCase();
  const actorRole = String(searchParams.get('actor_role') || '').trim().toLowerCase();
  const actorUserId = String(searchParams.get('actor_user_id') || '').trim();

  return rows
    .filter((row) => {
      if (q) {
        const haystack = [
          row.id,
          row.query_text,
          row.actor_email,
          row.actor_role,
          row.scope,
          row.target_section,
          row.target_student_id,
          row.target_course_id,
        ]
          .join(' ')
          .toLowerCase();
        if (!haystack.includes(q)) {
          return false;
        }
      }
      if (intent && String(row.intent || '').trim().toLowerCase() !== intent) {
        return false;
      }
      if (outcome && String(row.outcome || '').trim().toLowerCase() !== outcome) {
        return false;
      }
      if (actorRole && String(row.actor_role || '').trim().toLowerCase() !== actorRole) {
        return false;
      }
      if (actorUserId && String(row.actor_user_id || '') !== actorUserId) {
        return false;
      }
      return true;
    })
    .slice(0, limit);
}

async function installBrowserGuards(page) {
  await page.addInitScript(() => {
    class MockEventSource {
      constructor() {
        this.readyState = 1;
        window.setTimeout(() => {
          if (typeof this.onopen === 'function') {
            this.onopen({ type: 'open' });
          }
        }, 0);
      }

      close() {
        this.readyState = 2;
      }

      addEventListener() {}

      removeEventListener() {}
    }

    window.EventSource = MockEventSource;
    window.confirm = () => true;
  });
}

async function installApiRouter(page, handler) {
  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (url.origin !== APP_ORIGIN || isStaticRequest(url.pathname)) {
      await route.continue();
      return;
    }

    const handled = await handler(route, request, url);
    if (handled) {
      return;
    }

    await json(
      route,
      {
        detail: `Unhandled API request: ${request.method()} ${url.pathname}${url.search}`,
      },
      500,
    );
  });
}

async function bootstrapSession(page, user) {
  await page.goto('/web/');
  await page.waitForFunction(() => typeof window.setSession === 'function');
  await page.evaluate((sessionUser) => {
    window.setSession('test-token', sessionUser);
    window.stopRealtimeEventBus?.();
    window.stopStudentRealtimeTicker?.();
    window.stopStudentTimetableStatusTicker?.();
    window.stopModuleRealtimeTicker?.();
    window.stopRemedialLiveTicker?.();
  }, user);
  await expect(page.locator('#auth-overlay')).toBeHidden();
}

async function openCopilot(page) {
  await page.locator('#verlyn-toggle-btn').click();
  await expect(page.locator('#verlyn-panel')).toBeVisible();
}

async function setInputValue(locator, value) {
  await locator.evaluate((element, nextValue) => {
    element.value = nextValue;
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
  }, value);
}

test.beforeEach(async ({ page }) => {
  await installBrowserGuards(page);
});

test('student attendance copilot quick chips execute audited checks', async ({ page }) => {
  const copilotRequests = [];

  await installApiRouter(page, async (route, request, url) => {
    if (url.pathname === '/copilot/query' && request.method() === 'POST') {
      const payload = parseJson(request);
      copilotRequests.push(payload);

      if (payload.query_text === "Why can't I mark attendance?") {
        await json(route, {
          intent: 'attendance_blocker',
          title: 'Attendance Marker Blocked',
          outcome: 'blocked',
          explanation: [
            'Campus location verification is missing for the active attendance window.',
            'Selfie verification must complete before attendance can be accepted.',
          ],
          evidence: [
            {
              status: 'blocked',
              label: 'Geo verification',
              value: 'Campus perimeter check is still pending.',
            },
            {
              status: 'blocked',
              label: 'Face verification',
              value: 'Live selfie has not been submitted for this session.',
            },
          ],
          actions: [
            {
              action: 'retry_attendance',
              status: 'preview',
              detail: 'Enable location, complete selfie verification, then retry.',
            },
          ],
          next_steps: ['Retry attendance before the class window closes.'],
          audit_id: 401,
        });
        return true;
      }

      if (payload.query_text === 'What do I need to fix before I lose eligibility?') {
        await json(route, {
          intent: 'eligibility_risk',
          title: 'Eligibility Recovery Plan',
          outcome: 'completed',
          explanation: [
            'Your current aggregate is 74.0%, below the 75.0% threshold.',
            'Attending the next two delivered classes moves the aggregate back above the threshold.',
          ],
          evidence: [
            {
              status: 'warn',
              label: 'Current attendance',
              value: '74.0% aggregate across enrolled courses.',
            },
            {
              status: 'info',
              label: 'Recovery window',
              value: '2 consecutive present marks restore eligibility.',
            },
          ],
          actions: [
            {
              action: 'monitor_eligibility',
              status: 'completed',
              detail: 'Recovery target logged against your attendance ledger.',
            },
          ],
          next_steps: ['Attend the next two scheduled classes without absence.'],
          audit_id: 402,
        });
        return true;
      }
    }

    return false;
  });

  await bootstrapSession(page, STUDENT_USER);
  await openCopilot(page);

  await expect(page.locator('[data-verlyn-action="attendance_blocker"]')).toBeVisible();
  await expect(page.locator('[data-verlyn-action="eligibility_risk"]')).toBeVisible();

  await page.locator('[data-verlyn-action="attendance_blocker"]').click();
  await expect(page.locator('#verlyn-output')).toContainText('Attendance Marker Blocked');
  await expect(page.locator('#verlyn-output')).toContainText('Audit Log: #401');

  await page.locator('[data-verlyn-action="eligibility_risk"]').click();
  await expect(page.locator('#verlyn-output')).toContainText('Eligibility Recovery Plan');
  await expect(page.locator('#verlyn-output')).toContainText('Audit Log: #402');

  expect(copilotRequests.map((request) => request.query_text)).toEqual([
    "Why can't I mark attendance?",
    'What do I need to fix before I lose eligibility?',
  ]);
});

test('faculty RMS registration context stays connected to copilot flag review', async ({ page }) => {
  const copilotRequests = [];

  await installApiRouter(page, async (route, request, url) => {
    if (url.pathname === '/admin/rms/queries' && request.method() === 'GET') {
      await json(route, {
        total_threads: 0,
        total_pending: 0,
        categories: [],
      });
      return true;
    }

    if (url.pathname === '/admin/rms/students/search' && request.method() === 'GET') {
      await json(route, {
        student_id: 77,
        name: 'Riya Sharma',
        email: 'riya.sharma@example.com',
        registration_number: '22BCS777',
        section: 'P132',
        pending_query_count: 2,
        recent_query_count: 4,
        last_query_at: '2026-03-08T08:30:00Z',
      });
      return true;
    }

    if (url.pathname === '/copilot/query' && request.method() === 'POST') {
      const payload = parseJson(request);
      copilotRequests.push(payload);
      await json(route, {
        intent: 'student_flag_reason',
        title: 'Flag Review for 22BCS777',
        outcome: 'completed',
        explanation: [
          'The student has two unresolved RMS queries and one attendance mismatch.',
          'Attendance recovery is still possible, so remedial action is recommended instead of escalation.',
        ],
        evidence: [
          {
            status: 'warn',
            label: 'RMS pending',
            value: '2 active student service threads remain unresolved.',
          },
          {
            status: 'warn',
            label: 'Attendance mismatch',
            value: 'One subject is marked absent against an open rectification path.',
          },
        ],
        actions: [
          {
            action: 'recommend_remedial',
            status: 'completed',
            detail: 'Flag rationale recorded for faculty follow-up.',
          },
        ],
        next_steps: ['Review the RMS queue before closing the attendance discrepancy.'],
        audit_id: 501,
      });
      return true;
    }

    return false;
  });

  await bootstrapSession(page, FACULTY_USER);

  await page.locator('#top-nav-rms').click();
  await expect(page.locator('#rms-section')).toBeVisible();

  await openCopilot(page);
  await page.locator('#rms-search-registration').fill('22BCS777');
  await expect(page.locator('#verlyn-panel')).toBeVisible();
  await expect(page.locator('#verlyn-flag-registration')).toHaveValue('22BCS777');

  await page.locator('#rms-student-search-btn').click();
  await expect(page.locator('#rms-student-summary')).toContainText('Riya Sharma');

  await page
    .locator('#verlyn-quick-actions form[data-verlyn-action="flag_reason"] button[type="submit"]')
    .click();

  await expect(page.locator('#verlyn-output')).toContainText('Flag Review for 22BCS777');
  await expect(page.locator('#verlyn-output')).toContainText('Audit Log: #501');

  expect(copilotRequests).toEqual([
    expect.objectContaining({
      query_text: 'Show why student 22BCS777 is flagged',
      registration_number: '22BCS777',
      student_id: null,
    }),
  ]);
});

test('faculty remedial module stays synced with copilot and refreshes classes after planning', async ({ page }) => {
  const copilotRequests = [];
  let remedialClasses = [];

  await installApiRouter(page, async (route, request, url) => {
    if (url.pathname === '/core/courses' && request.method() === 'GET') {
      await json(route, [
        {
          id: 901,
          code: 'CSE501',
          title: 'Distributed Systems',
        },
      ]);
      return true;
    }

    if (url.pathname === '/makeup/faculty/eligible-courses' && request.method() === 'GET') {
      await json(route, [
        {
          id: 901,
          code: 'CSE501',
          title: 'Distributed Systems',
        },
      ]);
      return true;
    }

    if (url.pathname === '/makeup/classes' && request.method() === 'GET') {
      await json(route, remedialClasses);
      return true;
    }

    if (url.pathname === '/copilot/query' && request.method() === 'POST') {
      const payload = parseJson(request);
      copilotRequests.push(payload);
      remedialClasses = [
        {
          id: 601,
          course_id: 901,
          course_code: 'CSE501',
          course_title: 'Distributed Systems',
          class_date: '2026-03-10',
          start_time: '15:00:00',
          end_time: '16:00:00',
          topic: 'Recovery Lab',
          sections: ['P132'],
          class_mode: 'offline',
          room_number: '34-101',
          remedial_code: 'RD601',
          is_active: true,
        },
      ];
      await json(route, {
        intent: 'create_remedial_plan',
        title: 'Remedial Plan Scheduled',
        outcome: 'completed',
        explanation: [
          'The remedial plan passed section, time, and mode validation.',
          'Scheduling was recorded and the class list has been refreshed.',
        ],
        evidence: [
          {
            status: 'info',
            label: 'Section',
            value: 'P132',
          },
          {
            status: 'info',
            label: 'Schedule',
            value: '2026-03-10 15:00 offline in room 34-101',
          },
        ],
        actions: [
          {
            action: 'schedule_remedial',
            status: 'completed',
            detail: 'Remedial class RD601 was created for faculty review.',
          },
        ],
        next_steps: ['Send the remedial code to the section when you are ready.'],
        audit_id: 601,
      });
      return true;
    }

    return false;
  });

  await bootstrapSession(page, FACULTY_USER);

  await page.locator('#top-nav-remedial').click();
  await expect(page.locator('#remedial-section')).toBeVisible();
  await expect(page.locator('#remedial-classes-list')).toContainText('No active/upcoming remedial classes.');

  await openCopilot(page);

  await page.locator('#remedial-course-code-input').fill('CSE501');
  await page.locator('#remedial-course-title-input').fill('Distributed Systems');
  await page.locator('#remedial-sections-input').fill('P132');
  await setInputValue(page.locator('#remedial-date'), '2026-03-10');
  await setInputValue(page.locator('#remedial-start-time'), '15:00');
  await page.locator('#remedial-room-input').fill('34-101');

  await expect(page.locator('#verlyn-panel')).toBeVisible();
  await expect(page.locator('#verlyn-remedial-course-code')).toHaveValue('CSE501');
  await expect(page.locator('#verlyn-remedial-section')).toHaveValue('P132');
  await expect(page.locator('#verlyn-remedial-date')).toHaveValue('2026-03-10');
  await expect(page.locator('#verlyn-remedial-time')).toHaveValue('15:00');
  await expect(page.locator('#verlyn-remedial-room')).toHaveValue('34-101');

  await page
    .locator('#verlyn-quick-actions form[data-verlyn-action="create_remedial_plan"] button[type="submit"]')
    .click();

  await expect(page.locator('#verlyn-output')).toContainText('Remedial Plan Scheduled');
  await expect(page.locator('#verlyn-output')).toContainText('Audit Log: #601');
  await expect(page.locator('#remedial-classes-list')).toContainText('CSE501 - Distributed Systems');
  await expect(page.locator('#remedial-classes-list')).toContainText('Code RD601');

  expect(copilotRequests).toEqual([
    expect.objectContaining({
      query_text: 'Create a remedial plan for course CSE501 section P132 on 2026-03-10 at 15:00 room 34-101',
      course_code: 'CSE501',
      section: 'P132',
      class_date: '2026-03-10',
      start_time: '15:00',
      class_mode: 'offline',
      room_number: '34-101',
      send_message: true,
    }),
  ]);
});

test('admin administrative copilot exposes remedial planning and searchable audit refresh', async ({ page }) => {
  const auditRequests = [];
  let auditRows = [
    {
      id: 701,
      query_text: 'Show why student 22BCS999 is flagged',
      intent: 'student_flag_reason',
      outcome: 'completed',
      actor_user_id: 31,
      actor_role: 'admin',
      actor_email: 'admin@example.com',
      created_at: '2026-03-08T09:05:00Z',
      scope: 'administrative',
      target_section: 'P140',
      target_student_id: 999,
      explanation: ['Existing flagged-student audit run.'],
      evidence: [
        {
          status: 'warn',
          label: 'Pending issues',
          value: 'Student still has open discrepancies.',
        },
      ],
      actions: [
        {
          action: 'review_flag',
          status: 'completed',
          detail: 'Baseline audit row.',
        },
      ],
      result: {
        next_steps: ['Review student status before final escalation.'],
      },
    },
  ];

  await installApiRouter(page, async (route, request, url) => {
    if (url.pathname === '/admin/live' && request.method() === 'GET') {
      await json(route, buildAdminLivePayload());
      return true;
    }

    if (url.pathname === '/admin/insights' && request.method() === 'GET') {
      await json(route, buildAdminInsightsPayload());
      return true;
    }

    if (url.pathname === '/food/demand' && request.method() === 'GET') {
      await json(route, []);
      return true;
    }

    if (url.pathname === '/attendance/summary' && request.method() === 'GET') {
      await json(route, []);
      return true;
    }

    if (url.pathname === '/attendance/absentees' && request.method() === 'GET') {
      await json(route, []);
      return true;
    }

    if (url.pathname === '/copilot/audit' && request.method() === 'GET') {
      const snapshot = Object.fromEntries(url.searchParams.entries());
      auditRequests.push(snapshot);
      await json(route, filterAuditRows(auditRows, url.searchParams));
      return true;
    }

    if (url.pathname === '/copilot/query' && request.method() === 'POST') {
      const payload = parseJson(request);
      auditRows = [
        {
          id: 702,
          query_text: payload.query_text,
          intent: 'create_remedial_plan',
          outcome: 'completed',
          actor_user_id: 31,
          actor_role: 'admin',
          actor_email: 'admin@example.com',
          created_at: '2026-03-08T09:15:00Z',
          scope: 'administrative',
          target_section: 'P140',
          target_course_id: 701,
          explanation: [
            'Administrative remedial planning is allowed for admin role in the governance module.',
          ],
          evidence: [
            {
              status: 'info',
              label: 'Planned session',
              value: 'CSE701 | P140 | 2026-03-11 11:30',
            },
          ],
          actions: [
            {
              action: 'schedule_remedial',
              status: 'completed',
              detail: 'Administrative scheduling executed.',
            },
          ],
          result: {
            next_steps: ['Share the remedial plan with the responsible faculty lead.'],
          },
        },
        ...auditRows,
      ];
      await json(route, {
        intent: 'create_remedial_plan',
        title: 'Administrative Remedial Scheduled',
        outcome: 'completed',
        explanation: [
          'Admin scheduling is permitted from the administrative copilot workflow.',
          'The copilot timeline was refreshed immediately after execution.',
        ],
        evidence: [
          {
            status: 'info',
            label: 'Section',
            value: 'P140',
          },
          {
            status: 'info',
            label: 'Schedule',
            value: '2026-03-11 11:30 offline in room A-204',
          },
        ],
        actions: [
          {
            action: 'schedule_remedial',
            status: 'completed',
            detail: 'Administrative remedial plan recorded.',
          },
        ],
        next_steps: ['Review the audit timeline entry before distributing notifications.'],
        audit_id: 702,
      });
      return true;
    }

    return false;
  });

  await bootstrapSession(page, ADMIN_USER);

  await page.locator('#top-nav-administrative').click();
  await expect(page.locator('#executive-section')).toBeVisible();
  await expect(page.locator('#admin-copilot-audit-wrap')).toContainText('Show why student 22BCS999 is flagged');

  await openCopilot(page);
  await expect(page.locator('#verlyn-quick-actions [data-verlyn-action="flag_reason"]')).toBeVisible();
  await expect(page.locator('#verlyn-remedial-course-code')).toBeVisible();

  await page.locator('#admin-search-student-registration').fill('22BCS999');
  await expect(page.locator('#verlyn-panel')).toBeVisible();
  await expect(page.locator('#verlyn-flag-registration')).toHaveValue('22BCS999');

  await page.locator('[data-verlyn-action="focus_audit_timeline"]').click();
  await expect(page.locator('#admin-copilot-audit-search')).toBeFocused();

  await page.locator('#verlyn-remedial-course-code').fill('CSE701');
  await page.locator('#verlyn-remedial-section').fill('P140');
  await setInputValue(page.locator('#verlyn-remedial-date'), '2026-03-11');
  await setInputValue(page.locator('#verlyn-remedial-time'), '11:30');
  await page.locator('#verlyn-remedial-room').fill('A-204');

  const auditRequestCountBeforeRun = auditRequests.length;

  await page
    .locator('#verlyn-quick-actions form[data-verlyn-action="create_remedial_plan"] button[type="submit"]')
    .click();

  await expect(page.locator('#verlyn-output')).toContainText('Administrative Remedial Scheduled');
  await expect(page.locator('#verlyn-output')).toContainText('Audit Log: #702');
  await expect(page.locator('#admin-copilot-audit-wrap')).toContainText('Create a remedial plan for course CSE701 section P140');
  await expect.poll(() => auditRequests.length).toBeGreaterThan(auditRequestCountBeforeRun);

  await page.locator('#verlyn-minimize-btn').click();
  await expect(page.locator('#verlyn-toggle-btn')).toHaveAttribute('aria-expanded', 'false');

  await page.locator('#admin-copilot-audit-search').fill('CSE701');
  await page.locator('#admin-copilot-audit-intent').selectOption('create_remedial_plan');
  await page.locator('#admin-copilot-audit-outcome').selectOption('completed');
  await page.locator('#admin-copilot-audit-role').selectOption('admin');
  await page.locator('#admin-copilot-audit-actor-user-id').fill('31');

  const auditRequestCountBeforeFilter = auditRequests.length;
  await page.locator('#admin-copilot-audit-search-btn').click();
  await expect.poll(() => auditRequests.length).toBeGreaterThan(auditRequestCountBeforeFilter);
  await expect(page.locator('#admin-copilot-audit-wrap details')).toHaveCount(1);
  await expect(page.locator('#admin-copilot-audit-wrap')).toContainText('#702');

  expect(auditRequests.at(-1)).toMatchObject({
    q: 'CSE701',
    intent: 'create_remedial_plan',
    outcome: 'completed',
    actor_role: 'admin',
    actor_user_id: '31',
    limit: '50',
  });
});
