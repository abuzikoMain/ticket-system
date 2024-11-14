from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory
from flask_login import login_user, login_required, logout_user, current_user
from datetime import datetime
import getpass
import os

from .extensions import db, login_manager
from .models import User, Ticket, Message, File
from .forms import TicketForm

main = Blueprint('main', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@main.after_request
def add_header(response):
    response.cache_control.max_age = 31536000  # Устанавливаем время кэширования в секундах (1 год)
    return response

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('main.admin'))
        else:
            flash('Неверное имя пользователя или пароль')
    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/admin')
@login_required
def admin():
    if current_user.role.name != 'admin':
        return "Доступ запрещен", 403

    page = request.args.get('page', 1, type=int)
    tickets = Ticket.query.order_by(Ticket.created_at.desc()).paginate(page=page, per_page=15, error_out=False)

    for ticket in tickets.items:
        ticket.is_new = False
    db.session.commit()

    return render_template('admin.html', tickets=tickets)


@main.route('/ticket/<int:ticket_id>', methods=['GET', 'POST'])
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



@main.route('/ticket', methods=['GET', 'POST'])
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
        ticket_folder = os.path.join(main.config['UPLOAD_FOLDER'], str(new_ticket.id))
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

@main.route('/check_new_tickets')
@login_required
def check_new_tickets():
    if current_user.role.name != 'admin':
        return "Доступ запрещен", 403

    new_tickets = Ticket.query.filter_by(is_new=True).all()
    tickets_data = [{'id': ticket.id, 'title': ticket.title} for ticket in new_tickets]
    return {'new_tickets': tickets_data}


@main.route('/update_ticket/<int:ticket_id>', methods=['POST'])
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

@main.route('/my_tickets')
def my_tickets():
    # Получаем IP-адрес и имя ПК текущего пользователя
    user_ip = request.remote_addr
    user_pc_name = getpass.getuser()

    # Находим все заявки, соответствующие IP-адресу и имени ПК
    page = request.args.get('page', 1, type=int)
    tickets = Ticket.query.order_by(Ticket.created_at.desc()).paginate(page=page, per_page=15, error_out=False)  # Сортируем по дате создания

    return render_template('my_tickets.html', tickets=tickets)

@main.route('/edit_ticket/<int:ticket_id>', methods=['GET', 'POST'])
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


@main.route('/uploads/<int:ticket_id>/<filename>')
def download_file(ticket_id, filename):
    # Создаем путь к каталогу, где хранятся файлы для данной заявки
    ticket_folder = os.path.join(main.config['UPLOAD_FOLDER'], str(ticket_id))
    
    # Проверяем, существует ли файл
    return send_from_directory(ticket_folder, filename, as_attachment=True)

@main.route('/')
def index():
    return render_template('index.html')
# Остальные маршруты можно добавить аналогично
