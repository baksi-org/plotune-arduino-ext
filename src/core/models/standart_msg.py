from dataclasses import dataclass

@dataclass
class MessageIn:
    key:str
    value:float
    time:float

@dataclass
class MessageOut:
    key:str
    value:float
    timestamp:float

@dataclass
class Message:
    value:float
    timestamp:float