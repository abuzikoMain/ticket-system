from celery import shared_task
from models import db, Ticket, File
import os
from datetime import datetime

@shared_task
def create_ticket_task(ticket_data, file_paths):
    # Создаем новый объект заявки
    new_ticket = Ticket(
        created_at=datetime.now(),
        title=ticket_data['title'],
        description=ticket_data['description'],
        status="Открыта",
        pc_name=ticket_data['pc_name'],
        ip_address=ticket_data['ip_address'],
        is_new=True
    )
    
    # Сохраняем заявку в базе данных
    db.session.add(new_ticket)
    db.session.commit()  # Здесь мы фиксируем изменения, чтобы получить ID

    # Создание уникального каталога для файлов заявки
    ticket_folder = os.path.join('uploads', str(new_ticket.id))  # Убедитесь, что путь правильный
    os.makedirs(ticket_folder, exist_ok=True)  # Создаем каталог, если он не существует

    # Обработка загруженных файлов
    for file_path in file_paths:
        # Сохраняем информацию о файле в базе данных
        filename = os.path.basename(file_path)
        new_file = File(filename=filename, ticket_id=new_ticket.id)
        db.session.add(new_file)

    db.session.commit()  # Фиксируем изменения в базе данных


@shared_task
def update_ticket_task(ticket_id, updated_data):
    ticket = Ticket.query.get(ticket_id)
    if ticket:
        for key, value in updated_data.items():
            setattr(ticket, key, value)
        db.session.commit()
