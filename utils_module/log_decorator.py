import time
import json
from functools import wraps


def dump_result(result, str_max_size: int = 200):
    try:
        dumped_result = json.dumps(result)
        return dumped_result if len(str(dumped_result)) < str_max_size else str(dumped_result)[:str_max_size] + ' ...'
    except Exception as e:
        return str(result) if len(str(result)) < str_max_size else str(result)[:str_max_size] + ' ...'


def log_decorator(logger, res_max_size: int = 200):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                tact_time = time.time() - start_time
                logger.info({
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs),
                    'result': dump_result(result, res_max_size),
                    'tact_time': round(tact_time, 4),
                    'message': 'success'
                })
                return result
            except Exception as e:
                tact_time = time.time() - start_time
                logger.error({
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs),
                    'tact_time': round(tact_time, 4),
                    'message': e,
                })
                raise e

        return wrapper

    return decorator
