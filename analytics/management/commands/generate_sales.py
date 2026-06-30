import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from analytics.models import Product, Sale

class Command(BaseCommand):
    def handle(self, *args, **kwargs):

        # 商品を作成（毎回初期化）
        Product.objects.all().delete()
        Sale.objects.all().delete()

        products = [
            {"name": "コーヒー", "category": "ドリンク", "price": 450},
            {"name": "カフェラテ", "category": "ドリンク", "price": 520},
            {"name": "サンドイッチ", "category": "フード", "price": 650},
            {"name": "ケーキ", "category": "フード", "price": 700},
        ]

        product_objs = []

        for p in products:
            obj = Product.objects.create(
                name=p["name"],
                category=p["category"],
                price=p["price"]
            )
            product_objs.append(obj)

        start_date = datetime(2025, 1, 1)

        weather_list = ["晴れ", "曇り", "雨"]

        for i in range(365):
            date = start_date + timedelta(days=i)

            weather = random.choice(weather_list)

            # 気温ロジック（ざっくり季節感）
            temp = 10 + (i % 365) * 0.05 + random.randint(-5, 5)

            for product in product_objs:
                quantity = random.randint(0, 10)

                # 雨の日は少し減る
                if weather == "雨":
                    quantity = int(quantity * 0.7)

                Sale.objects.create(
                    product=product,
                    date=date,
                    quantity=quantity,
                    weather=weather,
                    temperature=round(temp, 1)
                )

        self.stdout.write(self.style.SUCCESS("ダミーデータ生成完了"))