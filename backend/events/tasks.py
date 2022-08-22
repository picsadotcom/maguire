from celery import Task
from celery.utils.log import get_task_logger

from maguire.celery import app


class DebitBatchCompleted(Task):
    """
    """
    name = "maguire.events.tasks.debit_batch_completed"
    tl = get_task_logger(__name__)

    def run(self, event_id, **kwargs):
        # trigger hook
        return "debit_batch_completed fired"


app.register_task(DebitBatchCompleted)
debit_batch_completed = DebitBatchCompleted()
