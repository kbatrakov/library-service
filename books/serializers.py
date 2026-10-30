from drf_spectacular.utils import extend_schema_field
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

    @extend_schema_field(
        {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "author": {"type": "string"},
                "availability": {"type": "string"},
            },
        }
    )
    def get_book_info(self, obj):
        return {"title": obj.title,
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
    borrowings = serializers.SerializerMethodField(read_only=True)

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
        request = self.context.get("request")
        show_user_status = bool(request and request.user.is_authenticated)
        return [
            {
                "id": borrowing.id,
                "borrowed_by": borrowing.user.get_full_name() or
                borrowing.user.email
                if show_user_status else None,
                "borrow_date": borrowing.borrow_date,
                "expected_return_date": borrowing.expected_return_date,
                "actual_return_date": borrowing.actual_return_date,
            }
            for borrowing in obj.borrowings.all()
        ]
