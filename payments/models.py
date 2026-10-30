from django.db import models


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        PAID = "PAID"

    class Type(models.TextChoices):
        PAYMENT = "PAYMENT"
        FINE = "FINE"

    status = models.CharField(
        max_length=7,
        choices=Status.choices,
        default=Status.PENDING,
    )
    type = models.CharField(max_length=7, choices=Type.choices)
    borrowing = models.ForeignKey(
        "borrowings.Borrowing",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    session_url = models.URLField(max_length=2000)
    session_id = models.CharField(max_length=255)
    money_to_pay = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.type} {self.status} for borrowing #{self.borrowing_id}"
