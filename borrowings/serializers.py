from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from books.models import Book
from books.serializers import BookSerializer
from borrowings.models import Borrowing


class BorrowingListSerializer(serializers.ModelSerializer):
    book = serializers.StringRelatedField()
    user = serializers.StringRelatedField()
    class Meta:
        model = Borrowing
        fields = [
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user"

        ]
        read_only_fields = fields



class BorrowingDetailSerializer(BorrowingListSerializer):
    book = BookSerializer(read_only=True)


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ["id", "expected_return_date", "book"]

    def validate_expected_return_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError(
                "Expected return date cannot be in the past."
            )
        return value

    def validate_book(self, book):
        if book.inventory < 1:
            raise serializers.ValidationError("This book is out of stock.")
        return book

    def create(self, validated_data):
        with transaction.atomic():
            book = Book.objects.select_for_update().get(pk=validated_data["book"].pk)
            if book.inventory < 1:
                raise serializers.ValidationError("This book is out of stock.")
            book.inventory -= 1
            book.save()
            return Borrowing.objects.create(**{**validated_data, "book": book})
