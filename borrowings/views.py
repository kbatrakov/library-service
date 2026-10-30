from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingCreateSerializer,
    BorrowingListSerializer, BorrowingDetailSerializer,
)
from borrowings.telegram import send_telegram_message


class BorrowingViewSet(mixins.CreateModelMixin,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       viewsets.GenericViewSet):

    queryset = Borrowing.objects.select_related("book", "user")
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user

        if user.is_staff:
            user_id = self.request.query_params.get("user_id")
            if user_id:
                queryset = queryset.filter(user_id=user_id)
        else:
            queryset = queryset.filter(user=user)

        is_active = self.request.query_params.get("is_active")

        if is_active is not None:
            if is_active.lower() in ("true", "1"):
                queryset = queryset.filter(actual_return_date__isnull=True)
            elif is_active.lower() in ("false", "0"):
                queryset = queryset.filter(actual_return_date__isnull=False)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return BorrowingListSerializer
        if self.action == "create":
            return BorrowingCreateSerializer
        return BorrowingDetailSerializer

    def perform_create(self, serializer):
        borrowing = serializer.save(user=self.request.user)
        send_telegram_message(
            f"New borrowing #{borrowing.id}\n"
            f"User: {borrowing.user.email}\n"
            f"Book: {borrowing.book.title} by {borrowing.book.author}\n"
            f"Borrowed: {borrowing.borrow_date}\n"
            f"Expected return: {borrowing.expected_return_date}"
        )

    @action(detail=True, methods=["post"], url_path="return")
    def return_book(self, request, pk=None):
        with transaction.atomic():
            borrowing = (
                Borrowing.objects.select_for_update()
                .select_related("book")
                .get(pk=self.get_object().pk)
            )
            if borrowing.actual_return_date:
                return Response(
                    {"detail": "Borrowing is already returned."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            borrowing.actual_return_date = timezone.localdate()
            borrowing.save()

            book = borrowing.book
            book.inventory += 1
            book.save()

        return Response(BorrowingSerializer(borrowing).data)
