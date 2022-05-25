import importlib

from django.conf import settings

from celery import Task
from celery.utils.log import get_task_logger

from maguire.celery import app
from .models import Debit


tl = get_task_logger(__name__)


class TQueuePending(Task):
    """
    Task that queues pending debits on provider
    """
    name = "maguire.debits.tasks.t_queue_pending"

    def run(self):
        tl.info("Queue pending debits")

        tl.info(". Setting up provider")
        debit_provider = settings.DEBIT_PROVIDER
        debit_package = settings.DEBIT_PACKAGE
        module = importlib.import_module(debit_provider, debit_package)
        provider = getattr(module, debit_package)()
        provider.config = settings.DEBIT_CONFIG
        provider.setup_provider()

        tl.info(". Preparing the debits list")
        debits = Debit.objects.filter(
            status="pending",
            load_attempts__lt=int(settings.DEBIT_LOAD_ATTEMPTS)
        )

        debits_list = list(debits.values_list('id', flat=True))

        tl.info(". Loading debits")
        results = provider.load_debits(debits_list)
        tl.info(". %s" % (results,))

        return "Queued {} pending debit(s)".format(len(debits_list))


app.register_task(TQueuePending)
t_queue_pending = TQueuePending()
