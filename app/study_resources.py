from __future__ import annotations

from dataclasses import dataclass
from dataclasses import asdict
from urllib.parse import quote_plus


@dataclass(frozen=True, slots=True)
class StudyResource:
    title: str
    url: str
    resource_type: str
    source: str


@dataclass(frozen=True, slots=True)
class SubjectStudyResources:
    course_code: str
    course_title: str
    videos: tuple[StudyResource, ...]
    references: tuple[StudyResource, ...]


_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "software_engineering": (
        "software engineering",
        "software development",
        "sdlc",
        "requirements",
        "testing",
        "uml",
        "agile",
    ),
    "distributed_systems": (
        "distributed systems",
        "distributed computing",
        "consensus",
        "replication",
        "fault tolerance",
        "microservices",
    ),
    "operating_systems": (
        "operating system",
        "operating systems",
        "os",
        "process",
        "threads",
        "scheduling",
        "memory management",
    ),
    "database_systems": (
        "database",
        "dbms",
        "sql",
        "postgresql",
        "transaction",
        "normalization",
    ),
    "computer_networks": (
        "computer network",
        "computer networks",
        "networking",
        "tcp",
        "ip",
        "routing",
        "dns",
    ),
    "data_structures": (
        "data structures",
        "algorithms",
        "dsa",
        "graph",
        "tree",
        "sorting",
        "complexity",
    ),
    "machine_learning": (
        "machine learning",
        "artificial intelligence",
        "deep learning",
        "neural network",
        "data science",
    ),
    "web_development": (
        "web development",
        "html",
        "css",
        "javascript",
        "react",
        "frontend",
        "backend",
    ),
    "cybersecurity": (
        "cyber security",
        "cybersecurity",
        "information security",
        "cryptography",
        "network security",
    ),
    "cloud_computing": (
        "cloud computing",
        "cloud",
        "devops",
        "docker",
        "kubernetes",
        "aws",
    ),
    "mathematics": (
        "mathematics",
        "linear algebra",
        "calculus",
        "probability",
        "statistics",
        "discrete mathematics",
    ),
}


_REFERENCE_CATALOG: dict[str, tuple[StudyResource, ...]] = {
    "software_engineering": (
        StudyResource(
            "SWEBOK Guide - software engineering knowledge areas",
            "https://www.computer.org/education/bodies-of-knowledge/software-engineering",
            "reference",
            "IEEE Computer Society",
        ),
        StudyResource(
            "Martin Fowler - software design and architecture articles",
            "https://martinfowler.com/",
            "reference",
            "Martin Fowler",
        ),
    ),
    "distributed_systems": (
        StudyResource(
            "MIT 6.824 Distributed Systems course materials",
            "https://pdos.csail.mit.edu/6.824/",
            "reference",
            "MIT CSAIL",
        ),
        StudyResource(
            "Designing Data-Intensive Applications notes and references",
            "https://dataintensive.net/",
            "reference",
            "Data-Intensive Systems",
        ),
    ),
    "operating_systems": (
        StudyResource(
            "Operating Systems: Three Easy Pieces",
            "https://pages.cs.wisc.edu/~remzi/OSTEP/",
            "reference",
            "University of Wisconsin",
        ),
        StudyResource(
            "MIT OpenCourseWare - Operating System Engineering",
            "https://ocw.mit.edu/courses/6-828-operating-system-engineering-fall-2012/",
            "reference",
            "MIT OpenCourseWare",
        ),
    ),
    "database_systems": (
        StudyResource(
            "PostgreSQL official documentation",
            "https://www.postgresql.org/docs/",
            "documentation",
            "PostgreSQL",
        ),
        StudyResource(
            "CMU Database Group course resources",
            "https://15445.courses.cs.cmu.edu/",
            "reference",
            "CMU Database Group",
        ),
    ),
    "computer_networks": (
        StudyResource(
            "Computer Networking: Principles, Protocols and Practice",
            "https://www.computer-networking.info/",
            "reference",
            "Open Textbook",
        ),
        StudyResource(
            "Cloudflare Learning Center - networking concepts",
            "https://www.cloudflare.com/learning/network-layer/",
            "documentation",
            "Cloudflare",
        ),
    ),
    "data_structures": (
        StudyResource(
            "Open Data Structures textbook",
            "https://opendatastructures.org/",
            "reference",
            "Open Data Structures",
        ),
        StudyResource(
            "CP-Algorithms reference",
            "https://cp-algorithms.com/",
            "documentation",
            "CP-Algorithms",
        ),
    ),
    "machine_learning": (
        StudyResource(
            "Google Machine Learning Crash Course",
            "https://developers.google.com/machine-learning/crash-course",
            "documentation",
            "Google Developers",
        ),
        StudyResource(
            "scikit-learn user guide",
            "https://scikit-learn.org/stable/user_guide.html",
            "documentation",
            "scikit-learn",
        ),
    ),
    "web_development": (
        StudyResource(
            "MDN Web Docs",
            "https://developer.mozilla.org/en-US/docs/Learn",
            "documentation",
            "Mozilla MDN",
        ),
        StudyResource(
            "web.dev learning paths",
            "https://web.dev/learn",
            "documentation",
            "Google web.dev",
        ),
    ),
    "cybersecurity": (
        StudyResource(
            "OWASP Web Security Testing Guide",
            "https://owasp.org/www-project-web-security-testing-guide/",
            "documentation",
            "OWASP",
        ),
        StudyResource(
            "NIST Cybersecurity Framework",
            "https://www.nist.gov/cyberframework",
            "reference",
            "NIST",
        ),
    ),
    "cloud_computing": (
        StudyResource(
            "Kubernetes official documentation",
            "https://kubernetes.io/docs/home/",
            "documentation",
            "Kubernetes",
        ),
        StudyResource(
            "AWS Well-Architected Framework",
            "https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html",
            "documentation",
            "AWS",
        ),
    ),
    "mathematics": (
        StudyResource(
            "MIT OpenCourseWare Mathematics",
            "https://ocw.mit.edu/search/?d=Mathematics",
            "reference",
            "MIT OpenCourseWare",
        ),
        StudyResource(
            "Khan Academy Mathematics",
            "https://www.khanacademy.org/math",
            "reference",
            "Khan Academy",
        ),
    ),
}


