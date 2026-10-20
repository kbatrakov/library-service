from django.db import models
from library_service import settings


class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey("books.Book", on_delete=models.CASCADE, related_name="borrowings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrowings")

    def __str__(self):
        return (f"Book {self.book} borrowed by {self.user.email} on {self.borrow_date}."
                f"Return by {self.expected_return_date}."
                )
