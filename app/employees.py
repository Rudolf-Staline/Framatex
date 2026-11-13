"""Employee account representation shared by authentication and administration."""
from .access import is_admin
from .models import User


def user_out(u: User):
    return {"id": u.id, "email": u.email, "name": u.name, "active": u.active, "roles": [r.name for r in u.roles], "admin": is_admin(u)}
