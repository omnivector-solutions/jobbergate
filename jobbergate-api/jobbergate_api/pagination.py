"""
Pagination feature for all endpoints.
"""

from typing import Dict, Generic, List, Optional, Type, TypeVar, Union

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel
from sqlalchemy import func, select

from jobbergate_api.storage import database


class Pagination(BaseModel):
    """
    Basic pagination class.
    """

    start: Optional[int] = Field(
        None,
        ge=0,
        description="""
            The page offset for items, where the first page index is 0.
            The index for the first item on each page is computed as

                index == start * limit.

            Value must be greater than or equal to 0.
        """,
    )
    limit: int = Field(
        10,
        gt=0,
        description="Limit of items to include per page. Must be greater than 0",
    )

    def dict(self):
        """
        Override default ``dict()`` behavior so that if ``page`` is None, all fields are omitted.
        """
        return dict() if self.start is None else super().dict()


class ResponsePagination(BaseModel):
    """
    A metadata model that describes pagination info.
    """

    total: int
    start: Optional[int]
    limit: Optional[int]


TResponseModel = TypeVar("TResponseModel", bound=BaseModel)


class Response(GenericModel, Generic[TResponseModel]):
    """
    An envelope for responses including the metadata for pagination.

    This is a generic response envelope that can be used for any of list of pydantic models.
    """

    results: List[TResponseModel]
    pagination: ResponsePagination


def ok_response(
    _: Type[TResponseModel],
) -> Dict[Union[int, str], Dict[str, Type[Response[TResponseModel]]]]:
    """
    Package up a response type compatible with FastAPI's ``responses`` argument.

    The typing is intense here, but is just basically saying that given some generic model input,
    return a dictionary that contains a ``Response`` for that model type.

    """
    return {200: {"model": Response[TResponseModel]}}


async def package_response(model: Type[TResponseModel], query, pagination: Pagination) -> JSONResponse:
    """
    Package the response in an envelope that includes the response and the metadata.

    Return a JSONResponse containing the packaged data.

    Structure of response is::

        {
            "results": [result0, result1, ...resultN],
            "metadata": {
                "total": N,
                "start": i,
                "limit", n,
            },
        }

    If pagination.start is None, no pagination is performed
    """
    # The explicit order_by removes any sorting added to the query for the total computation
    # total = await database.fetch_val(query.with_only_columns([func.count()]).order_by(None))
    count_query = select(func.count()).select_from(query.subquery())
    total = await database.fetch_val(query=count_query)
    if pagination.start is not None:
        query = query.limit(pagination.limit).offset(pagination.start * pagination.limit)
    raw_response = await database.fetch_all(query)
    validated_response = Response[TResponseModel](
        results=[model.parse_obj(x) for x in raw_response],
        pagination=ResponsePagination(total=total, **pagination.dict()),
    )
    jsonable_response = jsonable_encoder(validated_response)
    return JSONResponse(content=jsonable_response)
