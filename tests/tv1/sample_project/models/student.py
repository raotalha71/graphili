from dataclasses import dataclass


@dataclass
class Student:
    """Represents a single enrolled student."""
    id: int
    name: str
    grade: int
    email: str


@dataclass
class Teacher:
    id: int
    name: str
    subject: str
