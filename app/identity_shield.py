import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy.orm import Session

from . import models, schemas
from .face_verification import compare_face_templates
from .media_storage import signed_url_for_object, store_data_url_object
from .mongo import get_mongo_db, mirror_document
from .realtime_bus import publish_domain_event

LOGGER = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _env_float(name: str, default: float) -> float:
    raw = (os.getenv(name, str(default)) or "").strip()
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _stable_hash(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _mask_email(email: str | None) -> str | None:
    normalized = str(email or "").strip().lower()
    if not normalized or "@" not in normalized:
        return normalized or None
    local, domain = normalized.split("@", 1)
    head = (local[:2] if len(local) >= 2 else local[:1]) or "x"
    return f"{head}***@{domain}"


def _device_fingerprint(device_id: str | None, user_agent: str | None) -> str | None:
    normalized_device = str(device_id or "").strip().lower()
    ua_hash = _stable_hash(user_agent)
    if not normalized_device and not ua_hash:
        return None
    seed = f"{normalized_device or 'device:none'}|{ua_hash or 'ua:none'}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _risk_level(score: float, *, blocking: bool = False) -> models.FraudRiskLevel:
    if blocking or score >= 75.0:
        return models.FraudRiskLevel.CRITICAL
    if score >= 50.0:
        return models.FraudRiskLevel.HIGH
    if score >= 20.0:
        return models.FraudRiskLevel.MEDIUM
    return models.FraudRiskLevel.LOW


def _status_for_risk(score: float, *, blocking: bool = False) -> models.IdentityVerificationStatus:
    if blocking or score >= 50.0:
        return models.IdentityVerificationStatus.FLAGGED
    if score >= 20.0:
        return models.IdentityVerificationStatus.IN_REVIEW
    return models.IdentityVerificationStatus.VERIFIED


def _append_signal(
    target: list[dict[str, Any]],
    *,
    signal_type: str,
    severity: models.FraudRiskLevel,
    score_delta: float,
    reason: str,
    evidence: dict[str, Any] | None = None,
    blocking: bool = False,
) -> None:
    target.append(
        {
            "signal_type": signal_type,
            "severity": severity,
            "score_delta": float(score_delta),
            "is_blocking": bool(blocking),
            "reason": reason,
            "evidence": evidence or {},
        }
    )


def observe_identity_session(
    mongo_db,
    *,
    user_id: int,
    email: str | None,
    role: str,
    student_id: int | None,
    faculty_id: int | None,
    device_id: str | None,
    user_agent: str | None,
    ip_address: str | None,
    session_id: str | None,
) -> str | None:
    if mongo_db is None:
        return None

    fingerprint = _device_fingerprint(device_id, user_agent)
    if not fingerprint:
        return None

    now = _utc_now()
    update: dict[str, Any] = {
        "$set": {
            "device_fingerprint": fingerprint,
            "device_id_hint": (str(device_id or "")[-12:] or None),
            "user_agent_hash": _stable_hash(user_agent),
            "last_ip_hash": _stable_hash(ip_address),
            "last_session_id": str(session_id or "").strip() or None,
            "last_seen_at": now,
            "updated_at": now,
        },
        "$setOnInsert": {
            "created_at": now,
            "session_count": 0,
            "linked_user_ids": [],
            "linked_student_ids": [],
            "linked_faculty_ids": [],
            "linked_roles": [],
            "linked_email_hashes": [],
            "seen_ip_hashes": [],
        },
        "$inc": {"session_count": 1},
    }

    add_to_set: dict[str, Any] = {}
    if user_id:
        add_to_set["linked_user_ids"] = int(user_id)
    if student_id:
        add_to_set["linked_student_ids"] = int(student_id)
    if faculty_id:
        add_to_set["linked_faculty_ids"] = int(faculty_id)
    if role:
        add_to_set["linked_roles"] = str(role)
    email_hash = _stable_hash(email)
    if email_hash:
        add_to_set["linked_email_hashes"] = email_hash
    ip_hash = _stable_hash(ip_address)
    if ip_hash:
        add_to_set["seen_ip_hashes"] = ip_hash
    if add_to_set:
        update["$addToSet"] = add_to_set

    mongo_db["identity_device_profiles"].update_one(
        {"device_fingerprint": fingerprint},
        update,
        upsert=True,
    )
    return fingerprint


def observe_applicant_identity(
    mongo_db,
    *,
    applicant_email: str | None,
    external_subject_key: str | None,
    device_id: str | None,
    user_agent: str | None,
    ip_address: str | None,
) -> str | None:
    if mongo_db is None:
        return None

    fingerprint = _device_fingerprint(device_id, user_agent)
    if not fingerprint:
        return None

    now = _utc_now()
    update: dict[str, Any] = {
        "$set": {
            "device_fingerprint": fingerprint,
            "device_id_hint": (str(device_id or "")[-12:] or None),
            "user_agent_hash": _stable_hash(user_agent),
            "last_ip_hash": _stable_hash(ip_address),
            "last_seen_at": now,
            "updated_at": now,
        },
        "$setOnInsert": {
            "created_at": now,
            "session_count": 0,
            "linked_user_ids": [],
            "linked_student_ids": [],
            "linked_faculty_ids": [],
            "linked_roles": [],
            "linked_email_hashes": [],
            "linked_applicant_email_hashes": [],
            "linked_external_subject_keys": [],
            "seen_ip_hashes": [],
        },
        "$inc": {"session_count": 1},
    }

    add_to_set: dict[str, Any] = {}
    applicant_email_hash = _stable_hash(applicant_email)
    if applicant_email_hash:
        add_to_set["linked_applicant_email_hashes"] = applicant_email_hash
    normalized_subject_key = str(external_subject_key or "").strip().lower()
    if normalized_subject_key:
        add_to_set["linked_external_subject_keys"] = normalized_subject_key
    ip_hash = _stable_hash(ip_address)
    if ip_hash:
        add_to_set["seen_ip_hashes"] = ip_hash
    if add_to_set:
        update["$addToSet"] = add_to_set

    mongo_db["identity_device_profiles"].update_one(
        {"device_fingerprint": fingerprint},
        update,
        upsert=True,
    )
    return fingerprint


def _device_profiles_for_subject(
    mongo_db,
    *,
    user_id: int | None = None,
    student_id: int | None = None,
    applicant_email: str | None = None,
    external_subject_key: str | None = None,
) -> list[dict[str, Any]]:
    if mongo_db is None:
        return []
    clauses: list[dict[str, Any]] = []
    if user_id is not None:
        clauses.append({"linked_user_ids": int(user_id)})
    if student_id is not None:
        clauses.append({"linked_student_ids": int(student_id)})
    applicant_email_hash = _stable_hash(applicant_email)
    if applicant_email_hash:
        clauses.append({"linked_applicant_email_hashes": applicant_email_hash})
    normalized_subject_key = str(external_subject_key or "").strip().lower()
    if normalized_subject_key:
        clauses.append({"linked_external_subject_keys": normalized_subject_key})
    if not clauses:
        return []
    return list(mongo_db["identity_device_profiles"].find({"$or": clauses}))


def build_subject_identity_graph(
    *,
    user_id: int | None = None,
    student_id: int | None = None,
    applicant_email: str | None = None,
    external_subject_key: str | None = None,
) -> dict[str, Any]:
    mongo_db = get_mongo_db(required=False)
    profiles = _device_profiles_for_subject(
        mongo_db,
        user_id=user_id,
        student_id=student_id,
        applicant_email=applicant_email,
        external_subject_key=external_subject_key,
    )

    normalized_applicant_email = str(applicant_email or "").strip().lower()
    normalized_subject_key = str(external_subject_key or "").strip().lower()
    if user_id is not None:
        subject_key = f"user:{int(user_id)}"
    elif student_id is not None:
        subject_key = f"student:{int(student_id)}"
    elif normalized_applicant_email:
        subject_key = f"applicant:{normalized_applicant_email}"
    else:
        subject_key = f"external:{normalized_subject_key}"
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    connected_user_ids: set[int] = set()
    connected_student_ids: set[int] = set()
    connected_applicant_hashes: set[str] = set()
    connected_external_subject_keys: set[str] = set()
    shared_device_count = 0
    latest_seen_at: datetime | None = None

    if user_id is not None:
        nodes[subject_key] = {
            "id": subject_key,
            "node_type": "user",
            "label": f"User #{int(user_id)}",
            "risk_level": models.FraudRiskLevel.LOW,
            "metadata": {},
        }
    if student_id is not None:
        student_key = f"student:{int(student_id)}"
        nodes[student_key] = {
            "id": student_key,
            "node_type": "student",
            "label": f"Student #{int(student_id)}",
            "risk_level": models.FraudRiskLevel.LOW,
            "metadata": {},
        }
    if normalized_applicant_email:
        nodes[subject_key] = {
            "id": subject_key,
            "node_type": "applicant",
            "label": normalized_applicant_email,
            "risk_level": models.FraudRiskLevel.LOW,
            "metadata": {},
        }
    elif normalized_subject_key:
        nodes[subject_key] = {
            "id": subject_key,
            "node_type": "external_subject",
            "label": normalized_subject_key,
            "risk_level": models.FraudRiskLevel.LOW,
            "metadata": {},
        }

    for profile in profiles:
        fingerprint = str(profile.get("device_fingerprint") or "").strip()
        if not fingerprint:
            continue
        device_key = f"device:{fingerprint}"
        linked_users = {int(value) for value in profile.get("linked_user_ids") or [] if value is not None}
        linked_students = {int(value) for value in profile.get("linked_student_ids") or [] if value is not None}
        linked_applicants = {str(value).strip().lower() for value in profile.get("linked_external_subject_keys") or [] if str(value).strip()}
        linked_applicant_hashes = {str(value).strip() for value in profile.get("linked_applicant_email_hashes") or [] if str(value).strip()}
        connected_user_ids.update(linked_users)
        connected_student_ids.update(linked_students)
        connected_external_subject_keys.update(linked_applicants)
        connected_applicant_hashes.update(linked_applicant_hashes)
        if len(linked_users) > 1 or len(linked_students) > 1 or len(linked_applicants) > 1 or len(linked_applicant_hashes) > 1:
            shared_device_count += 1
        seen_at = profile.get("last_seen_at")
        if isinstance(seen_at, datetime) and (latest_seen_at is None or seen_at > latest_seen_at):
            latest_seen_at = seen_at

        device_risk = _risk_level(
            float((len(linked_users) - 1 + len(linked_students) - 1 + len(linked_applicants) - 1) * 15),
            blocking=False,
        )
        nodes[device_key] = {
            "id": device_key,
            "node_type": "device",
            "label": f"Device {fingerprint[:10]}",
            "risk_level": device_risk,
            "metadata": {
                "session_count": int(profile.get("session_count") or 0),
                "linked_user_count": len(linked_users),
                "linked_student_count": len(linked_students),
                "linked_applicant_count": len(linked_applicants),
                "last_seen_at": seen_at,
            },
        }
        for linked_user_id in sorted(linked_users):
            node_key = f"user:{linked_user_id}"
            if node_key not in nodes:
                nodes[node_key] = {
                    "id": node_key,
                    "node_type": "user",
                    "label": f"User #{linked_user_id}",
                    "risk_level": models.FraudRiskLevel.LOW,
                    "metadata": {},
                }
            edges.append(
                {
                    "source": device_key,
                    "target": node_key,
                    "relation": "session_device",
                    "weight": float(profile.get("session_count") or 1),
                    "metadata": {
                        "shared_users": len(linked_users),
                        "shared_students": len(linked_students),
                    },
                }
            )
        for linked_student_id in sorted(linked_students):
            node_key = f"student:{linked_student_id}"
            if node_key not in nodes:
                nodes[node_key] = {
                    "id": node_key,
                    "node_type": "student",
                    "label": f"Student #{linked_student_id}",
                    "risk_level": models.FraudRiskLevel.LOW,
                    "metadata": {},
                }
            edges.append(
                {
                    "source": device_key,
                    "target": node_key,
                    "relation": "enrollment_device",
                    "weight": float(profile.get("session_count") or 1),
                    "metadata": {
                        "shared_users": len(linked_users),
                        "shared_students": len(linked_students),
                    },
                }
            )
        for linked_subject_key in sorted(linked_applicants):
            node_key = f"external:{linked_subject_key}"
            if normalized_applicant_email and linked_subject_key == normalized_subject_key:
                node_key = subject_key
            if node_key not in nodes:
                nodes[node_key] = {
                    "id": node_key,
                    "node_type": "applicant",
                    "label": linked_subject_key,
                    "risk_level": models.FraudRiskLevel.LOW,
                    "metadata": {},
                }
            edges.append(
                {
                    "source": device_key,
                    "target": node_key,
                    "relation": "signup_device",
                    "weight": float(profile.get("session_count") or 1),
                    "metadata": {
                        "shared_users": len(linked_users),
                        "shared_students": len(linked_students),
                        "shared_applicants": len(linked_applicants),
                    },
                }
            )

    other_users = connected_user_ids - ({int(user_id)} if user_id is not None else set())
    other_students = connected_student_ids - ({int(student_id)} if student_id is not None else set())
    other_subjects = connected_external_subject_keys - ({normalized_subject_key} if normalized_subject_key else set())
    summary = {
        "shared_device_count": int(shared_device_count),
        "connected_user_count": len(other_users),
        "connected_student_count": len(other_students),
        "connected_applicant_count": len(other_subjects),
        "latest_seen_at": latest_seen_at,
        "profile_count": len(profiles),
    }
    return {
        "subject_key": subject_key,
        "summary": summary,
        "nodes": list(nodes.values()),
        "edges": edges,
    }


def _serialize_artifact(
    artifact: models.IdentityVerificationArtifact,
) -> schemas.IdentityVerificationArtifactOut:
    return schemas.IdentityVerificationArtifactOut(
        id=artifact.id,
        artifact_type=artifact.artifact_type,
        media_object_key=artifact.media_object_key,
        media_url=signed_url_for_object(artifact.media_object_key),
        content_type=artifact.content_type,
        size_bytes=int(artifact.size_bytes or 0),
        checksum_sha256=artifact.checksum_sha256,
        verification_state=artifact.verification_state,
        document_match_score=artifact.document_match_score,
        face_match_confidence=artifact.face_match_confidence,
        liveness_passed=artifact.liveness_passed,
        note=artifact.note,
        extracted_identity=json.loads(artifact.extracted_identity_json or "{}"),
        created_at=artifact.created_at,
    )


def _persist_case_artifacts(
    db: Session,
    *,
    case: models.IdentityVerificationCase,
    artifact_uploads: Iterable[schemas.IdentityVerificationArtifactUpload] | None,
) -> list[models.IdentityVerificationArtifact]:
    uploads = list(artifact_uploads or [])
    if not uploads:
        return []

    retention_days = max(30, int(os.getenv("IDENTITY_EVIDENCE_RETENTION_DAYS", "365")))
    artifacts: list[models.IdentityVerificationArtifact] = []
    for item in uploads:
        media = store_data_url_object(
            db,
            owner_table="identity_verification_cases",
            owner_id=int(case.id),
            media_kind=f"identity-{str(item.artifact_type or 'artifact').strip().lower()}",
            data_url=item.data_url,
            retention_days=retention_days,
        )
        artifact = models.IdentityVerificationArtifact(
            case_id=case.id,
            artifact_type=str(item.artifact_type or "artifact").strip().lower(),
            media_object_key=media.object_key,
            content_type=media.content_type,
            size_bytes=int(media.size_bytes or 0),
            checksum_sha256=media.checksum_sha256,
            verification_state=str(item.verification_state or "submitted").strip().lower() or "submitted",
            document_match_score=item.document_match_score,
            face_match_confidence=item.face_match_confidence,
            liveness_passed=item.liveness_passed,
            note=item.note,
            extracted_identity_json=json.dumps(item.extracted_identity or {}, default=str),
        )
        db.add(artifact)
        artifacts.append(artifact)
    return artifacts


def _serialize_case(
    case: models.IdentityVerificationCase,
    signals: Iterable[models.IdentityRiskSignal],
    artifacts: Iterable[models.IdentityVerificationArtifact] | None = None,
) -> schemas.IdentityVerificationCaseOut:
    requested_checks = json.loads(case.requested_checks_json or "[]")
    completed_checks = json.loads(case.completed_checks_json or "[]")
    graph_summary = json.loads(case.graph_summary_json or "{}")
    evidence = json.loads(case.evidence_json or "{}")
    return schemas.IdentityVerificationCaseOut(
        id=case.id,
        workflow_key=case.workflow_key,
        subject_role=case.subject_role,
        auth_user_id=case.auth_user_id,
        student_id=case.student_id,
        faculty_id=case.faculty_id,
        applicant_email=case.applicant_email,
        external_subject_key=case.external_subject_key,
        status=case.status,
        risk_score=float(case.risk_score or 0.0),
        risk_level=case.risk_level,
        requested_checks=requested_checks,
        completed_checks=completed_checks,
        latest_reason=case.latest_reason,
        graph_summary=graph_summary,
        evidence=evidence,
        reviewed_by_user_id=case.reviewed_by_user_id,
        reviewed_at=case.reviewed_at,
        created_at=case.created_at,
        updated_at=case.updated_at,
        signals=[
            schemas.IdentityRiskSignalOut(
                id=signal.id,
                signal_type=signal.signal_type,
                severity=signal.severity,
                score_delta=float(signal.score_delta or 0.0),
                is_blocking=bool(signal.is_blocking),
                reason=signal.reason,
                evidence=json.loads(signal.evidence_json or "{}"),
                created_at=signal.created_at,
            )
            for signal in signals
        ],
        artifacts=[_serialize_artifact(artifact) for artifact in (artifacts or [])],
    )


def _persist_case_and_signals(
    db: Session,
    *,
    workflow_key: str,
    subject_role: str,
    auth_user_id: int | None,
    student_id: int | None,
    faculty_id: int | None,
    applicant_email: str | None,
    external_subject_key: str | None,
    requested_checks: list[str],
    completed_checks: list[str],
    graph_summary: dict[str, Any],
    evidence: dict[str, Any],
    signals: list[dict[str, Any]],
    artifact_uploads: Iterable[schemas.IdentityVerificationArtifactUpload] | None = None,
) -> schemas.IdentityVerificationCaseOut:
    score = float(sum(float(item.get("score_delta") or 0.0) for item in signals))
    blocking = any(bool(item.get("is_blocking")) for item in signals)
    risk_level = _risk_level(score, blocking=blocking)
    status = _status_for_risk(score, blocking=blocking)
    latest_reason = next((str(item.get("reason") or "").strip() for item in signals if item.get("reason")), None)

    case = models.IdentityVerificationCase(
        workflow_key=workflow_key,
        subject_role=subject_role,
        auth_user_id=auth_user_id,
        student_id=student_id,
        faculty_id=faculty_id,
        applicant_email=applicant_email,
        external_subject_key=external_subject_key,
        status=status,
        risk_score=score,
        risk_level=risk_level,
        requested_checks_json=json.dumps(requested_checks),
        completed_checks_json=json.dumps(completed_checks),
        latest_reason=latest_reason,
        graph_summary_json=json.dumps(graph_summary, default=str),
        evidence_json=json.dumps(evidence, default=str),
        updated_at=_utc_now(),
    )
    db.add(case)
    db.flush()

    orm_signals: list[models.IdentityRiskSignal] = []
    for item in signals:
        signal = models.IdentityRiskSignal(
            case_id=case.id,
            signal_type=str(item.get("signal_type") or "unknown"),
            severity=item.get("severity") or models.FraudRiskLevel.LOW,
            score_delta=float(item.get("score_delta") or 0.0),
            is_blocking=bool(item.get("is_blocking")),
            reason=str(item.get("reason") or "Signal raised"),
            evidence_json=json.dumps(item.get("evidence") or {}, default=str),
        )
        db.add(signal)
        orm_signals.append(signal)

    orm_artifacts = _persist_case_artifacts(
        db,
        case=case,
        artifact_uploads=artifact_uploads,
    )

    db.commit()
    db.refresh(case)
    for signal in orm_signals:
        db.refresh(signal)
    for artifact in orm_artifacts:
        db.refresh(artifact)

    payload = _serialize_case(case, orm_signals, orm_artifacts)
    mirror_document(
        "identity_verification_cases",
        payload.model_dump(mode="json"),
        upsert_filter={"id": case.id},
    )
    for signal in payload.signals:
        mirror_document(
            "identity_risk_signals",
            {
                "case_id": case.id,
                **signal.model_dump(mode="json"),
            },
            upsert_filter={"id": signal.id},
        )
    for artifact in payload.artifacts:
        mirror_document(
            "identity_verification_artifacts",
            {
                "case_id": case.id,
                **artifact.model_dump(mode="json"),
            },
            upsert_filter={"id": artifact.id},
        )
    publish_domain_event(
        "identity.case.updated",
        payload={
            "case_id": case.id,
            "workflow_key": case.workflow_key,
            "status": case.status.value,
            "risk_score": case.risk_score,
            "risk_level": case.risk_level.value,
            "student_id": case.student_id,
            "auth_user_id": case.auth_user_id,
        },
        scopes={"role:admin"},
        topics={"identity", "identity_shield"},
        source="identity_shield",
    )
    return payload


def run_student_enrollment_screening(db: Session, *, student_id: int) -> schemas.IdentityVerificationCaseOut:
    student = db.get(models.Student, student_id)
    if student is None:
        raise ValueError("Student not found")

    auth_user = db.query(models.AuthUser).filter(models.AuthUser.student_id == student.id).first()
    graph = build_subject_identity_graph(
        user_id=auth_user.id if auth_user else None,
        student_id=student.id,
    )

    signals: list[dict[str, Any]] = []
    if not student.registration_number:
        _append_signal(
            signals,
            signal_type="missing_registration_number",
            severity=models.FraudRiskLevel.MEDIUM,
            score_delta=12.0,
            reason="Registration number is missing for enrollment identity verification.",
        )
    if not student.profile_face_template_json:
        _append_signal(
            signals,
            signal_type="missing_profile_face_template",
            severity=models.FraudRiskLevel.HIGH,
            score_delta=32.0,
            reason="Profile face reference is missing.",
            blocking=True,
        )
    if not student.enrollment_video_template_json:
        _append_signal(
            signals,
            signal_type="missing_enrollment_video_template",
            severity=models.FraudRiskLevel.CRITICAL,
            score_delta=40.0,
            reason="Enrollment video/liveness template is missing.",
            blocking=True,
        )
    if auth_user is None:
        _append_signal(
            signals,
            signal_type="missing_auth_account",
            severity=models.FraudRiskLevel.MEDIUM,
            score_delta=16.0,
            reason="Student does not have an active auth account linked yet.",
        )
    elif not bool(auth_user.is_active):
        _append_signal(
            signals,
            signal_type="inactive_auth_account",
            severity=models.FraudRiskLevel.HIGH,
            score_delta=20.0,
            reason="Linked auth account is inactive.",
        )

    if student.parent_email:
        parent_email_count = (
            db.query(models.Student)
            .filter(models.Student.parent_email == student.parent_email)
            .count()
        )
        if parent_email_count >= 3:
            _append_signal(
                signals,
                signal_type="parent_email_reuse_cluster",
                severity=models.FraudRiskLevel.MEDIUM,
                score_delta=18.0,
                reason="Parent email is reused across multiple student profiles.",
                evidence={"linked_students": parent_email_count},
            )

    profile_template = None
    enrollment_template = None
    if student.profile_face_template_json:
        try:
            profile_template = json.loads(student.profile_face_template_json)
        except json.JSONDecodeError:
            profile_template = None
    if student.enrollment_video_template_json:
        try:
            enrollment_template = json.loads(student.enrollment_video_template_json)
        except json.JSONDecodeError:
            enrollment_template = None

    completed_checks: list[str] = []
    requested_checks: list[str] = []
    if profile_template:
        completed_checks.append("profile_face_photo")
    else:
        requested_checks.append("profile_face_photo")
    if enrollment_template:
        completed_checks.append("enrollment_video_liveness")
    else:
        requested_checks.append("enrollment_video_liveness")

    if profile_template and enrollment_template:
        similarity = compare_face_templates(profile_template, enrollment_template)
        evidence = {"template_similarity": round(float(similarity), 4)}
        min_threshold = _env_float("IDENTITY_ENROLLMENT_FACE_MATCH_MIN", 0.72)
        warn_threshold = _env_float("IDENTITY_ENROLLMENT_FACE_MATCH_WARN", 0.82)
        if similarity < min_threshold:
            _append_signal(
                signals,
                signal_type="profile_enrollment_face_mismatch",
                severity=models.FraudRiskLevel.CRITICAL,
                score_delta=45.0,
                reason="Enrollment video does not match the stored profile face reference.",
                evidence=evidence,
                blocking=True,
            )
        elif similarity < warn_threshold:
            _append_signal(
                signals,
                signal_type="profile_enrollment_face_low_similarity",
                severity=models.FraudRiskLevel.MEDIUM,
                score_delta=18.0,
                reason="Enrollment video similarity is lower than the trusted threshold.",
                evidence=evidence,
            )
        else:
            completed_checks.append("profile_vs_enrollment_match")

    shared_device_count = int(graph.get("summary", {}).get("shared_device_count") or 0)
    if shared_device_count > 0:
        requested_checks.append("device_review")
        _append_signal(
            signals,
            signal_type="shared_device_reuse",
            severity=models.FraudRiskLevel.HIGH if shared_device_count >= 2 else models.FraudRiskLevel.MEDIUM,
            score_delta=min(30.0, 12.0 * shared_device_count),
            reason="Linked account is reusing a device fingerprint seen on other campus identities.",
            evidence={"shared_device_count": shared_device_count},
        )

    evidence = {
        "student_email": student.email,
        "registration_number": student.registration_number,
        "section": student.section,
        "parent_email": _mask_email(student.parent_email),
    }
    return _persist_case_and_signals(
        db,
        workflow_key="enrollment_identity",
        subject_role="student",
        auth_user_id=auth_user.id if auth_user else None,
        student_id=student.id,
        faculty_id=None,
        applicant_email=None,
        external_subject_key=None,
        requested_checks=sorted(set(requested_checks)),
        completed_checks=sorted(set(completed_checks)),
        graph_summary=graph.get("summary", {}),
        evidence=evidence,
        signals=signals,
    )


def assess_applicant_risk(
    db: Session,
    payload: schemas.ApplicantRiskAssessmentRequest,
) -> schemas.IdentityVerificationCaseOut:
    normalized_email = str(payload.applicant_email or "").strip().lower()
    normalized_subject_key = str(payload.external_subject_key or normalized_email or "").strip().lower() or None
    suspicious_flags = [str(item or "").strip() for item in payload.suspicious_flags if str(item or "").strip()]
    signals: list[dict[str, Any]] = []
    requested_checks: list[str] = []
    completed_checks: list[str] = []

    mongo_db = get_mongo_db(required=False)
    fingerprint = observe_applicant_identity(
        mongo_db,
        applicant_email=normalized_email,
        external_subject_key=normalized_subject_key,
        device_id=payload.device_id,
        user_agent=payload.user_agent,
        ip_address=payload.ip_address,
    )

    existing_user = db.query(models.AuthUser).filter(models.AuthUser.email == normalized_email).first()
    if existing_user is None and mongo_db is not None and normalized_email:
        existing_user = mongo_db["auth_users"].find_one({"email": normalized_email}, {"id": 1})
    if existing_user is not None:
        existing_user_id = int(existing_user.id) if hasattr(existing_user, "id") else int(existing_user.get("id") or 0)
        _append_signal(
            signals,
            signal_type="existing_account_email",
            severity=models.FraudRiskLevel.HIGH,
            score_delta=24.0,
            reason="Applicant email already belongs to an existing campus account.",
            evidence={"auth_user_id": existing_user_id},
        )

    if not payload.registration_number:
        _append_signal(
            signals,
            signal_type="missing_registration_number",
            severity=models.FraudRiskLevel.MEDIUM,
            score_delta=10.0,
            reason="Applicant registration number was not supplied.",
        )
    else:
        completed_checks.append("registration_number")

    if payload.parent_email:
        duplicate_parent_count = (
            db.query(models.Student)
            .filter(models.Student.parent_email == payload.parent_email)
            .count()
        )
        if duplicate_parent_count >= 3:
            _append_signal(
                signals,
                signal_type="parent_email_reuse_cluster",
                severity=models.FraudRiskLevel.MEDIUM,
                score_delta=14.0,
                reason="Applicant parent email is already associated with several campus identities.",
                evidence={"linked_students": duplicate_parent_count},
            )
        completed_checks.append("parent_email")

    if payload.document_match_score is None:
        requested_checks.append("document_verification")
    else:
        completed_checks.append("document_verification")
        if payload.document_match_score < 0.65:
            _append_signal(
                signals,
                signal_type="document_match_low",
                severity=models.FraudRiskLevel.CRITICAL,
                score_delta=38.0,
                reason="Document verification score is below the accepted threshold.",
                evidence={"document_match_score": payload.document_match_score},
                blocking=True,
            )
        elif payload.document_match_score < 0.82:
            _append_signal(
                signals,
                signal_type="document_match_warn",
                severity=models.FraudRiskLevel.MEDIUM,
                score_delta=16.0,
                reason="Document verification score needs manual review.",
                evidence={"document_match_score": payload.document_match_score},
            )

    if payload.face_match_confidence is None:
        requested_checks.append("face_match")
    else:
        completed_checks.append("face_match")
        if payload.face_match_confidence < 0.72:
            _append_signal(
                signals,
                signal_type="face_match_low",
                severity=models.FraudRiskLevel.CRITICAL,
                score_delta=40.0,
                reason="Applicant face similarity is below the required threshold.",
                evidence={"face_match_confidence": payload.face_match_confidence},
                blocking=True,
            )
        elif payload.face_match_confidence < 0.84:
            _append_signal(
                signals,
                signal_type="face_match_warn",
                severity=models.FraudRiskLevel.MEDIUM,
                score_delta=18.0,
                reason="Applicant face similarity should be manually reviewed.",
                evidence={"face_match_confidence": payload.face_match_confidence},
            )

    if payload.liveness_passed is None:
        requested_checks.append("liveness_video")
    elif payload.liveness_passed is False:
        _append_signal(
            signals,
            signal_type="liveness_failed",
            severity=models.FraudRiskLevel.CRITICAL,
            score_delta=45.0,
            reason="Applicant liveness/video verification failed.",
            blocking=True,
        )
    else:
        completed_checks.append("liveness_video")

    if suspicious_flags:
        _append_signal(
            signals,
            signal_type="manual_suspicion_flags",
            severity=models.FraudRiskLevel.MEDIUM,
            score_delta=min(25.0, 8.0 * len(suspicious_flags)),
            reason="Applicant was submitted with explicit suspicion flags.",
            evidence={"flags": suspicious_flags},
        )

    graph = build_subject_identity_graph(
        applicant_email=normalized_email,
        external_subject_key=normalized_subject_key,
    )
    graph_summary: dict[str, Any] = dict(graph.get("summary", {}) or {})
    if fingerprint:
        graph_summary["device_fingerprint"] = fingerprint

    shared_device_count = int(graph_summary.get("shared_device_count") or 0)
    connected_users = int(graph_summary.get("connected_user_count") or 0)
    connected_students = int(graph_summary.get("connected_student_count") or 0)
    connected_applicants = int(graph_summary.get("connected_applicant_count") or 0)
    connected_total = connected_users + connected_students + connected_applicants
    if connected_total > 0 or shared_device_count > 0:
        _append_signal(
            signals,
            signal_type="device_reuse_cluster",
            severity=models.FraudRiskLevel.HIGH if connected_total >= 3 or shared_device_count >= 2 else models.FraudRiskLevel.MEDIUM,
            score_delta=min(30.0, float(max(1, connected_total + shared_device_count) * 9)),
            reason="Applicant device fingerprint is already linked to other campus identities or signup attempts.",
            evidence=graph_summary,
        )
        requested_checks.append("device_review")

    evidence = {
        "applicant_email": _mask_email(normalized_email),
        "claimed_role": payload.claimed_role,
        "parent_email": _mask_email(payload.parent_email),
        "document_reference_hash": _stable_hash(payload.document_reference),
        "device_fingerprint": fingerprint,
    }
    return _persist_case_and_signals(
        db,
        workflow_key="applicant_identity",
        subject_role="applicant",
        auth_user_id=(int(existing_user.id) if hasattr(existing_user, "id") else int(existing_user.get("id") or 0)) if existing_user else None,
        student_id=None,
        faculty_id=None,
        applicant_email=normalized_email,
        external_subject_key=normalized_subject_key,
        requested_checks=sorted(set(requested_checks)),
        completed_checks=sorted(set(completed_checks)),
        graph_summary=graph_summary,
        evidence=evidence,
        signals=signals,
        artifact_uploads=payload.evidence_uploads,
    )


def list_identity_cases(
    db: Session,
    *,
    status: models.IdentityVerificationStatus | None = None,
    student_id: int | None = None,
    applicant_email: str | None = None,
    workflow_key: str | None = None,
    limit: int = 50,
) -> list[schemas.IdentityVerificationCaseOut]:
    query = db.query(models.IdentityVerificationCase).order_by(models.IdentityVerificationCase.created_at.desc())
    if status is not None:
        query = query.filter(models.IdentityVerificationCase.status == status)
    if student_id is not None:
        query = query.filter(models.IdentityVerificationCase.student_id == student_id)
    if applicant_email:
        query = query.filter(models.IdentityVerificationCase.applicant_email == str(applicant_email).strip().lower())
    if workflow_key:
        query = query.filter(models.IdentityVerificationCase.workflow_key == workflow_key)
    cases = query.limit(max(1, min(200, limit))).all()
    results: list[schemas.IdentityVerificationCaseOut] = []
    for case in cases:
        signals = (
            db.query(models.IdentityRiskSignal)
            .filter(models.IdentityRiskSignal.case_id == case.id)
            .order_by(models.IdentityRiskSignal.created_at.asc())
            .all()
        )
        artifacts = (
            db.query(models.IdentityVerificationArtifact)
            .filter(models.IdentityVerificationArtifact.case_id == case.id)
            .order_by(models.IdentityVerificationArtifact.created_at.asc())
            .all()
        )
        results.append(_serialize_case(case, signals, artifacts))
    return results


def get_identity_case(db: Session, case_id: int) -> schemas.IdentityVerificationCaseOut | None:
    case = db.get(models.IdentityVerificationCase, case_id)
    if case is None:
        return None
    signals = (
        db.query(models.IdentityRiskSignal)
        .filter(models.IdentityRiskSignal.case_id == case.id)
        .order_by(models.IdentityRiskSignal.created_at.asc())
        .all()
    )
    artifacts = (
        db.query(models.IdentityVerificationArtifact)
        .filter(models.IdentityVerificationArtifact.case_id == case.id)
        .order_by(models.IdentityVerificationArtifact.created_at.asc())
        .all()
    )
    return _serialize_case(case, signals, artifacts)
