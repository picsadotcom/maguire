from rolepermissions.roles import AbstractUserRole


class Admin(AbstractUserRole):
    available_permissions = {
        'create_all': True,
        'read_all': True,
        'update_all': True,
        'delete_all': True,
        'list_all': True,
    }


class ReadOnly(AbstractUserRole):
    available_permissions = {
        'create_all': False,
        'read_all': True,
        'update_all': False,
        'delete_all': False,
        'list_all': True,
    }


class DebitAdmin(AbstractUserRole):
    """ used for debit admins """
    available_permissions = {
        'create_debit': True,
        'read_debit': True,
        'update_debit': True,
        'delete_debit': True,
        'list_debit': True
    }


class CreditAdmin(AbstractUserRole):
    """ used for credit admins """
    available_permissions = {
        'create_credit': True,
        'read_credit': True,
        'update_credit': True,
        'delete_credit': True,
        'list_credit': True
    }
