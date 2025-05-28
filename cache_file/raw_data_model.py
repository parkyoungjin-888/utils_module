from pydantic import BaseModel, Field, field_validator
import base64
import cv2
import numpy as np
from typing import Any


class Rawdata(BaseModel):
    timestamp: float = Field(examples=[1717657200.000000])
    io_id: str = Field(examples=['io_id'])
    value: float = Field(examples=[100.1])


class Imgdata(BaseModel):
    device_id: str = Field(examples=['cam'], default=None)
    name: str = Field(examples=['img_name.jpg'], default=None)
    timestamp: float = Field(examples=[1717657200.000000], default=None)
    width: int = Field(examples=[1920], default=None)
    height: int = Field(examples=[1080], default=None)
    img: Any

    @field_validator('img')
    @classmethod
    def encode_img(cls, img) -> str:
        if isinstance(img, str):
            return img

        _, buffer = cv2.imencode('.jpg', img)
        return base64.b64encode(buffer).decode('utf-8')

    def get_dict_with_img_decoding(self):
        return_dict = self.model_dump()

        if 'img' in return_dict:
            img_data = base64.b64decode(return_dict['img'])
            img_data = np.frombuffer(img_data, np.uint8)
            return_dict['img'] = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
        return return_dict


class RawdataBatch(BaseModel):
    batch: list[Rawdata]


class ImgdataBatch(BaseModel):
    batch: list[Imgdata]
