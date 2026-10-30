from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Book

BOOKS_URL = "/api/books/"


def detail_url(book_id):
    return f"{BOOKS_URL}{book_id}/"


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


class BookModelTests(TestCase):
    def test_create_book(self):
        book = make_book()
        self.assertEqual(book.cover, Book.CoverType.HARD)
        self.assertEqual(book.inventory, 5)


class PublicBookApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.book = make_book()

    def test_list_available_for_anonymous(self):
        response = self.client.get(BOOKS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn("book_info", response.data[0])

    def test_list_book_info_content(self):
        response = self.client.get(BOOKS_URL)
        info = response.data[0]["book_info"]
        self.assertEqual(info["title"], "Dracula")
        self.assertEqual(info["author"], "Bram Stoker")

    def test_detail_available_for_anonymous(self):
        response = self.client.get(detail_url(self.book.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Dracula")
        self.assertIn("borrowings", response.data)

    def test_create_forbidden_for_anonymous(self):
        response = self.client.post(BOOKS_URL, {})
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )


class AuthenticatedBookApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="pass12345"
        )
        self.client.force_authenticate(self.user)

    def test_create_forbidden_for_non_staff(self):
        payload = {
            "title": "New",
            "author": "Author",
            "cover": "SOFT",
            "inventory": 3,
            "daily_fee": "2.00",
        }
        response = self.client.post(BOOKS_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_forbidden_for_non_staff(self):
        book = make_book()
        response = self.client.delete(detail_url(book.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminBookApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_user(
            email="admin@test.com", password="pass12345", is_staff=True
        )
        self.client.force_authenticate(self.admin)

    def test_create_book(self):
        payload = {
            "title": "New",
            "author": "Author",
            "cover": "SOFT",
            "inventory": 3,
            "daily_fee": "2.00",
        }
        response = self.client.post(BOOKS_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Book.objects.filter(title="New").exists())

    def test_create_book_invalid_cover(self):
        payload = {
            "title": "New",
            "author": "Author",
            "cover": "WRONG",
            "inventory": 3,
            "daily_fee": "2.00",
        }
        response = self.client.post(BOOKS_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_book(self):
        book = make_book()
        response = self.client.patch(detail_url(book.id), {"inventory": 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        book.refresh_from_db()
        self.assertEqual(book.inventory, 10)

    def test_delete_book(self):
        book = make_book()
        response = self.client.delete(detail_url(book.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Book.objects.filter(id=book.id).exists())
