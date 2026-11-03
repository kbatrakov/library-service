from rest_framework import viewsets
from books.models import Book
from books.permissions import IsAdminOrReadOnly
from books.serializers import (BookSerializer, BookListSerializer,
                               BookDetailSerializer)


class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    queryset = Book.objects.all()
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = self.queryset
        if self.action == "retrieve":
            queryset = queryset.prefetch_related("borrowings__user")
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return BookListSerializer
        elif self.action == "retrieve":
            return BookDetailSerializer

        return BookSerializer
