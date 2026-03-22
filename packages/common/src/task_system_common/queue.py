from redis import Redis
from rq import Queue

from task_system_common.settings import Settings


def get_redis_connection(settings: Settings) -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=False)


def get_queue(settings: Settings) -> Queue:
    return Queue(name=settings.rq_queue_name, connection=get_redis_connection(settings))

