from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """
    Paginación por defecto.
    Permite que el frontend pida más (o todos) los resultados en una sola
    llamada mediante el query param `page_size`.

    Ejemplos:
        /api/sales/                 -> 10 por página (default)
        /api/sales/?page_size=500   -> 500 por página
        /api/sales/?page_size=1000  -> hasta 1000 por página (máximo permitido)
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000