def _normalized_subject_text(course_code: str, course_title: str) -> str:
    return f"{course_code} {course_title}".strip().lower()


def _classify_subject(course_code: str, course_title: str) -> str | None:
    text = _normalized_subject_text(course_code, course_title)
    best_category: str | None = None
    best_score = 0
    for category, keywords in _CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > best_score:
            best_score = score
            best_category = category
    return best_category


def _youtube_search_resource(label: str, query: str) -> StudyResource:
    return StudyResource(
        title=label,
        url=f"https://www.youtube.com/results?search_query={quote_plus(query)}",
        resource_type="video",
        source="YouTube",
    )


def _ocw_search_resource(course_title: str) -> StudyResource:
    query = quote_plus(course_title or "computer science")
    return StudyResource(
        title=f"MIT OpenCourseWare search for {course_title or 'this subject'}",
        url=f"https://ocw.mit.edu/search/?q={query}",
        resource_type="reference",
        source="MIT OpenCourseWare",
    )


def subject_study_resources(
    *,
    course_code: str,
    course_title: str,
    max_videos: int = 2,
    max_references: int = 2,
) -> SubjectStudyResources:
    code = str(course_code or "").strip().upper()
    title = " ".join(str(course_title or "").split()).strip() or code or "Subject"
    subject_query = f"{code} {title}".strip()
    category = _classify_subject(code, title)

    videos = [
        _youtube_search_resource(
            f"NPTEL video lectures for {code or title}",
            f"NPTEL {subject_query} lectures",
        ),
        _youtube_search_resource(
            f"MIT OCW/free university videos for {title}",
            f"{title} MIT OpenCourseWare lecture",
        ),
    ]
    references = list(_REFERENCE_CATALOG.get(category or "", ()))
    references.append(_ocw_search_resource(title))

    return SubjectStudyResources(
        course_code=code,
        course_title=title,
        videos=tuple(videos[: max(1, int(max_videos))]),
        references=tuple(references[: max(1, int(max_references))]),
    )


def serialize_subject_study_resources(resources: SubjectStudyResources) -> dict[str, object]:
    return {
        "course_code": resources.course_code,
        "course_title": resources.course_title,
        "videos": [asdict(resource) for resource in resources.videos],
        "references": [asdict(resource) for resource in resources.references],
    }
