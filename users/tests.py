from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

REGISTER_URL = "/api/user/register/"
TOKEN_URL = "/api/user/token/"
ME_URL = "/api/user/me/"


class UserModelTests(TestCase):
    def test_create_user(self):
        user = get_user_model().objects.create_user(
            email="a@test.com", password="pass12345"
        )
        self.assertTrue(user.check_password("pass12345"))
        self.assertFalse(user.is_staff)
        self.assertEqual(str(user), "a@test.com")

    def test_create_user_without_email(self):
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user(email="", password="x")

    def test_create_superuser(self):
        user = get_user_model().objects.create_superuser(
            email="root@test.com", password="pass12345"
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class UserApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register(self):
        payload = {
            "email": "new@test.com",
            "password": "pass12345",
            "first_name": "Ann",
            "last_name": "Lee",
        }
        response = self.client.post(REGISTER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)

        user = get_user_model().objects.get(email="new@test.com")
        self.assertNotEqual(user.password, "pass12345")
        self.assertTrue(user.check_password("pass12345"))

    def test_register_cannot_set_is_staff(self):
        payload = {
            "email": "sneaky@test.com",
            "password": "pass12345",
            "is_staff": True,
        }
        self.client.post(REGISTER_URL, payload)
        user = get_user_model().objects.get(email="sneaky@test.com")
        self.assertFalse(user.is_staff)

    def test_register_duplicate_email(self):
        payload = {"email": "dup@test.com", "password": "pass12345"}
        self.client.post(REGISTER_URL, payload)
        response = self.client.post(REGISTER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password(self):
        payload = {"email": "short@test.com", "password": "1"}
        response = self.client.post(REGISTER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_obtain_token(self):
        get_user_model().objects.create_user(
            email="tok@test.com", password="pass12345"
        )
        response = self.client.post(
            TOKEN_URL, {"email": "tok@test.com", "password": "pass12345"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_obtain_token_wrong_password(self):
        get_user_model().objects.create_user(
            email="tok@test.com", password="pass12345"
        )
        response = self.client.post(
            TOKEN_URL, {"email": "tok@test.com", "password": "wrong"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_auth(self):
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_with_jwt(self):
        get_user_model().objects.create_user(
            email="me@test.com", password="pass12345"
        )
        token = self.client.post(
            TOKEN_URL, {"email": "me@test.com", "password": "pass12345"}
        ).data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "me@test.com")

    def test_update_me_changes_password(self):
        user = get_user_model().objects.create_user(
            email="upd@test.com", password="pass12345"
        )
        self.client.force_authenticate(user)
        response = self.client.patch(
            ME_URL, {"first_name": "Bob", "password": "newpass123"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Bob")
        self.assertTrue(user.check_password("newpass123"))
