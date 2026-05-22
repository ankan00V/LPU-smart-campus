from __future__ import annotations

from html import escape


def _pct(value: object) -> float:
    try:
        return max(0.0, min(100.0, float(value or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _risk_label(attendance_percent: float, threshold: float) -> tuple[str, str, str]:
    if attendance_percent < max(1.0, threshold * 0.35):
        return ("Critical", "#b42318", "#fef3f2")
    if attendance_percent < max(1.0, threshold * 0.65):
        return ("High Priority", "#b54708", "#fffaeb")
    if attendance_percent < threshold:
        return ("Needs Recovery", "#a15c07", "#fff7ed")
    return ("Monitor Closely", "#067647", "#ecfdf3")


def _resource_button(label: str, url: str, *, bg: str, fg: str) -> str:
    safe_url = escape(str(url or "").strip(), quote=True)
    if not safe_url:
        return ""
    return f"""
      <a href="{safe_url}" target="_blank" style="display:inline-block;margin:6px 6px 0 0;padding:9px 12px;border-radius:10px;background:{bg};color:{fg};font-family:Arial,Helvetica,sans-serif;font-size:12px;font-weight:700;text-decoration:none;line-height:14px;">
        {escape(label)}
      </a>
    """


def _subject_card(item: dict[str, object], *, threshold: float) -> str:
    course_code = escape(str(item.get("course_code") or "").strip())
    course_title = escape(str(item.get("course_title") or "").strip())
    attendance = _pct(item.get("attendance_percent"))
    risk, risk_color, risk_bg = _risk_label(attendance, threshold)
    progress_color = "#dc2626" if risk == "Critical" else "#f59e0b"
    label = f"{course_code} - {course_title}" if course_code and course_title else course_code or course_title or "Subject"

    buttons: list[str] = []
    for idx, resource in enumerate(item.get("videos", []) or []):
        if not isinstance(resource, dict):
            continue
        title = "Watch NPTEL" if idx == 0 else "Watch MIT OCW"
        buttons.append(_resource_button(title, str(resource.get("url") or ""), bg="#1d4ed8", fg="#ffffff"))
    for idx, resource in enumerate(item.get("references", []) or []):
        if not isinstance(resource, dict):
            continue
        title = "Open Resources" if idx == 0 else "View Materials"
        buttons.append(_resource_button(title, str(resource.get("url") or ""), bg="#eef2ff", fg="#3730a3"))

    return f"""
      <tr>
        <td style="padding:0 0 12px 0;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse:separate;border-spacing:0;background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;box-shadow:0 8px 22px rgba(15,23,42,0.06);">
            <tr>
              <td style="padding:16px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                  <tr>
                    <td style="font-family:Arial,Helvetica,sans-serif;color:#111827;font-size:15px;font-weight:800;line-height:20px;padding-right:12px;">{label}</td>
                    <td align="right" style="white-space:nowrap;">
                      <span style="display:inline-block;padding:6px 10px;border-radius:999px;background:{risk_bg};color:{risk_color};font-family:Arial,Helvetica,sans-serif;font-size:11px;font-weight:800;line-height:12px;">{risk}</span>
                    </td>
                  </tr>
                </table>
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top:12px;">
                  <tr>
                    <td style="font-family:Arial,Helvetica,sans-serif;color:#6b7280;font-size:12px;font-weight:700;">Attendance</td>
                    <td align="right" style="font-family:Arial,Helvetica,sans-serif;color:#111827;font-size:18px;font-weight:900;">{attendance:.1f}%</td>
                  </tr>
                </table>
                <div style="height:9px;background:#f3f4f6;border-radius:999px;overflow:hidden;margin-top:8px;">
                  <div style="height:9px;width:{attendance:.0f}%;max-width:100%;background:{progress_color};border-radius:999px;"></div>
                </div>
                <div style="margin-top:12px;">{''.join(buttons)}</div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    """


def render_recovery_email_html(
    *,
    student_name: str,
    overall_attendance_percent: float,
    watch_threshold: float,
    risk_level: str,
    subject_resources: list[dict[str, object]],
    next_slot_line: str,
    office_hour_line: str,
) -> str:
    overall = _pct(overall_attendance_percent)
    threshold = _pct(watch_threshold) or 75.0
    progress_color = "#dc2626" if overall < threshold * 0.5 else "#f59e0b"
    status_text = "Below Safe Threshold" if overall < threshold else "Subject Recovery Needed"
    urgency_text = "Critical" if str(risk_level).lower() == "critical" or overall < threshold * 0.5 else "High Priority"
    subject_cards = "".join(_subject_card(item, threshold=threshold) for item in subject_resources)
    if not subject_cards:
        subject_cards = """
          <tr>
            <td style="padding:14px 16px;background:#fff7ed;border:1px solid #fed7aa;border-radius:14px;font-family:Arial,Helvetica,sans-serif;color:#9a3412;font-size:13px;line-height:19px;">
              No below-threshold subject resources are attached to this alert.
            </td>
          </tr>
        """

    safe_name = escape(str(student_name or "Student").strip() or "Student")
    safe_next_slot = escape(str(next_slot_line or "Request a remedial slot from your faculty.").lstrip("- ").strip())
    safe_office_hour = escape(str(office_hour_line or "Request a faculty check-in this week.").lstrip("- ").strip())

    return f"""<!doctype html>
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>Attendance Recovery Required</title>
  </head>
  <body style="margin:0;padding:0;background:#f4f7fb;">
    <div style="display:none;max-height:0;overflow:hidden;font-size:1px;color:#f4f7fb;line-height:1px;">
      Attendance is below the required threshold. Review your recovery plan and subject resources.
    </div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f4f7fb;border-collapse:collapse;">
      <tr>
        <td align="center" style="padding:24px 12px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;max-width:680px;border-collapse:separate;border-spacing:0;">
            <tr>
              <td style="border-radius:22px 22px 0 0;background:linear-gradient(135deg,#111827 0%,#1d4ed8 58%,#6d28d9 100%);padding:28px 24px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                  <tr>
                    <td style="font-family:Arial,Helvetica,sans-serif;color:#ffffff;">
                      <div style="font-size:13px;font-weight:800;letter-spacing:.03em;text-transform:uppercase;">LPU Smart Campus</div>
                      <div style="font-size:28px;font-weight:900;line-height:34px;margin-top:8px;">Attendance Recovery Required</div>
                      <div style="font-size:14px;line-height:21px;color:#dbeafe;margin-top:8px;">Recovery Copilot has generated a structured academic recovery plan for {safe_name}.</div>
                    </td>
                    <td align="right" style="vertical-align:top;">
                      <span style="display:inline-block;background:rgba(255,255,255,0.16);border:1px solid rgba(255,255,255,0.28);color:#ffffff;border-radius:999px;padding:8px 12px;font-family:Arial,Helvetica,sans-serif;font-size:12px;font-weight:800;white-space:nowrap;">Recovery Copilot Alert</span>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="background:#ffffff;padding:22px 24px 8px 24px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse:separate;border-spacing:0;background:#fffaf0;border:1px solid #fed7aa;border-radius:18px;">
                  <tr>
                    <td style="padding:18px;">
                      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                        <tr>
                          <td style="font-family:Arial,Helvetica,sans-serif;color:#111827;">
                            <div style="font-size:12px;font-weight:900;color:#b45309;text-transform:uppercase;letter-spacing:.04em;">Status Summary</div>
                            <div style="font-size:15px;line-height:22px;margin-top:8px;">Your attendance is currently below the required academic threshold. Immediate corrective action is recommended.</div>
                          </td>
                          <td align="right" style="white-space:nowrap;padding-left:12px;">
                            <div style="font-family:Arial,Helvetica,sans-serif;color:#111827;font-size:34px;font-weight:900;line-height:38px;">{overall:.1f}%</div>
                            <div style="font-family:Arial,Helvetica,sans-serif;color:#92400e;font-size:12px;font-weight:800;">Overall Attendance</div>
                          </td>
                        </tr>
                      </table>
                      <div style="height:10px;background:#ffedd5;border-radius:999px;overflow:hidden;margin-top:16px;">
                        <div style="height:10px;width:{overall:.0f}%;max-width:100%;background:{progress_color};border-radius:999px;"></div>
                      </div>
                      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top:14px;">
                        <tr>
                          <td style="padding:0 8px 0 0;">
                            <span style="display:inline-block;padding:7px 10px;border-radius:999px;background:#fef3f2;color:#b42318;font-family:Arial,Helvetica,sans-serif;font-size:12px;font-weight:800;">{escape(status_text)}</span>
                          </td>
                          <td style="padding:0 8px;">
                            <span style="display:inline-block;padding:7px 10px;border-radius:999px;background:#fffbeb;color:#b45309;font-family:Arial,Helvetica,sans-serif;font-size:12px;font-weight:800;">Urgency: {escape(urgency_text)}</span>
                          </td>
                          <td style="padding:0 0 0 8px;">
                            <span style="display:inline-block;padding:7px 10px;border-radius:999px;background:#ecfdf3;color:#067647;font-family:Arial,Helvetica,sans-serif;font-size:12px;font-weight:800;">Target: {threshold:.0f}%+</span>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="background:#ffffff;padding:18px 24px 4px 24px;">
                <div style="font-family:Arial,Helvetica,sans-serif;color:#111827;font-size:18px;font-weight:900;line-height:24px;">Subject Alerts & Learning Resources</div>
                <div style="font-family:Arial,Helvetica,sans-serif;color:#6b7280;font-size:13px;line-height:20px;margin-top:4px;">Focus on these subjects first. Use the buttons below to start targeted catch-up immediately.</div>
              </td>
            </tr>
            <tr>
              <td style="background:#ffffff;padding:10px 24px 8px 24px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">{subject_cards}</table>
              </td>
            </tr>
            <tr>
              <td style="background:#ffffff;padding:10px 24px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse:separate;border-spacing:0;background:#f8fafc;border:1px solid #e2e8f0;border-radius:18px;">
                  <tr>
                    <td style="padding:18px;">
                      <div style="font-family:Arial,Helvetica,sans-serif;color:#111827;font-size:18px;font-weight:900;">Recovery Action Plan</div>
                      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top:12px;">
                        <tr><td style="font-family:Arial,Helvetica,sans-serif;color:#111827;font-size:14px;line-height:22px;padding:6px 0;">&#10003; Maintain a strict 14-day attendance streak with zero optional absences.</td></tr>
                        <tr><td style="font-family:Arial,Helvetica,sans-serif;color:#111827;font-size:14px;line-height:22px;padding:6px 0;">&#10003; Prioritize low-attendance subjects this week and complete the attached resources.</td></tr>
                        <tr><td style="font-family:Arial,Helvetica,sans-serif;color:#111827;font-size:14px;line-height:22px;padding:6px 0;">&#10003; {safe_next_slot}</td></tr>
                        <tr><td style="font-family:Arial,Helvetica,sans-serif;color:#111827;font-size:14px;line-height:22px;padding:6px 0;">&#10003; {safe_office_hour}</td></tr>
                        <tr><td style="font-family:Arial,Helvetica,sans-serif;color:#111827;font-size:14px;line-height:22px;padding:6px 0;">&#10003; Track attendance daily in Smart Campus until recovery is stable.</td></tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="background:#ffffff;padding:10px 24px 24px 24px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse:separate;border-spacing:0;background:linear-gradient(135deg,#eef2ff 0%,#f5f3ff 100%);border:1px solid #ddd6fe;border-radius:18px;">
                  <tr>
                    <td style="padding:18px;font-family:Arial,Helvetica,sans-serif;">
                      <div style="color:#3730a3;font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.04em;">Saarthi AI Support</div>
                      <div style="color:#111827;font-size:17px;font-weight:900;line-height:23px;margin-top:6px;">Need academic guidance or recovery planning?</div>
                      <div style="color:#4b5563;font-size:13px;line-height:20px;margin-top:6px;">Use Saarthi AI inside Smart Campus for subject prioritization, schedule planning, and next-step guidance.</div>
                      <a href="https://campus.test/ui" target="_blank" style="display:inline-block;margin-top:14px;padding:11px 14px;border-radius:12px;background:#4f46e5;color:#ffffff;font-size:13px;font-weight:800;text-decoration:none;">Open Saarthi AI</a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="border-radius:0 0 22px 22px;background:#111827;padding:20px 24px;font-family:Arial,Helvetica,sans-serif;color:#cbd5e1;">
                <div style="font-size:13px;font-weight:900;color:#ffffff;">LPU Smart Campus</div>
                <div style="font-size:12px;line-height:18px;margin-top:6px;">Recovery Copilot System - automated academic alert generated from attendance records and recovery rules.</div>
                <div style="font-size:12px;line-height:18px;margin-top:8px;">This notification is intended to help you recover attendance early. For genuine academic or personal constraints, contact your faculty coordinator or use Saarthi in Smart Campus.</div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""
