"""Tests for the non-smartphone SMS-reply path (Build Plan Phase 3).

Written after a live test against the running stack caught a real bug:
inbound_sms read a SQLAlchemy attribute off ``prompt`` *after* its
session had already closed (DetachedInstanceError) — every reply
was silently marked resolved without ever advancing the work order.
These lock that fix in. Uses asyncio.run() rather than pytest-asyncio,
matching this suite's existing convention (see test_pipeline.py).
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.lifecycle import append_lifecycle_event
from database.models import Base, PendingSmsPrompt, WorkOrderRecord


@pytest.fixture
def sms_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr("api.notifications.SessionLocal", session_factory)
    monkeypatch.setattr("api.workorders.SessionLocal", session_factory)
    monkeypatch.setattr("api.notifications.AFRICASTALKING_INBOUND_TOKEN", "")
    return session_factory


def _seed_dispatched_work_order(session_factory, work_order_id="WO-1", phone="+2547010500"):
    session = session_factory()
    session.add(WorkOrderRecord(id=work_order_id, equipment_id="VALVE-201", technician_id="TECH-105", part_number="Seal"))
    session.flush()
    append_lifecycle_event(session, work_order_id=work_order_id, to_status="PENDING_APPROVAL", actor_id="sys", actor_role="internal")
    append_lifecycle_event(session, work_order_id=work_order_id, from_status="PENDING_APPROVAL", to_status="APPROVED", actor_id="eng", actor_role="engineer")
    append_lifecycle_event(session, work_order_id=work_order_id, from_status="APPROVED", to_status="DISPATCHED", actor_id="eng", actor_role="engineer")
    now = datetime.now(timezone.utc)
    session.add(PendingSmsPrompt(
        phone_number=phone,
        work_order_id=work_order_id,
        expected_codes="1,3",
        code_to_status=json.dumps({"1": "IN_PROGRESS", "3": "COMPLETED"}),
        sent_at=now,
        expires_at=now + timedelta(hours=24),
    ))
    session.commit()
    session.close()


def test_matched_reply_advances_work_order_status(sms_db):
    from api.notifications import inbound_sms
    from database.lifecycle import current_work_order_status

    _seed_dispatched_work_order(sms_db)

    result = asyncio.run(inbound_sms(from_="+2547010500", text="1", token=None))

    assert result["status"] == "applied"
    assert result["work_order"]["status"] == "IN_PROGRESS"

    session = sms_db()
    assert current_work_order_status(session, "WO-1") == "IN_PROGRESS"
    prompt = session.query(PendingSmsPrompt).filter(PendingSmsPrompt.work_order_id == "WO-1").first()
    # Not yet resolved — "1" (Accept) isn't the terminal reply, so this
    # same prompt must still match a later "3" (Complete). See
    # test_accept_then_complete_both_match_the_same_prompt.
    assert prompt.resolved_at is None
    session.close()


def test_accept_then_complete_both_match_the_same_prompt(sms_db):
    """Regression test: resolving the prompt after the *first* reply
    ("1"=Accept) would make the *second* reply ("3"=Complete) — sent
    potentially hours later, once the job is actually done — unmatched.
    Both must land against the same PendingSmsPrompt row."""
    from api.notifications import inbound_sms
    from database.lifecycle import current_work_order_status

    _seed_dispatched_work_order(sms_db)

    accept_result = asyncio.run(inbound_sms(from_="+2547010500", text="1", token=None))
    assert accept_result["status"] == "applied"
    assert accept_result["work_order"]["status"] == "IN_PROGRESS"

    complete_result = asyncio.run(inbound_sms(from_="+2547010500", text="3", token=None))
    assert complete_result["status"] == "applied"
    assert complete_result["work_order"]["status"] == "COMPLETED"

    session = sms_db()
    assert current_work_order_status(session, "WO-1") == "COMPLETED"
    prompt = session.query(PendingSmsPrompt).filter(PendingSmsPrompt.work_order_id == "WO-1").first()
    assert prompt.resolved_at is not None  # resolved only now, after the terminal reply
    session.close()


def test_duplicate_accept_reply_is_a_clean_conflict_not_a_crash(sms_db):
    """Replying "1" twice: the prompt is still open (not resolved until
    "3"), so the second "1" matches again — but the underlying lifecycle
    transition map has no DISPATCHED-style self-loop for an
    already-IN_PROGRESS work order, so this surfaces as an ordinary 409,
    not an unhandled exception."""
    from fastapi import HTTPException

    from api.notifications import inbound_sms

    _seed_dispatched_work_order(sms_db)

    asyncio.run(inbound_sms(from_="+2547010500", text="1", token=None))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(inbound_sms(from_="+2547010500", text="1", token=None))
    assert exc_info.value.status_code == 409


def test_reply_from_unknown_phone_is_unmatched(sms_db):
    from api.notifications import inbound_sms

    _seed_dispatched_work_order(sms_db)

    result = asyncio.run(inbound_sms(from_="+254700000000", text="1", token=None))

    assert result["status"] == "unmatched"


def test_ambiguous_reply_does_not_guess(sms_db):
    from api.notifications import inbound_sms

    _seed_dispatched_work_order(sms_db, work_order_id="WO-1", phone="+2547010500")
    _seed_dispatched_work_order(sms_db, work_order_id="WO-2", phone="+2547010500")

    result = asyncio.run(inbound_sms(from_="+2547010500", text="1", token=None))

    assert result["status"] == "ambiguous"


def test_wrong_inbound_token_is_rejected(sms_db, monkeypatch):
    from fastapi import HTTPException

    from api.notifications import inbound_sms

    monkeypatch.setattr("api.notifications.AFRICASTALKING_INBOUND_TOKEN", "secret")
    _seed_dispatched_work_order(sms_db)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(inbound_sms(from_="+2547010500", text="1", token="wrong"))
    assert exc_info.value.status_code == 403
