"""
Provide functions to interact with persistent data storage.
"""
import re
import typing
from dataclasses import dataclass
from typing import AsyncIterator, Dict

import asyncpg
import fastapi
import pydantic
from armasec.token_security import PermissionMode
from asyncpg.exceptions import UniqueViolationError
from fastapi import Depends
from fastapi.exceptions import HTTPException
from loguru import logger
from sqlalchemy import Column, Enum, String, Table, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.sql.expression import BooleanClauseList, Case, UnaryExpression
from starlette import status
from yarl import URL

from jobbergate_api.config import settings
from jobbergate_api.security import IdentityPayload, lockdown_with_identity

INTEGRITY_CHECK_EXCEPTIONS = (UniqueViolationError,)


def build_db_url(
    override_db_name: typing.Optional[str] = None,
    force_test: bool = False,
    asynchronous: bool = True,
) -> str:
    """
    Build a database url based on settings.

    If ``force_test`` is set, build from the test database settings.
    If ``asynchronous`` is set, use asyncpg.
    If ``override_db_name`` replace the database name in the settings with the supplied value.
    """
    prefix = "TEST_" if force_test else ""
    db_user = getattr(settings, f"{prefix}DATABASE_USER")
    db_password = getattr(settings, f"{prefix}DATABASE_PSWD")
    db_host = getattr(settings, f"{prefix}DATABASE_HOST")
    db_port = getattr(settings, f"{prefix}DATABASE_PORT")
    db_name = getattr(settings, f"{prefix}DATABASE_NAME") if override_db_name is None else override_db_name
    db_path = "/{}".format(db_name)
    db_scheme = "postgresql+asyncpg" if asynchronous else "postgresql"

    return str(
        URL.build(
            scheme=db_scheme,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            path=db_path,
        )
    )


class EngineFactory:
    """
    Provide a factory class that creates engines and keeps track of them in an engine mapping.

    This is used for multi-tenancy and database URL creation at request time.
    """

    engine_map: Dict[str, AsyncEngine]

    def __init__(self):
        """
        Initialize the EngineFactory.
        """
        self.engine_map = dict()

    async def cleanup(self):
        """
        Close all engines stored in the engine map and clears the engine_map.
        """
        for engine in self.engine_map.values():
            await engine.dispose()
        self.engine_map = dict()

    def get_engine(self, override_db_name: typing.Optional[str] = None) -> AsyncEngine:
        """
        Get a database engine.

        If the database url is already in the engine map, return the engine stored there. Otherwise, build
        a new one, store it, and return the new engine.
        """
        db_url = build_db_url(
            override_db_name=override_db_name,
            force_test=settings.DEPLOY_ENV.lower() == "test",
        )
        if db_url not in self.engine_map:
            self.engine_map[db_url] = create_async_engine(db_url, pool_pre_ping=True)
        return self.engine_map[db_url]

    def get_session(self, override_db_name: typing.Optional[str] = None) -> AsyncSession:
        """
        Get an asynchronous database session.

        Gets a new session from the correct engine in the engine map.
        """
        engine = self.get_engine(override_db_name=override_db_name)
        return AsyncSession(engine)


engine_factory = EngineFactory()


@dataclass
class SecureSession:
    """
    Provide a container class for an IdentityPayload and AsyncSesson for the current request.
    """

    identity_payload: IdentityPayload
    session: AsyncSession


