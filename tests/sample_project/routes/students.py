from fastapi import APIRouter
from services.enrollment import enroll_student, withdraw_student, suspend_student

router = APIRouter()


@router.post("/students")
def create_student(name: str, grade: int, email: str):
    """API endpoint: enroll a new student."""
    return enroll_student(name, grade, email)


@router.delete("/students/{student_id}")
def remove_student(student_id: int):
    return withdraw_student(student_id)


@router.patch("/students/{student_id}/suspend")
def suspend(student_id: int):
    return suspend_student(student_id)


@router.get("/students/{student_id}")
def get_student(student_id: int):
    # NOTE: intentionally not wired to a service yet -- routes calling db directly
    # is a smell your graph should surface once edges are built (Phase 3).
    return {"id": student_id}
