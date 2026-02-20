import asyncio

from jobbergate_agent.utils.logging import logger
from jobbergate_agent.utils.scheduler import init_scheduler, scheduler, shut_down_scheduler
from jobbergate_agent.utils.sentry import init_sentry


async def helper():
    """
    Based on example from the scheduler documentation:

    https://github.com/agronholm/apscheduler/blob/3.x/examples/schedulers/asyncio_.py
    """
    init_scheduler()
    while True:
        await asyncio.sleep(1000)


def main():
    logger.info("Starting Jobbergate-agent")
    init_sentry()
    with asyncio.Runner() as runner:
        try:
            runner.run(helper())
        except (KeyboardInterrupt, SystemExit):
            logger.info("Jobbergate-agent is shutting down...")
        except Exception as err:
            logger.critical(f"Unexpected error in main event loop: {err}", exc_info=True)
            raise
        finally:
            shut_down_scheduler(scheduler, wait=False)
    logger.info("Jobbergate-agent has been stopped")
