from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any, Generator


@contextmanager
def open_optional_file(file_path: Path | None, mode: str = "rb") -> Generator[IO[Any] | None, None, None]:
    if file_path is None:
        yield None
        return
    with file_path.open(mode) as file:
        yield file


def filter_null_out(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}