def secure_session(*scopes: str, permission_mode: PermissionMode = PermissionMode.ALL):
    """
    Provide an injectable for FastAPI that checks permissions and returns a database session for this request.

    This should be used for all secured routes that need access to the database. It will commit the
    transaction upon completion of the request. If an exception occurs, it will rollback the transaction.
    If multi-tenancy is enabled, it will retrieve a database session for the database associated with the
    client_id found in the requesting user's auth token.

    If testing mode is enabled, it will flush the session instead of committing changes to the database.

    Note that the session should NEVER be explicitly committed anywhere else in the source code.
    """

    async def dependency(
        identity_payload: IdentityPayload = Depends(
            lockdown_with_identity(*scopes, permission_mode=permission_mode)
        )
    ) -> AsyncIterator[SecureSession]:

        override_db_name = identity_payload.organization_id if settings.MULTI_TENANCY_ENABLED else None
        session = engine_factory.get_session(override_db_name=override_db_name)
        await session.begin_nested()
        try:
            yield SecureSession(
                identity_payload=identity_payload,
                session=session,
            )
            # In test mode, we should not commit to the database. Instead, just flush to the session
            if settings.DEPLOY_ENV.lower() == "test":
                logger.debug("Flushing session due to test mode")
                await session.flush()
                session.expire_all()
            else:
                logger.debug("Committing session")
                await session.commit()
        except Exception as err:
            logger.warning(f"Rolling back session due to error: {err}")
            await session.rollback()
            raise err
        finally:
            # In test mode, we should not close the session so that assertions can be made about the state
            # of the db session in the test functions after calling the application logic
            if settings.DEPLOY_ENV.lower() != "test":
                logger.debug("Closing session")
                await session.close()

    return dependency


def render_sql(session: AsyncSession, query) -> str:
    """
    Render a sqlalchemy query into a string for debugging.
    """
    return query.compile(dialect=session.bind.dialect, compile_kwargs={"literal_binds": True})


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
    return case(dict(sort_tuple), value=cast(sort_column, String))


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
    if isinstance(sort_column, Column) and isinstance(sort_column.type, Enum):
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


async def insert_data(
    session: AsyncSession,
    table: Table,
    data: Dict,
    trace_query: bool = False,
) -> int:
    """
    Provide a helper method for inserting data into a database table.
    """
    query = table.insert().values(data)
    if trace_query:
        logger.trace(f"insert_query = {render_sql(session, query)}")

    raw_result = await session.execute(query)

    # SQLAlchemy returns a tuple since primary keys can be composite. We only want the single pk
    # See: https://docs.sqlalchemy.org/en/20/tutorial/data_insert.html#executing-the-statement
    return raw_result.inserted_primary_key[0]


async def insert_instance(
    session: AsyncSession,
    table: Table,
    data: Dict,
    response_model: typing.Type[T],
    trace_query: bool = False,
) -> T:
    """
    Provide a helper method for inserting data and returning the result in a pydantic model.
    """
    query = table.insert().values(data).returning(table)
    if trace_query:
        logger.trace(f"insert_query = {render_sql(session, query)}")

    raw_result = await session.execute(query)
    return response_model.from_orm(raw_result.one())


async def fetch_all(
    session: AsyncSession,
    table: Table,
    response_model: typing.Type[T],
    where_clause=None,
) -> typing.List[T]:
    """
    Provide a helper method for retrieving all rows from a table that match an optional where clause.
    """
    query = table.select()
    if where_clause is not None:
        query = query.where(where_clause)
    raw_result = await session.execute(query)
    return [response_model.from_orm(r) for r in raw_result.fetchall()]


async def fetch_count(
    session: AsyncSession,
    table: Table,
    where_clause=None,
) -> int:
    """
    Provide a helper method for retrieving the count of all rows from a table (with an optional where clause).
    """
    query = select(func.count(table.c.id))
    if where_clause is not None:
        query = query.where(where_clause)
    raw_result = await session.execute(query)
    return raw_result.scalar()


async def fetch_data(
    session: AsyncSession,
    id: int,
    table: Table,
    trace_query: bool = False,
):
    """
    Provide a helper method for retrieving a single row from the database with the provided id (Private Key).

    Note: no return type is specified because SQLAlchemy typehints don't register sqlalchemy.engine.Row
    """
    query = table.select().where(table.c.id == id)
    if trace_query:
        logger.trace(f"select_query = {render_sql(session, query)}")
    raw_result = await session.execute(query)
    result = raw_result.one_or_none()
    message = f"Could not find {table.name} instance with id {id}"
    if result is None:
        logger.error(message)
        raise HTTPException(status.HTTP_404_NOT_FOUND, message)
    return result


async def fetch_instance(
    session: AsyncSession, id: int, table: Table, response_model: typing.Type[T], trace_query: bool = False
) -> T:
    """
    Provide a helper method for retrieving a single row and unpacking it into a pydantic model instance.
    """
    result = await fetch_data(session, id, table, trace_query=trace_query)
    return response_model.from_orm(result)
