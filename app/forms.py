from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, FileField
from wtforms.validators import DataRequired
from flask_wtf.file import FileAllowed

class TicketForm(FlaskForm):
    title = StringField('Заголовок', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[DataRequired()])
    # status = SelectField('Статус', choices=[('Открыта', 'Открыта'), ('В работе', 'В работе'), ('Закрыта', 'Закрыта')], validators=[DataRequired()])
    files = FileField('Прикрепить файлы', validators=[FileAllowed(['jpg', 'png', 'pdf', 'txt'], 'Только изображения и документы!')])
    submit = SubmitField('Отправить')

