from models.student import Student


def enroll_student(name: str, grade: int, email: str) -> Student:
    """Creates a new student record and saves it."""
    student = Student(id=generate_id(), name=name, grade=grade, email=email)
    save_student(student)
    return student


def generate_id() -> int:
    import random
    return random.randint(1000, 9999)


def save_student(student: Student) -> None:
    print(f"Saving student {student.name} to db...")


def withdraw_student(student_id: int) -> bool:
    """Removes a student record. Structurally near-identical to enroll flow below."""
    ok = delete_from_db(student_id)
    return ok


def delete_from_db(student_id: int) -> bool:
    print(f"Deleting student {student_id} from db...")
    return True


# --- intentionally near-duplicate logic for testing similarity detection later ---
def suspend_student(student_id: int) -> bool:
    ok = delete_from_db(student_id)
    return ok
