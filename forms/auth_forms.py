from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Regexp
from models import User, UserRole

class RegistrationForm(FlaskForm):
    """Registration form for trekkers and trek staff."""
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=50, message="Username must be between 3 and 50 characters."),
            Regexp(
                r"^[A-Za-z0-9_]+$",
                message="Username may contain only letters, numbers and underscores."
            )
        ]
    )
    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email(message="Invalid email address."),
            Length(max=120)
        ]
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, max=64, message="Password must be at least 8 characters long.")
        ]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match.")
        ]
    )
    role = SelectField(
        "Role",
        choices=[
            (UserRole.TREKKER.value, "Trekker"),
            (UserRole.STAFF.value, "Trek Staff")
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField("Register")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("Username is already taken. Please choose another one.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("Email is already registered. Please choose another one.")


class LoginForm(FlaskForm):
    """Login form for users."""
    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email(message="Invalid email address.")
        ]
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired()
        ]
    )
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Log In")
