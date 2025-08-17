import pytest
from anyio import wait_all_tasks_blocked

from interview_helper.tests.shared import FakeWebSocket

from interview_helper.context_manager.concurrent_websocket import ConcurrentWebSocket
from interview_helper.context_manager.messages import Envelope, TranscriptionMessage

pytestmark = pytest.mark.anyio


async def test_send_and_receive_message():
    # Setup
    ws = FakeWebSocket()

    await ws.accept()

    cws = ConcurrentWebSocket(already_accepted_ws=ws)
    await cws.start()

    msg = TranscriptionMessage(session_id="sess1", text="hello world")
    await cws.send_message(msg)
    await wait_all_tasks_blocked()  # Let writer run

    assert len(ws.sent_messages) == 1
    assert Envelope.model_validate_json(ws.sent_messages[0]).message == msg

    ws.enqueue(Envelope(message=msg).model_dump_json())
    recv_msg = await cws.receive_message()

    assert recv_msg == msg

    await cws.aclose()
    await wait_all_tasks_blocked()  # Let writer close

    assert ws.closed is True
