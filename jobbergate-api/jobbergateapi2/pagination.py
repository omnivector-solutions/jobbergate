"""
Pagination feature for all endpoints.
"""

from typing import Optional, Generic, TypeVar, List

from pydantic import BaseModel
from pydantic.generics import GenericModel
from sqlalchemy import func, select

from jobbergateapi2.storage import database


class Pagination:
    """
    Basic pagination class.
    """

    def __init__(self, page: Optional[int] = None, per_page: int = 10):
        """
        Pagination constructor.

        Raises an exception if page is negative values.
        Raises an exception if per_page is less than 1.

        :param page: The start page. If None, no pagination will be applied.
        :param per_page: The number of items to include per page.
        """
        if page is not None and page < 0:
            raise ValueError("The page parameter must be greater than or equal to zero")
        if per_page < 1:
            raise ValueError("The per_page parameter must be greater than zero")

        self.page = page
        self.per_page = per_page

    def __str__(self):
        return f"page={self.page}, per_page={self.per_page}"

    def to_dict(self):
        return dict() if self.page is None else dict(page=self.page, per_page=self.per_page)


class ResponseMetadata(BaseModel):
    """
    A metadata model that describes pagination info.
    """
    total: int
    page: Optional[int]
    per_page: Optional[int]


DataT = TypeVar("DataT")


class Response(GenericModel, Generic[DataT]):
    """
    An envelope for responses including the metadata for pagination.
    """
    results: List[DataT]
    metadata: ResponseMetadata


async def package_response(model, query, pagination: Pagination) -> Response:
    """
    Packages the response in an envelope that includes the response and the metadata.

    Structure of response is::

        {
            "results": [result0, result1, ...resultN],
            "metadata": {
                "total": N,
                "page": i,
                "per_page", n,
            },
        }

    If pagination.page is None, no pagination is performed
    """
    # The explicit order_by removes any sorting added to the query for the total computation
    # total = await database.fetch_val(query.with_only_columns([func.count()]).order_by(None))
    count_query = select(func.count()).select_from(query.subquery())
    total = await database.fetch_val(query=count_query)
    if pagination.page is not None:
        query = query.limit(pagination.per_page).offset(pagination.page * pagination.per_page)
    raw_response = await database.fetch_all(query)
    return Response(
        results=[model.parse_obj(x) for x in raw_response],
        metadata=ResponseMetadata(total=total, **pagination.to_dict())
    )
