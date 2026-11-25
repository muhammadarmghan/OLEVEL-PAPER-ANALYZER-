from datetime import date

from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError


class PlanForm(FlaskForm):
    subject_id = SelectField("Subject", coerce=int)
    name = StringField("Plan name", validators=[DataRequired(), Length(3, 100)])
    exam_date = DateField("Exam date", validators=[DataRequired()])
    top_n = IntegerField("Number of topics", default=10, validators=[NumberRange(3, 20)])
    submit = SubmitField("Save plan")

    def validate_exam_date(self, field):
        if field.data <= date.today():
            raise ValidationError("The exam date must be in the future.")


class FeedbackForm(FlaskForm):
    rating = IntegerField("Rating (1-5)", validators=[NumberRange(1, 5)])
    comment = TextAreaField("Comment", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Send feedback")
