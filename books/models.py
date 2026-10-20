from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class Book(models.Model):
    class CoverType(models.TextChoices):
        HARD = "HARD"
        SOFT = "SOFT"

    title = models.CharField(max_length=168)
    author = models.CharField(max_length=168)
    cover = models.CharField(max_length=4, choices=CoverType.choices)
    inventory = models.PositiveIntegerField()
    daily_fee = models.DecimalField(max_digits=6,
                                    decimal_places=2,
                                    validators=[MinValueValidator(Decimal("0.01"))]
                                    )
