from django.db import models


class Product(models.Model):

    CATEGORY_CHOICES = [
        ("飲み物", "飲み物"),
        ("食べ物", "食べ物"),
        ("デザート", "デザート"),
    ]

    name = models.CharField(
        max_length=100
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES
    )

    price = models.IntegerField()

    def __str__(self):
        return self.name


class Sale(models.Model):

    WEATHER_CHOICES = [
        ("晴れ", "晴れ"),
        ("曇り", "曇り"),
        ("雨", "雨"),
        ("雪", "雪"),
    ]

    receipt_no = models.CharField(
        max_length=30
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    date = models.DateField()

    weather = models.CharField(
        max_length=10,
        choices=WEATHER_CHOICES
    )

    temperature = models.FloatField()

    quantity = models.IntegerField()

    def __str__(self):
        return f"{self.receipt_no} - {self.product.name}"