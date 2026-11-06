from packages.shared.types import User


def paginate(items, page, per_page):
    start = page * per_page
    return items[start:start + per_page]


def list_users(users, page=1, per_page=2):
    return [u.name for u in paginate(users, page, per_page)]


def get_user(users, user_id):
    for u in users:
        if u.id == user_id:
            return u
    return None


def make_user(id, name, email):
    return User(id=id, name=name, email=email, display_name=name)
