from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response


class SearchAPIMixin:
    search_fields = []
    search_data_sort = None

    def get_search_query(self, search_term):
        search_query = Q()
        search_queryset = self.get_queryset()
        for field in self.search_fields:
            search_query |= Q(**{f"{field}__icontains": search_term})
        return search_queryset.filter(search_query)

    @action(detail=False, methods=["get"])
    def search(self, request):
        search_query = request.query_params.get("q", None)
        if not search_query:
            return Response({"detail": "Search query is required"}, status=status.HTTP_400_BAD_REQUEST)

        query = self.get_search_query(search_term=search_query)
        data = self.get_serializer(query, many=True).data
        if self.search_data_sort is not None:
            data = sorted(data, key=self.search_data_sort)

        return Response(data, status=status.HTTP_200_OK)