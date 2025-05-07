"""
Provide functions to interact with persistent data storage.
"""

import re
import typing
from contextlib import asynccontextmanager
from dataclasses import dataclass
from itertools import product

import asyncpg
import fastapi
import sqlalchemy
from asyncpg.exceptions import UniqueViolationError
from fastapi.exceptions import HTTPException
from loguru import logger
from sqlalchemy import Column, Enum, or_
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Mapped
from sqlalchemy.sql.expression import Case, ColumnElement, UnaryExpression
from starlette import status
from yarl import URL

from jobbergate_api.config import LogLevelEnum, settings
from jobbergate_api.security import IdentityPayload, PermissionMode, lockdown_with_identity

INTEGRITY_CHECK_EXCEPTIONS = (UniqueViolationError,)


def build_db_url(
    override_db_name: str | None = None,
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

    engine_map: dict[str, AsyncEngine]

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

    def get_engine(self, override_db_name: str | None = None) -> AsyncEngine:
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
            self.engine_map[db_url] = create_async_engine(
                db_url,
                pool_size=settings.DATABASE_POOL_SIZE,
                pool_pre_ping=settings.DATABASE_POOL_PRE_PING,
                max_overflow=settings.DATABASE_POOL_MAX_OVERFLOW,
                logging_name="sqlalchemy.engine",
                echo=settings.LOG_LEVEL == LogLevelEnum.TRACE,
            )
        return self.engine_map[db_url]

    @asynccontextmanager
    async def auto_session(
        self,
        override_db_name: str | None = None,
        commit: bool = True,
    ) -> typing.AsyncIterator[AsyncSession]:
        """
        Get an asynchronous database session.

        Gets a new session from the correct engine in the engine map.
        """
        if settings.DEPLOY_ENV.lower() == "test":
            raise RuntimeError("The auto_session context manager may not be used in unit tests.")

        engine = self.get_engine(override_db_name=override_db_name)
        session = AsyncSession(engine)
        await session.begin()
        try:
            yield session
        except Exception as err:
            logger.warning(f"Rolling back session due to error: {err}")
            await session.rollback()
            raise err
        else:
            if commit is True:
                logger.debug("Committing session")
                await session.commit()
            else:
                logger.debug("Rolling back read-only session")
                await session.rollback()
        finally:
            logger.debug("Closing session")
            await session.close()


engine_factory = EngineFactory()


@dataclass
class SecureSession:
    """
    Provide a container class for an IdentityPayload and AsyncSession for the current request.
    """

    identity_payload: IdentityPayload
    session: AsyncSession


def secure_session(
    *scopes: str,
    permission_mode: PermissionMode = PermissionMode.SOME,
    commit: bool = True,
    ensure_email: bool = False,
    ensure_organization: bool = False,
    ensure_client_id: bool = False,
):
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
        identity_payload: IdentityPayload = fastapi.Depends(
            lockdown_with_identity(
                *scopes,
                permission_mode=permission_mode,
                ensure_email=ensure_email,
                ensure_organization=ensure_organization,
                ensure_client_id=ensure_client_id,
            )
        ),
    ) -> typing.AsyncIterator[SecureSession]:
        override_db_name = identity_payload.organization_id if settings.MULTI_TENANCY_ENABLED else None
        async with engine_factory.auto_session(override_db_name=override_db_name, commit=commit) as session:
            yield SecureSession(
                identity_payload=identity_payload,
                session=session,
            )

    return dependency


def render_sql(session: AsyncSession, query) -> str:
    """
    Render a sqlalchemy query into a string for debugging.
    """
    return query.compile(dialect=session.bind.dialect, compile_kwargs={"literal_binds": True})


def search_clause(
    search_terms: str,
    searchable_fields: set,
) -> ColumnElement[bool]:
    """
    Create search clause across searchable fields with search terms.

    Regarding the False first argument to or_():
        The or_() function must have one fixed positional argument.
        See: https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.or_
    """
    search_pairs = product(searchable_fields, search_terms.split())
    search_expressions = (field.ilike(f"%{term}%") for (field, term) in search_pairs)
    return or_(False, *search_expressions)


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

    Note::
        For sorting to work on sqlalchemy.Enum types, the enum _must_ be specified with ``native_enum=False``

        ```
        class SomeTable(Base):
            stuff: Mapped[StuffEnum] = mapped_column(Enum(StuffEnum, native_enum=False))
        ```
    """
    assert isinstance(sort_column.type, Enum)
    sorted_values = sorted(sort_column.type.enums)
    sort_tuple = zip(sorted_values, sorted_values if sort_ascending else reversed(sorted_values))
    return sqlalchemy.case(dict(sort_tuple), value=sort_column)


def sort_clause(
    sort_field: str,
    sortable_fields: set,
    sort_ascending: bool,
) -> typing.Union[Mapped, UnaryExpression, Case]:
    """
    Create a sort clause given a sort field, the list of sortable fields, and a sort_ascending flag.
    """
    sort_column: Mapped[typing.Any] | UnaryExpression | Case | None = None
    for sortable_field in sortable_fields:
        if sortable_field.name == sort_field:
            sort_column = sortable_field
            break

    if sort_column is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sorting column requested: {sort_field}. Must be one of {sortable_fields}",
        )

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
