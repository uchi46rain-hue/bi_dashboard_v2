import csv
import os
import random
from datetime import datetime, timedelta

def generate_daily_pos_data(output_filename="sample_sales_v2.csv"):
    # 立ち飲み屋の商品マスタ（元のメニュー、価格、ウェイトを完全維持）
    PRODUCTS = {
        "ドリンク": [
            {"name": "生ビール（プレミアムモルツ）", "price": 450, "weight": 35},
            {"name": "こだわり酒場のレモンサワー", "price": 380, "weight": 40},
            {"name": "角ハイボール", "price": 400, "weight": 30},
            {"name": "芋焼酎（黒霧島）ロック", "price": 420, "weight": 15},
            {"name": "クラフトビール（週替わり）", "price": 600, "weight": 10},
            {"name": "ウーロンハイ", "price": 380, "weight": 20},
            {"name": "日本酒（本醸造）1合", "price": 480, "weight": 12},
        ],
        "ソフトドリンク": [
            {"name": "ウーロン茶", "price": 280, "weight": 5},
            {"name": "緑茶", "price": 280, "weight": 5},
            {"name": "コーラ", "price": 300, "weight": 5},
        ],
        "フード": [
            {"name": "自家製 酢もつ", "price": 300, "weight": 25},
            {"name": "博多明太子きゅうり", "price": 350, "weight": 20},
            {"name": "冷やしトマト", "price": 280, "weight": 20},
            {"name": "枝豆（塩茹で）", "price": 250, "weight": 30},
            {"name": "名物！牛すじ煮込み", "price": 480, "weight": 45},
            {"name": "炭火焼き鳥（ねぎま2本）", "price": 380, "weight": 35},
            {"name": "ジューシー唐揚げ（3個）", "price": 420, "weight": 30},
            {"name": "鉄板餃子（6個）", "price": 450, "weight": 25},
            {"name": "ポテトフライ（塩あじ）", "price": 350, "weight": 20},
            {"name": "ハムカツ（厚切り）", "price": 320, "weight": 25},
        ],
        "デザート": [
            {"name": "バニラアイス", "price": 200, "weight": 2},
            {"name": "抹茶アイス", "price": 220, "weight": 2},
        ],
    }

    # 📅 2024年1月1日 〜 2026年6月30日 までの全日付を計算
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 6, 30)
    total_days = (end_date - start_date).days + 1

    current_receipt = 100001
    total_rows = 0

    with open(output_filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        # 既存のインポート機能が読み込める元のヘッダー列順
        writer.writerow(
            ["receipt_no", "date", "product", "category", "price", "quantity"]
        )

        # 🔄 2024年1月1日から1日ずつ順番にループを回す
        for day_idx in range(total_days):
            current_date = start_date + timedelta(days=day_idx)
            date_str = current_date.strftime("%Y-%m-%d")
            weekday = current_date.weekday()

            # 曜日ごとの客数の波（金土は忙しく、月火は少なめ）
            customer_weight = 1.0
            if weekday == 4:  # 金
                customer_weight = 1.8
            elif weekday == 5:  # 土
                customer_weight = 1.5
            elif weekday in [0, 1]:  # 月火
                customer_weight = 0.7

            # 1日あたりのレシート枚数（客数）を決定
            num_receipts_today = int(random.randint(22, 35) * customer_weight)

            # その日の客数分お会計を発生させる
            for _ in range(num_receipts_today):
                receipt_str = f"REC{current_receipt}"

                # 1回あたりの注文品数（平日はサクッと、金土は多め）
                if weekday in [4, 5]:
                    item_count = random.randint(5, 7)
                else:
                    item_count = random.randint(3, 5)

                for i in range(item_count):
                    if i == 0:
                        cat = "ドリンク"  # 最初は必ず一杯目
                    else:
                        cat = random.choices(
                            ["ドリンク", "フード", "ソフトドリンク", "デザート"],
                            weights=[48, 48, 3, 1],
                        )[0]

                    choices = PRODUCTS[cat]
                    weights = [item["weight"] for item in choices]

                    product = random.choices(choices, weights=weights)[0]
                    quantity = random.choices([1, 2], weights=[92, 8])[0]

                    writer.writerow(
                        [
                            receipt_str,
                            date_str,
                            product["name"],
                            cat,
                            product["price"],
                            quantity,
                        ]
                    )
                    total_rows += 1

                current_receipt += 1

    print(
        f"✨ 成功: {start_date.strftime('%Y/%m')}〜{end_date.strftime('%Y/%m')}の【毎日】のデータを生成しました！"
    )
    print(f"📊 総お会計数: {current_receipt - 100001:,} 件 / 総データ行数: {total_rows:,} 行")


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 元と同じ「sample_sales_v2.csv」を bi_dashboard の直下に出力します
    target_path = os.path.join(current_dir, "sample_sales_v2.csv")
    generate_daily_pos_data(output_filename=target_path)