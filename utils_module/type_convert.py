import json
from datetime import datetime

convert_map = {
    'str': str,
    'int': int,
    'float': float,
    'bool': (lambda s: s.strip().lower() == 'true'),
    'list': lambda x: json.loads(x.replace("'", '"')),
    'datetime': (lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f'))
}


def convert_date_type(data_value: any, data_type: str):
    if data_type not in convert_map:
        raise Exception(f'in convert_date_type, {data_type} is unknown type')

    convert_func = convert_map[data_type]
    return convert_func(data_value)
