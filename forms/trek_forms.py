from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional, ValidationError

from models import Difficulty, TrekStatus


class TrekForm(FlaskForm):
    name = StringField("Trek name", validators=[DataRequired(), Length(max=100)])
    location = StringField("Location", validators=[DataRequired(), Length(max=100)])
    difficulty = SelectField("Difficulty", choices=[(item.value, item.value) for item in Difficulty], validators=[DataRequired()])
    duration = IntegerField("Duration (days)", validators=[InputRequired(), NumberRange(min=1, max=60)])
    max_slots = IntegerField("Maximum slots", validators=[InputRequired(), NumberRange(min=1, max=500)])
    available_slots = IntegerField("Available slots", validators=[InputRequired(), NumberRange(min=0, max=500)])
    start_date = DateField("Start date", validators=[DataRequired()], format="%Y-%m-%d")
    end_date = DateField("End date", validators=[DataRequired()], format="%Y-%m-%d")
    status = SelectField("Status", choices=[(item.value, item.value) for item in TrekStatus], validators=[DataRequired()])
    staff_id = SelectField("Assigned staff", coerce=int, validators=[Optional()])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Save trek")

    def validate_end_date(self, field):
        if self.start_date.data and field.data and field.data < self.start_date.data:
            raise ValidationError("End date must be on or after the start date.")

    def validate_available_slots(self, field):
        if self.max_slots.data is not None and field.data is not None and field.data > self.max_slots.data:
            raise ValidationError("Available slots cannot exceed maximum slots.")


class StaffTrekUpdateForm(FlaskForm):
    available_slots = IntegerField("Available slots", validators=[InputRequired(), NumberRange(min=0, max=500)])
    status = SelectField("Trek status", choices=[
        (TrekStatus.OPEN.value, TrekStatus.OPEN.value),
        (TrekStatus.CLOSED.value, TrekStatus.CLOSED.value),
        (TrekStatus.STARTED.value, TrekStatus.STARTED.value),
        (TrekStatus.ONGOING.value, TrekStatus.ONGOING.value),
        (TrekStatus.COMPLETED.value, TrekStatus.COMPLETED.value),
    ], validators=[DataRequired()])
    submit = SubmitField("Update trek")


class TrekSearchForm(FlaskForm):
    query = StringField("Search", validators=[Optional(), Length(max=100)])
    difficulty = SelectField("Difficulty", choices=[("", "All difficulties")] + [(item.value, item.value) for item in Difficulty], validators=[Optional()])
    location = StringField("Location", validators=[Optional(), Length(max=100)])
    submit = SubmitField("Search")
