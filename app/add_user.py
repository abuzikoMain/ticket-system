from app import app, db
from models import User, Role

def create_roles():
    admin_role = Role(name='admin')
    user_role = Role(name='user')
    db.session.add(admin_role)
    db.session.add(user_role)
    db.session.commit()
    return admin_role, user_role

def create_user(username, password, role):
    user = User(username=username, password=password, role_id=role.id)
    db.session.add(user)
    db.session.commit()
    print(f'Пользователь {username} с ролью {role.name} успешно создан!')

if __name__ == '__main__':
    with app.app_context():
        # Создание ролей, если они еще не существуют
        if not Role.query.first():
            admin_role, user_role = create_roles()
        else:
            admin_role = Role.query.filter_by(name='admin').first()
            user_role = Role.query.filter_by(name='user').first()

        # Создание администратора
        create_user('admin', 'admin', admin_role)

        # Создание обычного пользователя (по желанию)
        create_user('user1', 'user_password', user_role)
