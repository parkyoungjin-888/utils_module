from enum import Enum
from typing import Optional
from beanie import PydanticObjectId
from pydantic import Field, validator

from utils_module.custom_base_model import CustomBaseModel


class AnalysisCategory(Enum):
    OCR = 'ocr'
    OBJECT_DETECTION = 'object_detection'


class ImgProcess(CustomBaseModel):
    name: str
    img_collection: Optional[str | None] = None
    category: Optional[AnalysisCategory | None] = None
    config: dict = None


class ProjectImgProcess(CustomBaseModel):
    id: PydanticObjectId = Field(alias='_id')
    name: str
    img_collection: Optional[str | None] = None
    category: Optional[AnalysisCategory | None] = None
