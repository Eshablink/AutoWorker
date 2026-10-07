import os
from uuid import uuid4

from redis import Redis

from packages.worker.broker import RedisStreamsTaskBroker


def test_real_redis_stream_round_trip():
    client = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    stream = f"autoworker:test:{uuid4()}"
    group = f"test-group:{uuid4()}"
    broker = RedisStreamsTaskBroker(client, stream_name=stream, group_name=group)
    task_id = uuid4()

    message_id = broker.publish(task_id)
    message = broker.consume("ci-worker", block_ms=1000)

    assert message is not None
    assert message.message_id == message_id
    assert message.task_id == task_id

    broker.acknowledge(message)
