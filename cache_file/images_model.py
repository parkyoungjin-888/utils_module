from enum import Enum
from typing import Optional
from beanie import PydanticObjectId
from pydantic import Field, validator
from datetime import datetime

from utils_module.custom_base_model import CustomBaseModel


class Image(CustomBaseModel):
    device_id: str
    name: str
    timestamp: float
    event_datetime: datetime
    process_datetime: datetime
    width: int
    height: int
    img_path: str


class ProjectImage(CustomBaseModel):
    id: PydanticObjectId = Field(alias='_id')
    device_id: str
    name: str
    event_datetime: str | datetime
    img_path: str
