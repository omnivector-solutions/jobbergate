"""
Provide functions to interact with persistent data storage.
"""
import re
import typing

import asyncpg
import databases
import databases.core
import fastapi
import pydantic
import sqlalchemy
from asyncpg.exceptions import UniqueViolationError
from fastapi.exceptions import HTTPException
from loguru import logger
from sqlalchemy import Column, Enum, or_
from sqlalchemy.sql.expression import BooleanClauseList, Case, UnaryExpression
from starlette import status
from yarl import URL

from jobbergate_api.config import settings

INTEGRITY_CHECK_EXCEPTIONS = (UniqueViolationError,)


def build_db_url(force_test: bool = False) -> str:
    """
    Build a database url based on settings.

    If the ``DEPLOY_ENV`` setting is "TEST" or if the ``force_test`` is passed, build from the test database
    settings.
    """
    is_test = force_test or settings.DEPLOY_ENV.lower() == "test"
    prefix = "TEST_" if is_test else ""

    return str(
        URL.build(
            scheme="postgresql",
            user=getattr(settings, f"{prefix}DATABASE_USER"),
            password=getattr(settings, f"{prefix}DATABASE_PSWD"),
            host=getattr(settings, f"{prefix}DATABASE_HOST"),
            port=getattr(settings, f"{prefix}DATABASE_PORT"),
            path="/{}".format(getattr(settings, f"{prefix}DATABASE_NAME")),
        )
    )


database = databases.Database(build_db_url(), force_rollback=settings.DEPLOY_ENV.lower() == "test")


def render_sql(query) -> str:
    """
    Render a sqlalchemy query into a string for debugging.
    """
    return query.compile(dialect=database._backend._dialect, compile_kwargs={"literal_binds": True})


def search_clause(
    search_terms: str,
    searchable_fields: typing.List[Column],
) -> BooleanClauseList:
    """
    Create search clause across searchable fields with search terms.
    """
    return or_(*[field.ilike(f"%{term}%") for field in searchable_fields for term in search_terms.split()])


def _build_enum_sort_clause(sort_column: Column, sort_ascending: bool) -> Case:
    """
    Build a Case statement that can be used as a sort clause for an enum column.

    SQLAlchemy will not sort enums alphabetically by default, but rather by creation order.  Thus, we have to
    force alphabetical sorting using a CASE clause. The logic here is strange. Basically, we have to provide a
    lookup and then a string sort value. If sort order is ascending, each enum value's sort value is itself.
    Otherwise, the sort value is it's opposite in the list. For example::

        Given the enum (GAMMA, ALPHA, DELTA, BETA)
        The default sort order used by SQLAlchemy is (GAMMA, ALPHA, DELTA, BETA)
        Mapping used for ascending sort: {ALPHA: ALPHA, BETA: BETA, DELTA: DELTA, GAMMA: GAMMA}
        Mapping used for descending sort: {ALPHA: GAMMA, BETA: DELTA, DELTA: BETA, GAMMA: ALPHA}

    To understand this more fully, start with this SO question: https://stackoverflow.com/a/23618085/642511
    """
    assert isinstance(sort_column.type, Enum)
    sorted_values = sorted(sort_column.type.enums)
    sort_tuple = zip(sorted_values, sorted_values if sort_ascending else reversed(sorted_values))
    return sqlalchemy.case(dict(sort_tuple), value=sort_column)


def sort_clause(
    sort_field: str,
    sortable_fields: typing.List[Column],
    sort_ascending: bool,
) -> typing.Union[Column, UnaryExpression, Case]:
    """
    Create a sort clause given a sort field, the list of sortable fields, and a sort_ascending flag.
    """
    sort_field_names = [f.name for f in sortable_fields]
    try:
        index = sort_field_names.index(sort_field)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sorting column requested: {sort_field}. Must be one of {sort_field_names}",
        )
    sort_column: typing.Union[Column, UnaryExpression, Case] = sortable_fields[index]
    if isinstance(sort_column, Column) and isinstance(sort_column.type, sqlalchemy.Enum):
        sort_column = _build_enum_sort_clause(sort_column, sort_ascending)
    elif not sort_ascending:
        sort_column = sort_column.desc()
    return sort_column


def handle_fk_error(
    _: fastapi.Request,
    err: asyncpg.exceptions.ForeignKeyViolationError,
):
    """
    Unpack metadata from a ForeignKeyViolationError and return a 409 response.
    """
    FK_DETAIL_RX = r"DETAIL:  Key \(id\)=\((?P<pk_id>\d+)\) is still referenced from table \"(?P<table>\w+)\""
    matches = re.search(FK_DETAIL_RX, str(err), re.MULTILINE)
    (table, pk_id) = (None, None)
    if matches:
        table = matches.group("table")
        pk_id = matches.group("pk_id")

    logger.error(f"Delete failed due to foreign-key constraint: {table=} {pk_id=}")

    return fastapi.responses.JSONResponse(
        status_code=fastapi.status.HTTP_409_CONFLICT,
        content=dict(
            detail=dict(
                message="Delete failed due to foreign-key constraint",
                table=table,
                pk_id=pk_id,
            ),
        ),
    )


T = typing.TypeVar("T", bound=pydantic.BaseModel)


async def fetch_instance(id: int, table: sqlalchemy.Table, model: typing.Type[T]) -> T:
    """
    Fetch a single frow from a table by its id and unpack it into a response model.
    """
    query = table.select(table.c.id == id)
    result = await database.fetch_one(query)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Could not find {table.name} instance with id {id}")
    return model.parse_obj(result)
