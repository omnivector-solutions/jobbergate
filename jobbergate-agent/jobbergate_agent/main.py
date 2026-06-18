import asyncio

from jobbergate_agent.utils.logging import logger
from jobbergate_agent.utils.scheduler import schedule_tasks, scheduler
from jobbergate_agent.utils.sentry import init_sentry


async def run_scheduler():
    """
    Start the scheduler, register all task plugins, then run until stopped.

    References:
        https://github.com/agronholm/apscheduler/blob/master/examples/
    """
    async with scheduler:
        await schedule_tasks(scheduler)
        await scheduler.run_until_stopped()


def main():
    logger.info("Starting Jobbergate-agent")
    init_sentry()
    with asyncio.Runner() as runner:
        try:
            runner.run(run_scheduler())
        except (KeyboardInterrupt, SystemExit):
            logger.info("Jobbergate-agent is shutting down...")
        except Exception as err:
            logger.critical(f"Unexpected error in main event loop: {err}", exc_info=True)
            raise
    logger.info("Jobbergate-agent has been stopped")

