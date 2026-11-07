from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

from extensions import db
from forms.trek_forms import TrekForm
from models import Booking, Difficulty, Trek, TrekStatus, User, UserRole
from utils.decorators import admin_required


admin = Blueprint("admin", __name__, url_prefix="/admin")


def _staff_choices():
    staff_members = User.query.filter_by(role=UserRole.STAFF.value, active=True, approved=True).order_by(User.username).all()
    return [(0, "Unassigned")] + [(member.id, member.username) for member in staff_members]


def _populate_trek_form(form, trek):
    form.staff_id.choices = _staff_choices()
    if not form.is_submitted():
        form.name.data = trek.name
        form.location.data = trek.location
        form.difficulty.data = trek.difficulty.value
        form.duration.data = trek.duration
        form.max_slots.data = trek.max_slots
        form.available_slots.data = trek.available_slots
        form.start_date.data = trek.start_date
        form.end_date.data = trek.end_date
        form.status.data = trek.status.value
        form.staff_id.data = trek.staff_id or 0
        form.description.data = trek.description


def _apply_trek_form(trek, form):
    trek.name = form.name.data.strip()
    trek.location = form.location.data.strip()
    trek.difficulty = Difficulty(form.difficulty.data)
    trek.duration = form.duration.data
    trek.max_slots = form.max_slots.data
    trek.available_slots = form.available_slots.data
    trek.start_date = form.start_date.data
    trek.end_date = form.end_date.data
    trek.status = TrekStatus(form.status.data)
    trek.staff_id = form.staff_id.data or None
    trek.description = form.description.data.strip() if form.description.data else None


@admin.route("/dashboard")
@login_required
@admin_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        total_treks=Trek.query.count(),
        total_users=User.query.filter_by(role=UserRole.TREKKER.value).count(),
        total_staff=User.query.filter_by(role=UserRole.STAFF.value).count(),
        total_bookings=Booking.query.count(),
    )


@admin.route("/treks")
@login_required
@admin_required
def treks():
    return render_template("admin/treks.html", treks=Trek.query.order_by(Trek.start_date).all())


@admin.route("/treks/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_trek():
    form = TrekForm()
    form.staff_id.choices = _staff_choices()
    if form.validate_on_submit():
        trek = Trek()
        _apply_trek_form(trek, form)
        db.session.add(trek)
        db.session.commit()
        flash("Trek created successfully.", "success")
        return redirect(url_for("admin.treks"))
    return render_template("admin/trek_form.html", form=form, heading="Create trek")


@admin.route("/treks/<int:trek_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_trek(trek_id):
    trek = db.session.get(Trek, trek_id)
    if trek is None:
        return "Trek not found", 404
    form = TrekForm()
    _populate_trek_form(form, trek)
    if form.validate_on_submit():
        _apply_trek_form(trek, form)
        db.session.commit()
        flash("Trek updated successfully.", "success")
        return redirect(url_for("admin.treks"))
    return render_template("admin/trek_form.html", form=form, heading="Edit trek", trek=trek)


@admin.route("/treks/<int:trek_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_trek(trek_id):
    trek = db.session.get(Trek, trek_id)
    if trek is None:
        return "Trek not found", 404
    db.session.delete(trek)
    db.session.commit()
    flash("Trek deleted successfully.", "success")
    return redirect(url_for("admin.treks"))


@admin.route("/staff")
@login_required
@admin_required
def staff():
    staff_members = User.query.filter_by(role=UserRole.STAFF.value).order_by(User.username).all()
    return render_template("admin/staff.html", staff_members=staff_members)


@admin.route("/staff/<int:user_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve_staff(user_id):
    staff_member = User.query.filter_by(id=user_id, role=UserRole.STAFF.value).first_or_404()
    staff_member.approved = True
    db.session.commit()
    flash(f"{staff_member.username} has been approved.", "success")
    return redirect(url_for("admin.staff"))


@admin.route("/staff/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_staff_active(user_id):
    staff_member = User.query.filter_by(id=user_id, role=UserRole.STAFF.value).first_or_404()
    staff_member.active = not staff_member.active
    db.session.commit()
    flash(f"{staff_member.username}'s access has been updated.", "success")
    return redirect(url_for("admin.staff"))


@admin.route("/users")
@login_required
@admin_required
def users():
    trekkers = User.query.filter_by(role=UserRole.TREKKER.value).order_by(User.username).all()
    return render_template("admin/users.html", trekkers=trekkers)


@admin.route("/bookings")
@login_required
@admin_required
def bookings():
    all_bookings = Booking.query.order_by(Booking.booking_date.desc()).all()
    return render_template("admin/bookings.html", bookings=all_bookings)
