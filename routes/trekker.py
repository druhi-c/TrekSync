from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, update

from extensions import db
from forms.trek_forms import TrekSearchForm
from models import Booking, BookingStatus, Difficulty, Trek, TrekStatus
from utils.decorators import trekker_required


trekker = Blueprint("trekker", __name__, url_prefix="/trekker")


@trekker.route("/dashboard")
@login_required
@trekker_required
def dashboard():
    form = TrekSearchForm(request.args, meta={"csrf": False})
    treks_query = Trek.query.filter_by(status=TrekStatus.OPEN).order_by(Trek.start_date)
    if form.validate():
        if form.query.data:
            term = f"%{form.query.data.strip()}%"
            treks_query = treks_query.filter(or_(Trek.name.ilike(term), Trek.location.ilike(term)))
        if form.difficulty.data:
            treks_query = treks_query.filter_by(difficulty=Difficulty(form.difficulty.data))
        if form.location.data:
            treks_query = treks_query.filter(Trek.location.ilike(f"%{form.location.data.strip()}%"))

    booked_trek_ids = {
        booking.trek_id
        for booking in Booking.query.filter_by(user_id=current_user.id, status=BookingStatus.BOOKED).all()
    }
    return render_template("trekker/dashboard.html", form=form, treks=treks_query.all(), booked_trek_ids=booked_trek_ids)


@trekker.route("/treks/<int:trek_id>/book", methods=["POST"])
@login_required
@trekker_required
def book_trek(trek_id):
    trek = db.session.get(Trek, trek_id)
    if trek is None:
        flash("That trek no longer exists.", "danger")
        return redirect(url_for("trekker.dashboard"))

    existing_booking = Booking.query.filter_by(user_id=current_user.id, trek_id=trek.id, status=BookingStatus.BOOKED).first()
    if existing_booking:
        flash("You already have an active booking for this trek.", "warning")
        return redirect(url_for("trekker.dashboard"))

    result = db.session.execute(
        update(Trek)
        .where(Trek.id == trek.id, Trek.status == TrekStatus.OPEN, Trek.available_slots > 0)
        .values(available_slots=Trek.available_slots - 1)
    )
    if result.rowcount != 1:
        db.session.rollback()
        flash("This trek is closed or no longer has available slots.", "warning")
        return redirect(url_for("trekker.dashboard"))

    db.session.add(Booking(user_id=current_user.id, trek_id=trek.id, status=BookingStatus.BOOKED))
    db.session.commit()
    flash("Your trek has been booked successfully.", "success")
    return redirect(url_for("trekker.bookings"))


@trekker.route("/bookings")
@login_required
@trekker_required
def bookings():
    user_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_date.desc()).all()
    return render_template("trekker/bookings.html", bookings=user_bookings)


@trekker.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required
@trekker_required
def cancel_booking(booking_id):
    booking = Booking.query.filter_by(id=booking_id, user_id=current_user.id).first_or_404()
    if booking.status != BookingStatus.BOOKED:
        flash("Only active bookings can be cancelled.", "warning")
        return redirect(url_for("trekker.bookings"))

    booking.status = BookingStatus.CANCELLED
    if booking.trek.status != TrekStatus.COMPLETED and booking.trek.available_slots < booking.trek.max_slots:
        booking.trek.available_slots += 1
    db.session.commit()
    flash("Your booking has been cancelled.", "success")
    return redirect(url_for("trekker.bookings"))
