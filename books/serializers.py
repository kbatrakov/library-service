from rest_framework import serializers
from books.models import Book


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "cover",
            "inventory",
            "daily_fee"
        ]


class BookListSerializer(serializers.ModelSerializer):
    book_info = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Book
        fields = [
            "id",
            "book_info",
        ]

    def get_book_info(self, obj):
        return  {"title": obj.title,
                "author": obj.author,
                "availability": self.get_availability(obj)
                 }

    def get_availability(self, obj):
        if obj.inventory == 0:
            return "Out of stock"
        if obj.inventory <= 2:
            return "Last copies"
        return "In stock"


class BookDetailSerializer(serializers.ModelSerializer):
    borrowings = serializers.SerializerMethodField()
    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "cover",
            "inventory",
            "daily_fee",
            "borrowings"
        ]

    def get_borrowings(self, obj):
        return [
            {
                "id": book.id,
                "borrow_date": book.borrow_date,
                "expected_return_date": book.expected_return_date,
                "actual_return_date": book.actual_return_date,
            }
            for book in obj.borrowings.all()
        ]
