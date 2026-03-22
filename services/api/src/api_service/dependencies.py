from collections.abc import Iterator

from redis import Redis
from rq import Queue
from task_system_common.queue import get_queue, get_redis_connection
from task_system_common.settings import get_settings


def get_redis() -> Iterator[Redis]:
    settings = get_settings()
    client = get_redis_connection(settings)
    try:
        yield client
    finally:
        client.close()
def get_task_queue() -> Queue:
    settings = get_settings()
    return get_queue(settings)
