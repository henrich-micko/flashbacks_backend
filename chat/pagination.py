from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from urllib.parse import urlparse


class MessageCursorPagination(CursorPagination):
    page_size = 30
    ordering = "-timestamp"