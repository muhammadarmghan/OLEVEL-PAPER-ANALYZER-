from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange


class ReviewForm(FlaskForm):
    text = TextAreaField("Question text", validators=[DataRequired()])
    marks = IntegerField("Marks", validators=[NumberRange(min=0, max=100)])
    topic_id = SelectField("Topic", coerce=int)
    approve = SubmitField("Approve")
    reject = SubmitField("Reject")
