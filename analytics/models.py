from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50)
    price = models.IntegerField()

    def __repr__(self):
        return f"<Product: {self.name}>"


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    receipt_no = models.CharField(max_length=50)
    date = models.DateField()
    weather = models.CharField(max_length=20)
    temperature = models.FloatField()
    quantity = models.IntegerField()

    # 👇 ここを追加して重複判定のルールを定義します
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["receipt_no", "date", "product"], 
                name="unique_receipt_product"
            )
        ]

    def __repr__(self):
        return f"<Sale: {self.receipt_no} - {self.product.name}>"