from django.contrib import admin
from .models import Product, Sale


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "category",
        "price",
    )

    list_filter = (
        "category",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "category",
        "name",
    )


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "receipt_no",
        "date",
        "product",
        "weather",
        "temperature",
        "quantity",
    )

    list_filter = (
        "date",
        "weather",
        "product__category",
    )

    search_fields = (
        "receipt_no",
        "product__name",
    )

    ordering = (
        "-date",
    )

    list_per_page = 30