from enum import Enum
from datetime import datetime

from extensions import db


class BookingStatus(Enum):
    BOOKED = "Booked"
    CANCELLED = "Cancelled"
    COMPLETED = "Completed"

class PaymentStatus(Enum):
    PENDING = "Pending"
    PAID = "Paid"
    REFUNDED = "Refunded"


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    trek_id = db.Column(
        db.Integer,
        db.ForeignKey("treks.id"),
        nullable=False
    )

    booking_date = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    status = db.Column(
        db.Enum(BookingStatus),
        default=BookingStatus.BOOKED,
        nullable=False
    )

    payment_status = db.Column(
        db.Enum(PaymentStatus),
        default=PaymentStatus.PENDING,
        nullable=False
    )

    user = db.relationship(
        "User",
        back_populates="bookings"
    )

    trek = db.relationship(
        "Trek",
        back_populates="bookings"
    )

    def __repr__(self):
        return f"<Booking User:{self.user_id} Trek:{self.trek_id}>"