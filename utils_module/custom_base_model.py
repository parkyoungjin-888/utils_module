from pydantic import BaseModel, ConfigDict, root_validator
from datetime import datetime


def convert_type_str(obj):
    if isinstance(obj, dict):
        return {k: convert_type_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_type_str(v) for v in obj]
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    elif isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    else:
        return str(obj)


class CustomBaseModel(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    @root_validator(pre=True)
    def type_based_conversion(cls, values):
        for field_name, value in values.items():
            if field_name not in cls.__annotations__:
                continue
            field_type = cls.__annotations__.get(field_name)
            if field_type == str and not isinstance(value, str):
                values[field_name] = str(value)
            if field_type == int and isinstance(value, str) and value.isdigit():
                values[field_name] = int(value)
            elif field_type == int and isinstance(value, float):
                values[field_name] = int(value)
            elif field_type == float and isinstance(value, str):
                try:
                    values[field_name] = float(value)
                except ValueError:
                    raise ValueError(f'Field {field_name} expects a float value, got {value}')
        return values

    def model_dump(self, *args, stringify_extra_type=False, **kwargs):
        result = super().model_dump(*args, **kwargs)
        if stringify_extra_type:
            result = convert_type_str(result)
        return result
