import asyncio

from jobbergate_agent.utils.logging import logger
from jobbergate_agent.utils.scheduler import init_scheduler, shut_down_scheduler
from jobbergate_agent.utils.sentry import init_sentry


def main():
    logger.info("Starting Jobbergate-agent")
    init_sentry()
    scheduler = init_scheduler()

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        shut_down_scheduler(scheduler)


if __name__ == "__main__":
    main()
