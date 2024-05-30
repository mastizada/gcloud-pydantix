from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True, strict=False, populate_by_name=True)
