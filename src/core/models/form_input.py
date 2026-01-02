from dataclasses import dataclass
from typing import Optional
from uuid import uuid4


@dataclass
class FormInput:
    serial_port: str = "AUTO"
    baudrate: int = 115200

    line_enable: bool = True
    line_key: str = ""

    csv_enable: bool = False
    csv_delimiter: str = ","
    csv_key_index: Optional[int] = 0
    csv_value_index: Optional[int] = 1
    csv_time_index: Optional[int] = None

    json_enable: bool = False
    json_key_field: str = "key"
    json_value_field: str = "value"
    json_time_field: Optional[str] = "time"
