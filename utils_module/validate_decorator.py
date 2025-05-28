from functools import wraps
from pydantic import BaseModel

def validate_input(model: BaseModel):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            validated_data = model(**kwargs)
            return func(*args, **{'data_model': validated_data})
        return wrapper
    return decorator


def validate_output(model: BaseModel):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if result is None:
                return None
            validated_data = model(**result)
            return validated_data.model_dump()
        return wrapper
    return decorator
