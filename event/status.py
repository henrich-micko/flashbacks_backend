from enum import Enum


class EventStatus(Enum):
    OPENED = 0
    ACTIVE = 1
    CLOSED = 2


class EventMemberStatus(Enum):
    MEMBER = 0
    INVITED = 1
    NONE = 2
