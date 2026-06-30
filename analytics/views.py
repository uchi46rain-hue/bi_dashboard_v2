from django.shortcuts import render, redirect
from django.db.models import Sum, F, IntegerField, ExpressionWrapper
from .models import Sale, Product
from .forms import CSVUploadForm

import csv
import io
from datetime import datetime


def dashboard(request):

    # ==========================
    # CSVアップロード
    # ==========================

    if request.method == "POST":

        form = CSVUploadForm(request.POST, request.FILES)

        if form.is_valid():

            csv_file = form.cleaned_data["file"]

            text = io.StringIO(
                csv_file.read().decode("utf-8-sig")
            )

            reader = csv.DictReader(text)

            for row in reader:

                product, created = Product.objects.get_or_create(
                    name=row["product"],
                    defaults={
                        "category": row["category"],
                        "price": int(row["price"])
                    }
                )

                if not created:
                    product.category = row["category"]
                    product.price = int(row["price"])
                    product.save()

                Sale.objects.create(
                    product=product,
                    date=datetime.strptime(
                        row["date"],
                        "%Y-%m-%d"
                    ).date(),
                    quantity=int(row["quantity"])
                )

            return redirect("dashboard")

    else:

        form = CSVUploadForm()

    # ==========================
    # フィルター
    # ==========================

    category = request.GET.get("category")

    sales = Sale.objects.all()

    if category:
        sales = sales.filter(product__category=category)

    # 売上金額 = 単価 × 数量
    amount = ExpressionWrapper(
        F("product__price") * F("quantity"),
        output_field=IntegerField()
    )

    # ==========================
    # 月別売上（金額）
    # ==========================

    monthly_sales = (
        sales
        .values("date__month")
        .annotate(total=Sum(amount))
        .order_by("date__month")
    )

    # ==========================
    # 商品別売上（金額）
    # ==========================

    product_sales = (
        sales
        .values("product__name")
        .annotate(total=Sum(amount))
        .order_by("-total")
    )

    # ==========================
    # カテゴリ別売上（金額）
    # ==========================

    category_sales = (
        sales
        .values("product__category")
        .annotate(total=Sum(amount))
        .order_by("-total")
    )

    # ==========================
    # KPI
    # ==========================

    total_sales = (
        sales.aggregate(total=Sum(amount))["total"]
        or 0
    )

    product_count = Product.objects.count()

    category_count = (
        Product.objects
        .values("category")
        .distinct()
        .count()
    )

    monthly_count = monthly_sales.count()

    context = {
        "form": form,

        "monthly_sales": monthly_sales,
        "product_sales": product_sales,
        "category_sales": category_sales,

        "total_sales": total_sales,
        "product_count": product_count,
        "category_count": category_count,
        "monthly_count": monthly_count,

        "selected_category": category,
    }

    return render(
        request,
        "analytics/dashboard.html",
        context
    )