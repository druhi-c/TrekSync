from enum import Enum

from extensions import db


class Difficulty(Enum):
    EASY = "Easy"
    MODERATE = "Moderate"
    HARD = "Hard"


class TrekStatus(Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    OPEN = "Open"
    CLOSED = "Closed"
    STARTED = "Started"
    ONGOING = "Ongoing"
    COMPLETED = "Completed"


class Trek(db.Model):
    __tablename__ = "treks"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False
    )

    location = db.Column(
        db.String(100),
        nullable=False
    )

    difficulty = db.Column(
        db.Enum(Difficulty),
        nullable=False
    )

    duration = db.Column(
        db.Integer,
        nullable=False
    )

    available_slots = db.Column(
        db.Integer,
        nullable=False
    )

    max_slots = db.Column(
    db.Integer,
    nullable=False
    )

    description = db.Column(
        db.Text
    )

    start_date = db.Column(
        db.Date,
        nullable=False
    )

    end_date = db.Column(
        db.Date,
        nullable=False
    )

    status = db.Column(
        db.Enum(TrekStatus),
        nullable=False,
        default=TrekStatus.PENDING
    )

    staff_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    assigned_staff = db.relationship(
        "User",
        back_populates="assigned_treks"
    )

    bookings = db.relationship(
        "Booking",
        back_populates="trek",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Trek {self.name}>"
