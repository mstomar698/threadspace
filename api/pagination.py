from rest_framework.pagination import CursorPagination, PageNumberPagination


class FeedCursorPagination(CursorPagination):
    page_size = 20
    ordering = "-created_at"


class FeedPagination(PageNumberPagination):
    """Page-number pagination for the ranked feed.

    The feed is scored in Python (see ``core.ranking``) and paginated as a list,
    so a cursor (which needs a single ordering column) doesn't fit; page numbers
    do. Django's Paginator accepts the pre-sorted list directly.
    """

    page_size = 20
