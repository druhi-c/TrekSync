from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from extensions import db
from forms.trek_forms import StaffTrekUpdateForm
from models import Booking, BookingStatus, Trek, TrekStatus
from utils.decorators import staff_required
from flask import Blueprint


staff = Blueprint("staff", __name__, url_prefix="/staff")


def _assigned_trek_or_404(trek_id):
    trek = db.session.get(Trek, trek_id)
    if trek is None:
        abort(404)
    if trek.staff_id != current_user.id:
        abort(403)
    return trek


@staff.route("/dashboard")
@login_required
@staff_required
def dashboard():
    treks = Trek.query.filter_by(staff_id=current_user.id).order_by(Trek.start_date).all()
    participant_counts = {
        trek.id: Booking.query.filter_by(trek_id=trek.id, status=BookingStatus.BOOKED).count()
        for trek in treks
    }
    return render_template("staff/dashboard.html", treks=treks, participant_counts=participant_counts)


@staff.route("/treks/<int:trek_id>/edit", methods=["GET", "POST"])
@login_required
@staff_required
def edit_trek(trek_id):
    trek = _assigned_trek_or_404(trek_id)
    form = StaffTrekUpdateForm()
    booked_count = Booking.query.filter_by(trek_id=trek.id, status=BookingStatus.BOOKED).count()

    if form.validate_on_submit():
        if form.available_slots.data > trek.max_slots - booked_count:
            form.available_slots.errors.append("Available slots exceed the trek capacity after confirmed bookings.")
        else:
            trek.available_slots = form.available_slots.data
            trek.status = TrekStatus(form.status.data)
            db.session.commit()
            flash("Trek details updated.", "success")
            return redirect(url_for("staff.dashboard"))
    elif not form.is_submitted():
        form.available_slots.data = trek.available_slots
        form.status.data = trek.status.value

    return render_template("staff/edit_trek.html", form=form, trek=trek, booked_count=booked_count)


@staff.route("/treks/<int:trek_id>/participants")
@login_required
@staff_required
def participants(trek_id):
    trek = _assigned_trek_or_404(trek_id)
    bookings = Booking.query.filter_by(trek_id=trek.id).order_by(Booking.booking_date.desc()).all()
    return render_template("staff/participants.html", trek=trek, bookings=bookings)
