from typing import List

import sqlalchemy
from pydantic import BaseModel

from jobbergateapi2.storage import database


async def insert_objects(objects: List[BaseModel], table: sqlalchemy.Table):
    """
    Perform a database insertion for the objects passed as the argument, into
    the specified table
    """
    ModelType = type(objects[0])
    await database.execute_many(
        query=table.insert(), values=[obj.dict() for obj in objects]
    )
    fetched = await database.fetch_all(table.select())
    return [ModelType.parse_obj(o) for o in fetched]
