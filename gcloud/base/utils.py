from collections.abc import Callable
from typing import ParamSpec, TypeVar

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict

__all__ = ["DecoratorType", "BaseModel"]

P = ParamSpec("P")
T = TypeVar("T")
DecoratorType = Callable[[Callable[P, T]], Callable[P, T]]


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True, strict=False, populate_by_name=True)
