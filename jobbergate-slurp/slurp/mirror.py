"""
Provides logic for mirroring application data from nextgen db to nextgen mirror.
"""
from loguru import logger


def reflect(nextgen_db, mirror_db):
    """
    Mirrors data from nextgen database.
    """
    logger.debug("Mirroring applications from nextgen database")
    with nextgen_db.copy("copy applications to stdout") as copy_out:
        with mirror_db.copy("copy applications from stdin") as copy_in:
            copy_out.write(copy_in.read())
    logger.debug("Finished mirroring applications")
