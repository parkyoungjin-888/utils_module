from enum import Enum
from typing import Optional
from beanie import PydanticObjectId
from pydantic import Field, validator
from datetime import datetime

from utils_module.custom_base_model import CustomBaseModel


class Image(CustomBaseModel):
    device_id: str = None
    name: str
    timestamp: float = None
    event_datetime: datetime = None
    process_datetime: datetime = None
    width: int = None
    height: int = None
    img_path: str = None
    result: Optional[dict] = {}
    updated_datetime: datetime = None


class ProjectImage(CustomBaseModel):
    id: PydanticObjectId = Field(alias='_id')
    device_id: str = None
    name: str
    event_datetime: str | datetime = None
    img_path: str = None
