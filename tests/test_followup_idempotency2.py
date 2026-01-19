import pytest
from types import SimpleNamespace
from src.utils.followup_manager import save_followups
from src.utils.event_dispatcher import schedule_followups


class FakeJobQueue:
    def __init__(self):
        self.scheduled = {}

    def get_jobs_by_name(self, name):
        return [self.scheduled[name]] if name in self.scheduled else []

    def run_once(self, callback, delay, name=None, data=None):
        # record the job without executing
        self.scheduled[name] = {'callback': callback, 'delay': delay, 'data': data}
        return self.scheduled[name]


class FakeApplication(SimpleNamespace):
    def __init__(self):
        super().__init__()
        self.job_queue = FakeJobQueue()


def test_schedule_followups_idempotent_with_different_contexts(tmp_path):
    app = FakeApplication()

    seq = [
        {'delay_hours': 0.001, 'template': 'PAYMENT_REMINDER_1'},
    ]
    save_followups(admin_id=1, event_key='IDEMP_EVENT', seq=seq)

    from src.utils import event_registry
    event_registry.EVENT_KEYS.add('IDEMP_EVENT')

    # Schedule with first context_vars
    schedule_followups(app, chat_id=5555, event_key='IDEMP_EVENT', context_vars={'order_id': 1})
    assert len(app.job_queue.scheduled) == 1

    # Schedule again with different context_vars - should NOT create duplicate jobs
    schedule_followups(app, chat_id=5555, event_key='IDEMP_EVENT', context_vars={'order_id': 2})
    assert len(app.job_queue.scheduled) == 1
