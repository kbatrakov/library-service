from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Book
from borrowings.models import Borrowing
from borrowings.telegram import send_telegram_message
import logging

logging.disable(logging.CRITICAL)

BORROWINGS_URL = "/api/borrowings/"


def detail_url(pk):
    return f"{BORROWINGS_URL}{pk}/"


def return_url(pk):
    return f"{BORROWINGS_URL}{pk}/return/"


def make_user(email="user@test.com", **kwargs):
    return get_user_model().objects.create_user(
        email=email, password="pass12345", **kwargs
    )


def make_book(**kwargs):
    defaults = {
        "title": "Dracula",
        "author": "Bram Stoker",
        "cover": "HARD",
        "inventory": 5,
        "daily_fee": Decimal("1.50"),
    }
    defaults.update(kwargs)
    return Book.objects.create(**defaults)


def make_borrowing(user, book, **kwargs):
    defaults = {"expected_return_date": timezone.localdate() + timedelta(days=7)}
    defaults.update(kwargs)
    return Borrowing.objects.create(user=user, book=book, **defaults)


class BorrowingModelTests(TestCase):
    def test_str(self):
        borrowing = make_borrowing(make_user(), make_book())
        self.assertIn("user@test.com", str(borrowing))


class UnauthenticatedBorrowingTests(TestCase):
    def test_list_requires_auth(self):
        response = APIClient().get(BORROWINGS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_auth(self):
        response = APIClient().post(BORROWINGS_URL, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@patch("borrowings.views.send_telegram_message")
class BorrowingCreateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.book = make_book(inventory=2)
        self.future = str(timezone.localdate() + timedelta(days=7))

    def test_create_borrowing(self, mock_send):
        payload = {"book": self.book.id, "expected_return_date": self.future}
        response = self.client.post(BORROWINGS_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        borrowing = Borrowing.objects.get()
        self.assertEqual(borrowing.user, self.user)
        self.assertEqual(borrowing.book, self.book)

    def test_create_decreases_inventory(self, mock_send):
        payload = {"book": self.book.id, "expected_return_date": self.future}
        self.client.post(BORROWINGS_URL, payload)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 1)

    def test_create_sends_notification(self, mock_send):
        payload = {"book": self.book.id, "expected_return_date": self.future}
        self.client.post(BORROWINGS_URL, payload)
        mock_send.assert_called_once()
        self.assertIn("Dracula", mock_send.call_args[0][0])

    def test_create_out_of_stock(self, mock_send):
        self.book.inventory = 0
        self.book.save()
        payload = {"book": self.book.id, "expected_return_date": self.future}
        response = self.client.post(BORROWINGS_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Borrowing.objects.count(), 0)
        mock_send.assert_not_called()

    def test_create_past_date(self, mock_send):
        past = str(timezone.localdate() - timedelta(days=1))
        payload = {"book": self.book.id, "expected_return_date": past}
        response = self.client.post(BORROWINGS_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_is_not_taken_from_payload(self, mock_send):
        other = make_user("other@test.com")
        payload = {
            "book": self.book.id,
            "expected_return_date": self.future,
            "user": other.id,
        }
        self.client.post(BORROWINGS_URL, payload)
        self.assertEqual(Borrowing.objects.get().user, self.user)


class BorrowingListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.other = make_user("other@test.com")
        self.admin = make_user("admin@test.com", is_staff=True)
        self.book = make_book()

        self.active = make_borrowing(self.user, self.book)
        self.returned = make_borrowing(
            self.user, self.book, actual_return_date=timezone.localdate()
        )
        self.other_borrowing = make_borrowing(self.other, self.book)

    def _ids(self, response):
        return {item["id"] for item in response.data}

    def test_user_sees_only_own(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(BORROWINGS_URL)
        self.assertEqual(
            self._ids(response), {self.active.id, self.returned.id}
        )

    def test_user_cannot_use_user_id_filter(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(BORROWINGS_URL, {"user_id": self.other.id})
        self.assertNotIn(self.other_borrowing.id, self._ids(response))

    def test_admin_sees_all(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(BORROWINGS_URL)
        self.assertEqual(len(response.data), 3)

    def test_admin_filter_by_user_id(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(BORROWINGS_URL, {"user_id": self.other.id})
        self.assertEqual(self._ids(response), {self.other_borrowing.id})

    def test_filter_is_active_true(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(BORROWINGS_URL, {"is_active": "true"})
        self.assertEqual(self._ids(response), {self.active.id})

    def test_filter_is_active_false(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(BORROWINGS_URL, {"is_active": "false"})
        self.assertEqual(self._ids(response), {self.returned.id})

    def test_detail_own(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(detail_url(self.active.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["book"]["title"], "Dracula")

    def test_detail_foreign_is_404(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(detail_url(self.other_borrowing.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class BorrowingReturnTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.book = make_book(inventory=1)
        self.borrowing = make_borrowing(self.user, self.book)

    def test_return_sets_date_and_increases_inventory(self):
        response = self.client.post(return_url(self.borrowing.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.borrowing.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(self.borrowing.actual_return_date, timezone.localdate())
        self.assertEqual(self.book.inventory, 2)

    def test_cannot_return_twice(self):
        self.client.post(return_url(self.borrowing.id))
        response = self.client.post(return_url(self.borrowing.id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 2)

    def test_cannot_return_foreign_borrowing(self):
        other = make_user("other@test.com")
        foreign = make_borrowing(other, self.book)
        response = self.client.post(return_url(foreign.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TelegramHelperTests(TestCase):
    @override_settings(TELEGRAM_BOT_TOKEN="token", TELEGRAM_CHAT_ID="123")
    @patch("borrowings.telegram.requests.post")
    def test_send_success(self, mock_post):
        mock_post.return_value = MagicMock()
        self.assertTrue(send_telegram_message("hello"))
        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args.kwargs["json"]["text"], "hello")

    @override_settings(TELEGRAM_BOT_TOKEN="token", TELEGRAM_CHAT_ID="123")
    @patch("borrowings.telegram.requests.post")
    def test_send_request_error(self, mock_post):
        mock_post.side_effect = requests.RequestException("boom")
        self.assertFalse(send_telegram_message("hello"))

    @override_settings(TELEGRAM_BOT_TOKEN=None, TELEGRAM_CHAT_ID=None)
    @patch("borrowings.telegram.requests.post")
    def test_not_configured(self, mock_post):
        self.assertFalse(send_telegram_message("hello"))
        mock_post.assert_not_called()
