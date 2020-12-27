from typing import Callable, List, Dict

from pydantic import BaseModel, Json, validator


class JSONModel(BaseModel):
    data: Json

    # @validator('data')
    # def data_mast_be_json(cls, d):
    #     if not isinstance(d, Json):
    #         raise ValueError('Data type error')
    #     return d
