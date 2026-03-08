from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import CurrentUser, require_roles
from ..database import get_db
from ..identity_shield import (
    assess_applicant_risk,
    build_subject_identity_graph,
    get_identity_case,
    list_identity_cases,
    run_student_enrollment_screening,
)

router = APIRouter(prefix="/identity-shield", tags=["Fraud And Identity Shield"])

_ADMIN_DEPENDENCY = require_roles(models.UserRole.ADMIN, models.UserRole.OWNER)


@router.post(
    "/screenings/enrollment/students/{student_id}",
    response_model=schemas.IdentityVerificationCaseOut,
)
def run_enrollment_identity_screening(
    student_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_ADMIN_DEPENDENCY),
):
    try:
        return run_student_enrollment_screening(db, student_id=student_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/screenings/applicants",
    response_model=schemas.IdentityVerificationCaseOut,
)
def run_applicant_identity_screening(
    payload: schemas.ApplicantRiskAssessmentRequest,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_ADMIN_DEPENDENCY),
):
    return assess_applicant_risk(db, payload)


@router.get("/cases", response_model=list[schemas.IdentityVerificationCaseOut])
def get_identity_cases(
    status: models.IdentityVerificationStatus | None = Query(default=None),
    student_id: int | None = Query(default=None),
    workflow_key: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_ADMIN_DEPENDENCY),
):
    return list_identity_cases(
        db,
        status=status,
        student_id=student_id,
        workflow_key=workflow_key,
        limit=limit,
    )


@router.get("/cases/{case_id}", response_model=schemas.IdentityVerificationCaseOut)
def get_identity_case_by_id(
    case_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(_ADMIN_DEPENDENCY),
):
    case = get_identity_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Identity verification case not found")
    return case


@router.get("/graph/students/{student_id}", response_model=schemas.IdentityGraphOut)
def get_student_identity_graph(
    student_id: int,
    _: CurrentUser = Depends(_ADMIN_DEPENDENCY),
):
    graph = build_subject_identity_graph(student_id=student_id)
    return schemas.IdentityGraphOut(**graph)


@router.get("/graph/users/{user_id}", response_model=schemas.IdentityGraphOut)
def get_user_identity_graph(
    user_id: int,
    _: CurrentUser = Depends(_ADMIN_DEPENDENCY),
):
    graph = build_subject_identity_graph(user_id=user_id)
    return schemas.IdentityGraphOut(**graph)
