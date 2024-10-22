from flask_wtf import FlaskForm
from wtforms import Form, StringField, SelectField, BooleanField, PasswordField
from wtforms.validators import DataRequired, Email, Optional, Length, ValidationError
from models import Role, Team, TeamColor, User
import pytz
from wtforms import validators

class PhoneNumberField(StringField):
    def process_formdata(self, valuelist):
        if valuelist:
            self.data = ''.join(filter(str.isdigit, valuelist[0]))
        else:
            self.data = ''

    def pre_validate(self, form):
        if self.data and len(self.data) != 10:
            raise ValidationError('Phone number must be 10 digits.')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    work_phone = PhoneNumberField('Work Phone', validators=[Optional()])
    mobile_phone = PhoneNumberField('Mobile Phone', validators=[Optional()])
    timezone = SelectField('Timezone', choices=[(tz, tz) for tz in pytz.all_timezones], validators=[DataRequired()])
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    team_id = SelectField('Team', coerce=int, validators=[Optional()])
    is_active = BooleanField('Active')
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.role_id.choices = [(role.id, role.name) for role in Role.query.all()]
        self.team_id.choices = [(0, 'No Team')] + [(team.id, team.name) for team in Team.query.all()]
    
class TeamForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    manager_id = SelectField('Manager', validators=[DataRequired()], coerce=int)
    color_id = SelectField('Color', validators=[DataRequired()], coerce=int)

    def __init__(self, *args, **kwargs):
        super(TeamForm, self).__init__(*args, **kwargs)
        self.manager_id.choices = [(user.id, user.username) for user in User.query.filter(User.role_id.in_([1, 2])).all()]
        self.color_id.choices = [(color.id, color.hex_value) for color in TeamColor.query.all()]
