from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, InputRequired
from utils import get_countries

country_list = get_countries()

class ReusableForm(FlaskForm):
    name = StringField('Recipe Name:', validators=[DataRequired(message="*Required"), Length(min=1, max=100)])
    description = TextAreaField('Description:', validators=[DataRequired(message="*Required"), Length(min=1, max=500)])
    instruction1 = StringField('Step 1:', validators=[DataRequired(message="*Required"), Length(min=1, max=500)])
    ingredient1 = StringField('Ingredient 1:', validators=[DataRequired(message="*Required"), Length(min=1, max=100)])
    allergen1 = StringField('Allergen 1:', validators=[Length(max=100)])  # Không bắt buộc
    country = SelectField('Country of Origin', choices=country_list, validators=[InputRequired(message="*Required")])
    is_public = BooleanField('Make this recipe public', default=True)
    submit = SubmitField('Submit')

class Username(FlaskForm):
    username = StringField('Username:', validators=[DataRequired(message="*Required"), Length(min=1, max=50)])

class Search(FlaskForm):
    search = StringField('Search:', validators=[DataRequired(message="*Required"), Length(min=1, max=100)])