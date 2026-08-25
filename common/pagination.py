from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class with customizable page_size via query params.
    Default page size: 10, Maximum allowed: 100.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
