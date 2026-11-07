"""Seed the TrekSync development database with demo data.

Credentials match the README:
    admin@test.com / admin123
    staff@test.com / staff123
    trekker@test.com / trekker123

Run with: python seed.py
"""
from datetime import date, datetime

from app import app
from extensions import db
from models import User, UserRole, StaffProfile, Trek, Difficulty, TrekStatus, Booking, BookingStatus


def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # --- Users -----------------------------------------------------
        admin = User(
            username="admin",
            email="admin@test.com",
            role=UserRole.ADMIN.value,
            approved=True,
            active=True,
        )
        admin.set_password("admin123")

        staff = User(
            username="staff",
            email="staff@test.com",
            role=UserRole.STAFF.value,
            approved=True,
            active=True,
        )
        staff.set_password("staff123")

        guide_maya = User(
            username="guide_maya",
            email="guide_maya@test.com",
            role=UserRole.STAFF.value,
            approved=False,   # pending administrator approval
            active=True,
        )
        guide_maya.set_password("staff123")

        trekker = User(
            username="trekker",
            email="trekker@test.com",
            role=UserRole.TREKKER.value,
            approved=True,
            active=True,
        )
        trekker.set_password("trekker123")

        aria = User(
            username="aria",
            email="aria@test.com",
            role=UserRole.TREKKER.value,
            approved=True,
            active=True,
        )
        aria.set_password("trekker123")

        db.session.add_all([admin, staff, guide_maya, trekker, aria])
        db.session.flush()

        # --- Staff profile --------------------------------------------
        db.session.add(StaffProfile(
            user_id=staff.id,
            phone="9800000001",
            experience=6,
            emergency_contact="9800000011",
        ))

        # --- Treks -----------------------------------------------------
        annapurna_circuit = Trek(
            name="Annapurna Circuit",
            location="Manang, Nepal",
            difficulty=Difficulty.HARD,
            duration=14,
            max_slots=12,
            available_slots=12,
            description="A classic 14-day circuit crossing Thorong La pass with stunning mountain views.",
            start_date=date(2026, 11, 20),
            end_date=date(2026, 12, 4),
            status=TrekStatus.OPEN,
            staff_id=staff.id,
        )

        everest_bc = Trek(
            name="Everest Base Camp",
            location="Khumbu, Nepal",
            difficulty=Difficulty.MODERATE,
            duration=12,
            max_slots=10,
            available_slots=10,
            description="Trek to the foot of the world's highest mountain via Namche Bazaar.",
            start_date=date(2026, 12, 5),
            end_date=date(2026, 12, 17),
            status=TrekStatus.OPEN,
            staff_id=staff.id,
        )

        langtang = Trek(
            name="Langtang Valley Sunrise",
            location="Langtang, Nepal",
            difficulty=Difficulty.EASY,
            duration=5,
            max_slots=15,
            available_slots=15,
            description="A short and scenic valley trek perfect for first-time trekkers.",
            start_date=date(2026, 11, 4),
            end_date=date(2026, 11, 9),
            status=TrekStatus.OPEN,
        )

        annapurna_bc = Trek(
            name="Annapurna Base Camp",
            location="Kaski, Nepal",
            difficulty=Difficulty.MODERATE,
            duration=9,
            max_slots=8,
            available_slots=8,
            description="Journey into the Annapurna Sanctuary amphitheatre of peaks.",
            start_date=date(2026, 12, 20),
            end_date=date(2026, 12, 29),
            status=TrekStatus.OPEN,
            staff_id=staff.id,
        )

        manaslu = Trek(
            name="Manaslu Circuit",
            location="Gorkha, Nepal",
            difficulty=Difficulty.HARD,
            duration=16,
            max_slots=10,
            available_slots=10,
            description="A remote 16-day circuit around the eighth highest mountain on earth.",
            start_date=date(2026, 10, 26),
            end_date=date(2026, 11, 11),
            status=TrekStatus.OPEN,
            staff_id=staff.id,
        )

        db.session.add_all([
            annapurna_circuit, everest_bc, langtang, annapurna_bc, manaslu,
        ])
        db.session.flush()

        # --- Bookings --------------------------------------------------
        bookings = [
            Booking(
                user_id=trekker.id,
                trek_id=annapurna_circuit.id,
                status=BookingStatus.BOOKED,
                booking_date=datetime(2026, 10, 21, 13, 56, 36),
            ),
            Booking(
                user_id=aria.id,
                trek_id=annapurna_circuit.id,
                status=BookingStatus.BOOKED,
                booking_date=datetime(2026, 10, 21, 13, 56, 36),
            ),
            Booking(
                user_id=aria.id,
                trek_id=annapurna_bc.id,
                status=BookingStatus.BOOKED,
                booking_date=datetime(2026, 10, 21, 13, 56, 36),
            ),
            Booking(
                user_id=trekker.id,
                trek_id=langtang.id,
                status=BookingStatus.CANCELLED,
                booking_date=datetime(2026, 10, 21, 13, 56, 36),
            ),
        ]
        db.session.add_all(bookings)

        # Keep slot counts consistent with confirmed bookings.
        annapurna_circuit.available_slots = annapurna_circuit.max_slots - 2
        annapurna_bc.available_slots = annapurna_bc.max_slots - 1

        db.session.commit()
        print("Seeded: 5 users, 5 treks, 4 bookings.")


if __name__ == "__main__":
    seed()
