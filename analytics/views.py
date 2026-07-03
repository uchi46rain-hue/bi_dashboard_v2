import datetime
import csv
import io
import requests
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db import transaction
from django.db.models import Sum, Count, F, ExpressionWrapper, IntegerField, Min, Max
from django.db.models.functions import ExtractWeekDay, TruncMonth
from .models import Sale, Product
from .forms import CSVUploadForm

def download_csv_template(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="pos_data_template.csv"'
    writer = csv.writer(response)
    writer.writerow(['receipt_no', 'date', 'product', 'category', 'price', 'quantity'])
    return response


def get_fukuoka_night_weather_api(start_date, end_date):
    """
    Open-Meteoから指定期間の福岡の毎時気象データを取得。
    17:00〜24:00（23:59）の時間帯のみを抽出して、夜間天気と平均気温を判定。
    """
    start_str = start_date.strftime('%Y-%m-%d')
    today = datetime.date(2026, 7, 1)
    if end_date >= today:
        end_date = today - datetime.timedelta(days=1)
    end_str = end_date.strftime('%Y-%m-%d')

    url = f"https://archive-api.open-meteo.com/v1/archive?latitude=33.6064&longitude=130.4182&start_date={start_str}&end_date={end_str}&hourly=weather_code,temperature_2m&timezone=Asia%2FTokyo"
    
    weather_mapping = {}
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            hourly = data.get('hourly', {})
            times = hourly.get('time', [])
            weather_codes = hourly.get('weather_code', [])
            temperatures = hourly.get('temperature_2m', [])
            
            daily_chunks = {}
            for i, time_str in enumerate(times):
                dt = datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
                date_key = dt.date()
                hour = dt.hour
                
                if date_key not in daily_chunks:
                    daily_chunks[date_key] = {"codes": [], "temps": []}
                
                if 17 <= hour <= 23:
                    daily_chunks[date_key]["codes"].append(weather_codes[i])
                    daily_chunks[date_key]["temps"].append(temperatures[i])
            
            for date_key, chunk in daily_chunks.items():
                codes = chunk["codes"]
                temps = chunk["temps"]
                if not codes: continue
                
                avg_night_temp = round(sum(temps) / len(temps), 1) if temps else 20.0
                
                rain_hours = sum(1 for c in codes if c >= 51)
                cloud_hours = sum(1 for c in codes if c in [3, 45, 48])
                clear_hours = sum(1 for c in codes if c in [0, 1, 2])
                
                if rain_hours >= 2 or (rain_hours >= 1 and max(codes) >= 61):
                    night_weather = "雨"
                elif cloud_hours > clear_hours:
                    night_weather = "曇り"
                else:
                    night_weather = "晴れ"
                
                weather_mapping[date_key] = {
                    'weather': night_weather,
                    'temperature': avg_night_temp
                }
    except Exception:
        pass
        
    return weather_mapping


def dashboard(request):
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']
            data_set = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(data_set)
            reader = csv.reader(io_string)
            header = next(reader)
            
            rows = [row for row in reader if row]
            
            if rows:
                dates = [datetime.datetime.strptime(r[1], '%Y-%m-%d').date() for r in rows]
                upload_min_date = min(dates)
                upload_max_date = max(dates)
                
                weather_api_map = get_fukuoka_night_weather_api(upload_min_date, upload_max_date)
                
                product_cache = {p.name: p for p in Product.objects.all()}
                aggregated_sales = {}
                
                for row in rows:
                    receipt_no, date_str, prod_name, cat, price, qty = row
                    current_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    if prod_name not in product_cache:
                        product = Product.objects.create(name=prod_name, category=cat, price=int(price))
                        product_cache[prod_name] = product
                    else:
                        product = product_cache[prod_name]
                    
                    unique_key = (receipt_no, current_date, product.id)
                    
                    if unique_key in aggregated_sales:
                        aggregated_sales[unique_key]['quantity'] += int(qty)
                    else:
                        api_info = weather_api_map.get(current_date, {'weather': '晴れ', 'temperature': 20.0})
                        aggregated_sales[unique_key] = {
                            'receipt_no': receipt_no,
                            'date': current_date,
                            'product': product,
                            'quantity': int(qty),
                            'weather': api_info['weather'],
                            'temperature': api_info['temperature']
                        }
                
                sales_to_create = [
                    Sale(
                        receipt_no=data['receipt_no'],
                        date=data['date'],
                        product=data['product'],
                        quantity=data['quantity'],
                        weather=data['weather'],
                        temperature=data['temperature']
                    )
                    for data in aggregated_sales.values()
                ]
                
                with transaction.atomic():
                    if sales_to_create:
                        Sale.objects.bulk_create(sales_to_create, batch_size=10000)
            
            return redirect('dashboard')
    else:
        form = CSVUploadForm()

    # ------------------------------------------------------------------
    # リクエストパラメータの取得
    # ------------------------------------------------------------------
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    selected_category = request.GET.get('category', '')
    selected_weather = request.GET.get('weather', '')
    display_type = request.GET.get('display_type', 'amount')  # 'amount' または 'quantity'

    date_bounds = Sale.objects.aggregate(min_d=Min('date'), max_d=Max('date'))
    min_date = date_bounds['min_d'] or datetime.date(2024, 1, 1)
    max_date = date_bounds['max_d'] or datetime.date(2026, 7, 1)

    duration_queryset = Sale.objects.all()
    if start_date_str:
        try:
            filter_start = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            duration_queryset = duration_queryset.filter(date__gte=filter_start)
            min_date = filter_start
        except ValueError:
            start_date_str = ''

    if end_date_str:
        try:
            filter_end = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
            duration_queryset = duration_queryset.filter(date__lte=filter_end)
            max_date = filter_end
        except ValueError:
            end_date_str = ''

    prev_date_str = (min_date - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    next_date_str = (min_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

    # 基本アノテーション（売上金額と丸め年月）
    sales_queryset = duration_queryset.select_related('product').annotate(
        total_price=ExpressionWrapper(F('quantity') * F('product__price'), output_field=IntegerField()),
        month_period=TruncMonth('date'),
        extracted_weekday=ExtractWeekDay('date')
    )

    # フィルター適用
    if selected_category:
        sales_queryset = sales_queryset.filter(product__category=selected_category)
    if selected_weather:
        sales_queryset = sales_queryset.filter(weather=selected_weather)

    # 【重要】表示タイプ（金額ベース or 個数ベース）による動的切り替え
    target_field = 'total_price' if display_type == 'amount' else 'quantity'
    display_label = "売上金額" if display_type == 'amount' else "売上個数"
    display_unit = "円" if display_type == 'amount' else "個"
    
    # 全体基本統計の算出
    metrics = sales_queryset.aggregate(
        total_sales=Sum('total_price'),
        total_qty=Sum('quantity'),
        total_cust=Count('receipt_no', distinct=True)
    )
    total_sales = metrics['total_sales'] or 0
    total_quantity = metrics['total_qty'] or 0
    total_customers = metrics['total_cust'] or 0
    
    customer_price = int(total_sales / total_customers) if total_customers > 0 else 0
    avg_purchase_items = round(total_quantity / total_customers, 1) if total_customers > 0 else 0.0
    
    # グラフ用：月別推移（年・月を完全分離）
    monthly_sales_qs = sales_queryset.values('month_period').annotate(total=Sum(target_field)).order_by('month_period')
    monthly_sales = [
        {
            'month': item['month_period'].strftime('%Y-%m') if item['month_period'] else '', 
            'total': item['total']
        } 
        for item in monthly_sales_qs if item['month_period']
    ]
    
    # グラフ用：カテゴリ別・商品別
    category_sales = sales_queryset.values('product__category').annotate(total=Sum(target_field)).order_by('-total')
    product_sales = sales_queryset.values('product__name').annotate(total=Sum(target_field)).order_by('-total')[:10]
    
    # グラフ用：曜日別
    WEEKDAY_MAP = {1: '日', 2: '月', 3: '火', 4: '水', 5: '木', 6: '金', 7: '土'}
    weekday_sales_qs = sales_queryset.values('extracted_weekday').annotate(total=Sum(target_field)).order_by('extracted_weekday')
    weekday_sales = [{'weekday': WEEKDAY_MAP.get(item['extracted_weekday'], ''), 'total': item['total']} for item in weekday_sales_qs]
    
    # グラフ用：天気別
    weather_sales_qs = sales_queryset.values('weather').annotate(total=Sum(target_field))
    weather_sales = [{'weather': item['weather'] if item['weather'] else '晴れ', 'total': item['total']} for item in weather_sales_qs]
    
    # 営業日数のカウント処理
    days_qs = sales_queryset.values('date', 'weather').distinct()
    weather_days = {"晴れ": 0, "曇り": 0, "雨": 0}
    for d in days_qs:
        w = d['weather'] if d['weather'] else "晴れ"
        if w in weather_days:
            weather_days[w] += 1
    total_days = sum(weather_days.values())

    # グラフ用：気温別（5℃刻み）
    temp_sales_dict = {}
    for s in sales_queryset.values('temperature', target_field):
        t = s['temperature']
        if t is not None:
            group_base = int(float(t) // 5) * 5
            temp_sales_dict[group_base] = temp_sales_dict.get(group_base, 0) + s[target_field]
    temperature_sales = [{'temp_range': f"{k}℃〜{k+5}℃", 'total': v} for k, v in sorted(temp_sales_dict.items())]

    product_count = sales_queryset.values('product').distinct().count()
    category_count = sales_queryset.values('product__category').distinct().count()

    # ------------------------------------------------------------------
    # フィルター連動型・動的AI分析インサイトの生成（ロジック強化版）
    # ------------------------------------------------------------------
    filters_active = []
    if start_date_str or end_date_str: filters_active.append(f"期間: {min_date}〜{max_date}")
    if selected_category: filters_active.append(f"カテゴリ: {selected_category}")
    if selected_weather: filters_active.append(f"夜間天気: {selected_weather}")
    filter_desc = f"［ {' ・ '.join(filters_active)} ］" if filters_active else "［ 全データ対象 ］"

    # 動的インサイトメッセージの構築
    current_focus_total = total_sales if display_type == 'amount' else total_quantity
    
    ai_comments = [
        f"🎯 現在の分析視点：【{display_label}ベース】 {filter_desc}",
        f"📊 条件合致データの総{display_label}は {current_focus_total:,}{display_unit} （客数: {total_customers:,}人 / 客単価: ¥{customer_price:,} / 平均客単商品数: {avg_purchase_items}個）です。"
    ]

    # コンテキストに応じた分析インサイトの動的追加
    if selected_weather:
        avg_per_day = int(current_focus_total / total_days) if total_days > 0 else 0
        ai_comments.append(
            f"💡 【天気特化分析】夜間天気が「{selected_weather}」の営業日は計 {total_days} 日存在します。1日あたりの平均{display_label}は {avg_per_day:,}{display_unit} となっています。"
        )
    else:
        # 天気未選択時は、最も売上（または個数）シェアの高い天気を特定
        if weather_sales:
            top_weather = max(weather_sales, key=lambda x: x['total'])
            ai_comments.append(
                f"☀️ 【夜間天気相関】全期間中で最も{display_label}を牽引している天気は「{top_weather['weather']}」で、該当期間の総計は {top_weather['total']:,}{display_unit} です。"
            )

    if selected_category:
        if product_sales:
            top_prod = product_sales[0]
            ai_comments.append(
                f"📦 【カテゴリ内分析】「{selected_category}」セグメント内のエース商品は「{top_prod['product__name']}」であり、この単一商品で {top_prod['total']:,}{display_unit} を計上しています。"
            )
    else:
        if category_sales:
            top_cat = category_sales[0]
            ai_comments.append(
                f"🏆 【部門別シェア】現在、売上構造のトップは「{top_cat['product__category']}」カテゴリで、{top_cat['total']:,}{display_unit} を記録しています。"
            )

    context = {
        'form': form,
        'total_sales': f"{total_sales:,}",
        'total_quantity': f"{total_quantity:,}",
        'total_customers': f"{total_customers:,}",
        'customer_price': f"{customer_price:,}",
        'avg_purchase_items': avg_purchase_items,
        'product_count': product_count,
        'category_count': category_count,
        'monthly_sales': monthly_sales,
        'category_sales': category_sales,
        'product_sales': product_sales,
        'weekday_sales': weekday_sales,
        'weather_sales': weather_sales,
        'temperature_sales': temperature_sales,
        'ai_comments': ai_comments,
        'selected_category': selected_category,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'selected_weather': selected_weather,
        'display_type': display_type,
        'prev_date': prev_date_str,
        'next_date': next_date_str,
        'weather_days': weather_days,
        'total_days': total_days,
    }

    return render(request, "analytics/dashboard.html", context)