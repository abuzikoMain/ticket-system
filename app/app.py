from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from datetime import datetime
from forms import TicketForm
from models import db, User, Ticket, Role, File, Message
from config import Config
import getpass
import os

app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = 'uploads'  # Папка для загрузки файлов
# celery = make_celery(app)
db.init_app(app)

# Создание папки для загрузки, если она не существует
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('admin'))
        else:
            flash('Неверное имя пользователя или пароль')
    return render_template('login.html')

@app.after_request
def add_header(response):
    response.cache_control.max_age = 31536000  # Устанавливаем время кэширования в секундах (1 год)
    return response

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin():
    if current_user.role.name != 'admin':
        return "Доступ запрещен", 403

    # Получаем номер страницы из параметров запроса, по умолчанию 1
    page = request.args.get('page', 1, type=int)
    tickets = Ticket.query.order_by(Ticket.created_at.desc()).paginate(page=page, per_page=15, error_out=False)  # Сортируем по дате создания

    # Обновляем статус новых заявок
    for ticket in tickets.items:
        ticket.is_new = False
    db.session.commit()

    return render_template('admin.html', tickets=tickets)



@app.route('/ticket/<int:ticket_id>', methods=['GET', 'POST'])
def view_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)

    # Проверяем, что заявка принадлежит текущему пользователю или администратору
    user_ip = request.remote_addr
    user_pc_name = getpass.getuser()
    if ticket.ip_address != user_ip and ticket.pc_name != user_pc_name and current_user.role.name != 'admin':
        return "Доступ запрещен", 403

    # Обновляем состояние заявки на "не новая"
    if current_user.is_authenticated:
        if current_user.role.name == 'admin' and ticket.is_new:
            ticket.is_new = False
            db.session.commit()

    if request.method == 'POST':
        content = request.form['content']
        new_message = Message(ticket_id=ticket.id, ip_address=user_ip, pc_name=user_pc_name, content=content)
        db.session.add(new_message)
        db.session.commit()
        flash('Сообщение отправлено!')
        return redirect(url_for('view_ticket', ticket_id=ticket.id))

    messages = Message.query.filter_by(ticket_id=ticket.id).all()
    return render_template('view_ticket.html', ticket=ticket, messages=messages)



@app.route('/ticket', methods=['GET', 'POST'])
def ticket():
    form = TicketForm()
    if form.validate_on_submit():
        new_ticket = Ticket(
            created_at=datetime.now(),
            title=form.title.data,
            description=form.description.data,
            status="Открыта",
            pc_name=getpass.getuser(),
            ip_address=request.remote_addr,
            is_new=True  # Устанавливаем флаг новой заявки
        )
        db.session.add(new_ticket)
        db.session.commit()

        # Создание уникального каталога для файлов заявки
        ticket_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(new_ticket.id))
        os.makedirs(ticket_folder, exist_ok=True)  # Создаем каталог, если он не существует

        # Обработка загрузки файлов
        if form.files.data:
            files = request.files.getlist(form.files.name)  # Получаем список загруженных файлов
            for file in files:
                if file:
                    filename = file.filename
                    file_path = os.path.join(ticket_folder, filename)  # Сохраняем файл в уникальном каталоге
                    file.save(file_path)  # Сохраняем файл на сервере

                    # Сохраняем информацию о файле в базе данных
                    new_file = File(filename=filename, ticket_id=new_ticket.id)
                    db.session.add(new_file)

        db.session.commit()
        flash('Заявка успешно создана!')
        return redirect(url_for('ticket'))
    return render_template('ticket_form.html', form=form)

@app.route('/check_new_tickets')
@login_required
def check_new_tickets():
    if current_user.role.name != 'admin':
        return "Доступ запрещен", 403

    new_tickets = Ticket.query.filter_by(is_new=True).all()
    tickets_data = [{'id': ticket.id, 'title': ticket.title} for ticket in new_tickets]
    return {'new_tickets': tickets_data}


@app.route('/update_ticket/<int:ticket_id>', methods=['POST'])
@login_required
def update_ticket(ticket_id):
    if current_user.role.name != 'admin':
        return "Доступ запрещен", 403

    ticket = Ticket.query.get_or_404(ticket_id)
    new_status = request.form.get('status')

    # Обновление статуса и соответствующих дат
    ticket.status = new_status
    if new_status == 'В работе' and ticket.received_at is None:
        ticket.received_at = datetime.now()  # Устанавливаем дату получения
    elif new_status == 'Закрыта' and ticket.closed_at is None:
        if ticket.received_at is None:
            ticket.received_at = datetime.now()            
        ticket.closed_at = datetime.now()  # Устанавливаем дату закрытия

    db.session.commit()
    flash('Статус заявки обновлен!')
    return redirect(url_for('admin'))

@app.route('/my_tickets')
def my_tickets():
    # Получаем IP-адрес и имя ПК текущего пользователя
    user_ip = request.remote_addr
    user_pc_name = getpass.getuser()

    # Находим все заявки, соответствующие IP-адресу и имени ПК
    page = request.args.get('page', 1, type=int)
    tickets = Ticket.query.order_by(Ticket.created_at.desc()).paginate(page=page, per_page=15, error_out=False)  # Сортируем по дате создания

    return render_template('my_tickets.html', tickets=tickets)

@app.route('/edit_ticket/<int:ticket_id>', methods=['GET', 'POST'])
def edit_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)

    # Проверяем, что заявка принадлежит текущему пользователю
    user_ip = request.remote_addr
    user_pc_name = getpass.getuser()
    if ticket.ip_address != user_ip or ticket.pc_name != user_pc_name:
        return "Доступ запрещен", 403

    form = TicketForm()
    if form.validate_on_submit():
        ticket.title = form.title.data
        ticket.description = form.description.data
        # ticket.status = form.status.data
        db.session.commit()
        flash('Заявка успешно обновлена!')
        return redirect(url_for('my_tickets'))

    # Заполняем форму текущими данными заявки
    form.title.data = ticket.title
    form.description.data = ticket.description
    # form.status.data = ticket.status
    return render_template('ticket_form.html', form=form)


@app.route('/uploads/<int:ticket_id>/<filename>')
def download_file(ticket_id, filename):
    # Создаем путь к каталогу, где хранятся файлы для данной заявки
    ticket_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(ticket_id))
    
    # Проверяем, существует ли файл
    return send_from_directory(ticket_folder, filename, as_attachment=True)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создание всех таблиц
    app.run(debug=True)

