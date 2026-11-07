from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User, UserRole
from forms.auth_forms import RegistrationForm, LoginForm
from utils.decorators import admin_required, staff_required, trekker_required

auth = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth"
)

def redirect_by_role(user):
    if user.role == UserRole.ADMIN.value:
        return redirect(url_for("admin.dashboard"))
    elif user.role == UserRole.STAFF.value:
        return redirect(url_for("staff.dashboard"))
    else:
        return redirect(url_for("trekker.dashboard"))


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect_by_role(current_user)
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            flash("Invalid email or password.", "danger")
            return render_template("login.html", form=form)

        if not user.check_password(form.password.data):
            flash("Invalid email or password.", "danger")
            return render_template("login.html", form=form)

        if not user.active:
            flash("Your account has been deactivated.", "danger")
            return render_template("login.html", form=form)

        if user.role == UserRole.STAFF.value and not user.approved:
            flash("Your staff account is awaiting administrator approval.", "warning")
            return render_template("login.html", form=form)

        login_user(user, remember=form.remember_me.data)
        return redirect_by_role(user)

    return render_template("login.html", form=form)


@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect_by_role(current_user)
    form = RegistrationForm()
    if form.validate_on_submit():
        role_val = form.role.data
        is_trekker = (role_val == UserRole.TREKKER.value)
        approved = True if is_trekker else False

        user = User(
            username=form.username.data,
            email=form.email.data,
            role=role_val,
            approved=approved,
            active=True
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        if is_trekker:
            flash("Registration successful! You can now log in.", "success")
        else:
            flash("Registration successful! Your staff account is awaiting admin approval.", "warning")

        return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("auth.login"))


@auth.route("/dashboard/admin")
@login_required
@admin_required
def admin_dashboard():
    return f"Admin Dashboard - Welcome {current_user.username}"


@auth.route("/dashboard/staff")
@login_required
@staff_required
def staff_dashboard():
    return f"Staff Dashboard - Welcome {current_user.username}"


@auth.route("/dashboard/trekker")
@login_required
@trekker_required
def trekker_dashboard():
    return f"Trekker Dashboard - Welcome {current_user.username}"
