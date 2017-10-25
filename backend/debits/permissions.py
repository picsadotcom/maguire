from rolepermissions.permissions import register_object_checker
from maguire.roles import Admin


@register_object_checker()
def access_debit(role, user, debit):
    if role in (Admin, ):
        return True

    return False
