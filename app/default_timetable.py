"""Global weekly timetable used for default student schedule seeding.

This blueprint matches the latest uploaded timetable grid.
"""

COURSES = {
    "CSE332": {
        "title": "Industry Ethics and Legal Issues",
        "faculty_name": "Arvind Kumar Bhatia",
        "faculty_email": "arvind.bhatia@lpu.in",
    },
    "CSE357": {
        "title": "Combinatorial Studies",
        "faculty_name": "Konne Madhavi",
        "faculty_email": "konne.madhavi@lpu.in",
    },
    "CSES001": {
        "title": "Fundamentals of Computers-I",
        "faculty_name": "Hunny Batra",
        "faculty_email": "hunny.batra@lpu.in",
    },
    "INT312": {
        "title": "Big Data Fundamentals",
        "faculty_name": "Dr. Ravindra Singh Yadav",
        "faculty_email": "ravindra.yadav@lpu.in",
    },
    "MKT905": {
        "title": "Search Engine Optimization",
        "faculty_name": "Abhishek Sahai",
        "faculty_email": "abhishek.sahai@lpu.in",
    },
    "PES319": {
        "title": "Soft Skills-II",
        "faculty_name": "Hariz Aftab",
        "faculty_email": "hariz.aftab@lpu.in",
    },
    "PETV08": {
        "title": "Modern Web Programming with HTML, CSS & Javascript",
        "faculty_name": "Dr. Avinash Kaur",
        "faculty_email": "avinash.kaur@lpu.in",
    },
}


def _entry(
    course_code: str,
    weekday: int,
    start: str,
    end: str,
    block: str,
    room: str,
    kind: str,
    section: str,
) -> dict:
    meta = COURSES[course_code]
    label_room = f"{block}-{room}" if block and room else room
    return {
        "course_code": course_code,
        "course_title": meta["title"],
        "faculty_name": meta["faculty_name"],
        "faculty_email": meta["faculty_email"],
        "weekday": weekday,
        "start": start,
        "end": end,
        "classroom_block": block,
        "classroom_room": room,
        "classroom_label": f"{label_room} - {kind} - {course_code} | {section}",
    }


DEFAULT_TIMETABLE_BLUEPRINT = [
    # Monday
    _entry("INT312", 0, "13:00", "14:00", "26", "505", "Lecture", "423ZK"),
    _entry("INT312", 0, "14:00", "15:00", "26", "505", "Lecture", "423ZK"),
    _entry("CSE332", 0, "15:00", "16:00", "26", "505", "Lecture", "423ZK"),
    _entry("PETV08", 0, "18:00", "19:00", "Assignment", "1", "Lecture", "9PV51"),
    _entry("CSES001", 0, "19:00", "20:00", "Assignment", "1", "Lecture", "9P132"),
    _entry("CSES001", 0, "20:00", "21:00", "Assignment", "1", "Lecture", "9P132"),
    # Tuesday
    _entry("CSE357", 1, "10:00", "11:00", "28", "408", "Practical", "423ZK"),
    _entry("CSE357", 1, "11:00", "12:00", "28", "408", "Practical", "423ZK"),
    _entry("INT312", 1, "14:00", "15:00", "26", "603", "Practical", "423ZK"),
    _entry("INT312", 1, "15:00", "16:00", "26", "603", "Practical", "423ZK"),
    _entry("PETV08", 1, "18:00", "19:00", "Assignment", "1", "Lecture", "9PV51"),
    # Wednesday
    _entry("MKT905", 2, "13:00", "14:00", "37", "706", "Lecture", "2OM67"),
    _entry("PES319", 2, "14:00", "15:00", "26", "504", "Lecture", "423ZK"),
    _entry("CSE332", 2, "15:00", "16:00", "26", "504", "Lecture", "423ZK"),
    _entry("PETV08", 2, "18:00", "19:00", "Assignment", "1", "Lecture", "9PV51"),
    _entry("CSES001", 2, "19:00", "20:00", "Assignment", "1", "Lecture", "9P132"),
    _entry("CSES001", 2, "20:00", "21:00", "Assignment", "1", "Lecture", "9P132"),
    # Thursday
    _entry("MKT905", 3, "13:00", "14:00", "37", "703", "Lecture", "2OM67"),
    _entry("CSE357", 3, "14:00", "15:00", "27", "104A", "Lecture", "423ZK"),
    _entry("CSE357", 3, "15:00", "16:00", "27", "104A", "Lecture", "423ZK"),
    _entry("PETV08", 3, "18:00", "19:00", "Assignment", "1", "Lecture", "9PV51"),
    # Friday
    _entry("PES319", 4, "10:00", "11:00", "27", "107", "Tutorial", "423ZK"),
    _entry("PES319", 4, "11:00", "12:00", "27", "107", "Tutorial", "423ZK"),
    _entry("MKT905", 4, "13:00", "14:00", "33", "505", "Lecture", "2OM67"),
    _entry("PETV08", 4, "18:00", "19:00", "Assignment", "1", "Lecture", "9PV51"),
    _entry("CSES001", 4, "19:00", "20:00", "Assignment", "1", "Lecture", "9P132"),
    _entry("CSES001", 4, "20:00", "21:00", "Assignment", "1", "Lecture", "9P132"),
]
