import logging

from rq import Worker
from task_system_common.logging import configure_logging
from task_system_common.queue import get_redis_connection
from task_system_common.settings import get_settings


def main() -> None:
    configure_logging()
    settings = get_settings()
    logger = logging.getLogger(__name__)

    redis = get_redis_connection(settings)
    worker = Worker([settings.rq_queue_name], connection=redis)
    logger.info("Starting worker")
    worker.work(with_scheduler=True, burst=settings.rq_worker_burst)


if __name__ == "__main__":
    main()
