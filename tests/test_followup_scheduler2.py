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


def test_schedule_followups_creates_jobs(tmp_path):
    app = FakeApplication()
    # Prepare followups for event
    seq = [
        {'delay_hours': 0.001, 'template': 'PAYMENT_REMINDER_1'},
        {'delay_hours': 0.002, 'template': 'PAYMENT_REMINDER_2'},
    ]
    # Save followups (writes to config/followups.json)
    save_followups(admin_id=1, event_key='TEST_EVENT', seq=seq)

    # Monkeypatch event_registry to include TEST_EVENT
    from src.utils import event_registry
    event_registry.EVENT_KEYS.add('TEST_EVENT')

    # Schedule followups
    schedule_followups(app, chat_id=12345, event_key='TEST_EVENT', context_vars={'order_id': 999})

    # Expect two scheduled jobs
    scheduled = app.job_queue.scheduled
    assert any('followup:12345:TEST_EVENT:0' in k for k in scheduled.keys())
    assert len(scheduled) == 2

    # Calling schedule_followups again should not duplicate jobs
    schedule_followups(app, chat_id=12345, event_key='TEST_EVENT', context_vars={'order_id': 999})
    assert len(app.job_queue.scheduled) == 2


def test_schedule_followups_no_followups(tmp_path):
    app = FakeApplication()
    # Ensure no followups exist for UNKNOWN_EVENT
    schedule_followups(app, chat_id=1, event_key='UNKNOWN_EVENT', context_vars={})
    assert len(app.job_queue.scheduled) == 0
