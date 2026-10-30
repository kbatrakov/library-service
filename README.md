# Library Service API

Library API with core borrowing and return features. Built with Django REST Framework.

## Features

- JWT authentication (login by email)
- Books: list and detail for everyone, create/update/delete for admins only
- Borrowings: create, list, detail, return
  - creating a borrowing decreases the book inventory by 1
  - returning a borrowing increases the inventory by 1 (a borrowing can't be returned twice)
  - a regular user sees only their own borrowings, an admin sees all of them
- Filtering borrowings: `is_active` and `user_id` (admin only)
- Telegram notification on every new borrowing
- Interactive API documentation (Swagger)
- `Payment` model (data model only, no payment logic yet)

## Tech stack

- Python 3.11
- Django 5.2, Django REST Framework
- SimpleJWT
- drf-spectacular
- python-dotenv, requests

## Installation

```bash
git clone <your-repo-url>
cd library-service
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

Install dependencies and set up the project:

```bash
pip install -r requirements.txt
copy .env.sample .env        # Linux / macOS: cp .env.sample .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`.

## Environment variables

Copy `.env.sample` to `.env` and fill in the values. The `.env` file must never be committed.

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token of your Telegram bot (from @BotFather) |
| `TELEGRAM_CHAT_ID` | Id of the chat or channel for notifications |

If the Telegram variables are empty, the API still works, notifications are just skipped.

## Telegram notifications

1. Create a bot with `@BotFather` and copy its token.
2. Create a channel or group and add the bot (as an admin with the "Post messages" right for channels).
3. Send any message to the chat and open `https://api.telegram.org/bot<TOKEN>/getUpdates` to find the `chat.id`.
4. Put both values into `.env`.

## Authentication

1. Register: `POST /api/user/register/`
2. Get tokens: `POST /api/user/token/` with `email` and `password`
3. Send the access token in the header: `Authorization: Bearer <access_token>`
4. Refresh the token: `POST /api/user/token/refresh/`

## API endpoints

| Method | URL | Description | Access |
|---|---|---|---|
| POST | `/api/user/register/` | Register a new user | Anyone |
| POST | `/api/user/token/` | Get JWT pair | Anyone |
| POST | `/api/user/token/refresh/` | Refresh access token | Anyone |
| POST | `/api/user/token/verify/` | Verify token | Anyone |
| GET, PATCH | `/api/user/me/` | Own profile | Authenticated |
| GET | `/api/books/` | List books | Anyone |
| POST | `/api/books/` | Create a book | Admin |
| GET | `/api/books/<id>/` | Book detail | Anyone |
| PUT, PATCH, DELETE | `/api/books/<id>/` | Update / delete a book | Admin |
| GET | `/api/borrowings/` | List borrowings | Authenticated |
| POST | `/api/borrowings/` | Create a borrowing | Authenticated |
| GET | `/api/borrowings/<id>/` | Borrowing detail | Authenticated |
| POST | `/api/borrowings/<id>/return/` | Return a book | Authenticated |
| GET | `/api/doc/swagger/` | Swagger UI | Anyone |

### Filtering borrowings

- `GET /api/borrowings/?is_active=true` only borrowings that are not returned yet
- `GET /api/borrowings/?is_active=false` only returned borrowings
- `GET /api/borrowings/?user_id=<id>` borrowings of a specific user (admin only)

### Example: create a borrowing

```
POST /api/borrowings/
Authorization: Bearer <access_token>

{
    "book": 1,
    "expected_return_date": "2026-11-20"
}
```

## Documentation

Swagger UI: `http://127.0.0.1:8000/api/doc/swagger/`

Use the **Authorize** button to pass your JWT access token.

## Tests

```bash
python manage.py test
```

Test coverage:

```bash
pip install coverage
coverage run manage.py test
coverage report
```

## Project structure

```
books/        Book model, serializers, viewset, permissions
borrowings/   Borrowing model, serializers, viewset, Telegram helper
payments/     Payment model
user/         Custom user model (email login), registration, profile
```