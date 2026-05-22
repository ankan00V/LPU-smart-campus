from app.recovery_email_template import render_recovery_email_html


def test_recovery_email_template_uses_cards_and_ctas_without_visible_raw_urls():
    html = render_recovery_email_html(
        student_name="ANKAN GHOSH",
        overall_attendance_percent=0.94,
        watch_threshold=75.0,
        risk_level="critical",
        next_slot_line="- Remedial slot suggested: 2026-05-22 at 10:00.",
        office_hour_line="- Faculty check-in suggested by: 2026-05-23T10:00:00.",
        subject_resources=[
            {
                "course_code": "CSE332",
                "course_title": "Industry Ethics and Legal Issues",
                "attendance_percent": 0.0,
                "videos": [
                    {
                        "title": "NPTEL video lectures",
                        "url": "https://www.youtube.com/results?search_query=NPTEL+CSE332+lectures",
                    },
                    {
                        "title": "MIT OCW videos",
                        "url": "https://www.youtube.com/results?search_query=CSE332+MIT+OpenCourseWare",
                    },
                ],
                "references": [
                    {
                        "title": "MIT OCW materials",
                        "url": "https://ocw.mit.edu/search/?q=Industry+Ethics",
                    }
                ],
            }
        ],
    )

    assert "<!doctype html>" in html.lower()
    assert "Attendance Recovery Required" in html
    assert "Recovery Copilot Alert" in html
    assert "CSE332 - Industry Ethics and Legal Issues" in html
    assert "Watch NPTEL" in html
    assert "Watch MIT OCW" in html
    assert "Open Resources" in html
    assert "https://www.youtube.com/results?search_query=NPTEL+CSE332+lectures" in html
    assert "Video:" not in html
    assert "Resource:" not in html
