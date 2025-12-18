from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db import connection

# --- АНАЛІТИКА ---
import pandas as pd
import plotly.express as px
import time
import concurrent.futures
from math import pi

# --- BOKEH ---
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models import ColumnDataSource, HoverTool, LinearColorMapper
from bokeh.transform import cumsum, transform
from bokeh.resources import CDN
from bokeh.palettes import Category20c, Viridis256

# --- МОДЕЛІ ---
from tickets.models import Passenger, Cashier, Trip, Ticket
from tickets.repositories import RepositoryManager

import psutil
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots


repo = RepositoryManager()

# ==========================================
# 1. АВТОРИЗАЦІЯ І ГОЛОВНА
# ==========================================

class CustomLoginView(LoginView):
    template_name = 'web/login.html'
    next_page = 'home'

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'web/register.html', {'form': form})

def home(request):
    return render(request, 'web/home.html')

# ==========================================
# 2. DASHBOARD V1 (PLOTLY)
# ==========================================

def dashboard_view(request):
    analytics = repo.get_complex_analytics()
    graphs = {}

    # --- ОТРИМАННЯ ФІЛЬТРІВ ---
    min_revenue = float(request.GET.get('min_revenue', 0))
    min_occupancy = float(request.GET.get('min_occupancy', 0))
    top_n = int(request.GET.get('top_n', 10))
    filter_type = request.GET.get('train_type', 'All')

    # === 1. Прибуток (Bar) ===
    df1 = pd.DataFrame(list(analytics['revenue_by_trip'].values('id', 'number', 'start_station', 'end_station', 'total_revenue')))
    df1 = df1.fillna(0)
    
    if not df1.empty:
        df1['total_revenue'] = df1['total_revenue'].astype(float)
        
        # Фільтр: Мін. прибуток
        df1 = df1[df1['total_revenue'] >= min_revenue]
        
        # Логіка назв
        def get_short_name(row):
            num = row['number']
            if num and str(num).lower() != 'none' and str(num).strip() != '':
                return str(num)
            return f"#{row['id']}"

        if not df1.empty:
            df1['short_name'] = df1.apply(get_short_name, axis=1)
            df1['full_route'] = df1['start_station'] + " - " + df1['end_station']
            
            fig = px.bar(
                df1, 
                x='short_name', 
                y='total_revenue', 
                title=f"1. Прибуток рейсів (> {min_revenue} грн)", 
                color='total_revenue',
                hover_name='full_route',
                labels={'short_name': 'Рейс', 'total_revenue': 'Прибуток (грн)'}
            )
            graphs['g1'] = fig.to_html(full_html=False)

    # === 2. Касири (Pie) ===
    df2 = pd.DataFrame(list(analytics['cashier_performance'].values('first_name', 'last_name', 'total_sales')))
    df2 = df2.fillna(0)
    if not df2.empty:
        df2['total_sales'] = df2['total_sales'].astype(float)
        df2['name'] = df2['first_name'] + " " + df2['last_name']
        fig = px.pie(df2, values='total_sales', names='name', title="2. Продажі касирів")
        graphs['g2'] = fig.to_html(full_html=False)

    # === 3. Завантаженість (Bar) ===
    df3 = pd.DataFrame(list(analytics['trip_occupancy'].values('id', 'number', 'occupancy_rate')))
    df3 = df3.fillna(0)
    if not df3.empty:
        df3['occupancy_rate'] = df3['occupancy_rate'].astype(float)
        
        # Фільтр: Завантаженість
        df3 = df3[df3['occupancy_rate'] >= min_occupancy]

        if not df3.empty:
            def get_route_name(row):
                num = row['number']
                if num and str(num).lower() != 'none' and str(num).strip() != '':
                    return str(num)
                return f"#{row['id']}"

            df3['route'] = df3.apply(get_route_name, axis=1)
            
            fig = px.bar(df3, x='route', y='occupancy_rate', title=f"3. Завантаженість > {min_occupancy}%", range_y=[0, 100])
            graphs['g3'] = fig.to_html(full_html=False)

    # === 4. Типи (Scatter) ===
    df4 = pd.DataFrame(list(analytics['train_type_stats'].values('train_type', 'avg_passenger_age', 'max_ticket_price')))
    df4 = df4.fillna(0)
    if not df4.empty:
        # Фільтр: Тип потяга
        if filter_type != 'All':
            df4 = df4[df4['train_type'] == filter_type]

        if not df4.empty:
            df4['max'] = df4['max_ticket_price'].astype(float)
            df4['age'] = df4['avg_passenger_age'].astype(float)
            fig = px.scatter(df4, x='age', y='max', size='max', color='train_type', title="4. Вік vs Ціна", size_max=60)
            graphs['g4'] = fig.to_html(full_html=False)

    # === 5. Місяці (Line) ===
    df5 = pd.DataFrame(list(analytics['sales_by_month'].values('month', 'tickets_sold')))
    df5 = df5.fillna(0)
    if not df5.empty:
        df5 = df5.sort_values('month')
        fig = px.line(df5, x='month', y='tickets_sold', markers=True, title="5. Продажі по місяцях")
        graphs['g5'] = fig.to_html(full_html=False)

    # === 6. VIP (Horizontal Bar) ===
    df6 = pd.DataFrame(list(analytics['top_passengers'].values('id', 'first_name', 'last_name', 'total_spent')))
    df6 = df6.fillna(0)
    if not df6.empty:
        df6['sum'] = df6['total_spent'].astype(float)
        df6['name'] = df6['first_name'] + " " + df6['last_name'] + " (#" + df6['id'].astype(str) + ")"
        
        # Сортування і Фільтр Топ-N
        df6 = df6.sort_values('sum', ascending=True) # Plotly малює знизу вгору
        df6 = df6.tail(top_n) # Беремо N найбільших

        fig = px.bar(df6, x='sum', y='name', orientation='h', title=f"6. Топ-{top_n} VIP Клієнтів")
        graphs['g6'] = fig.to_html(full_html=False)

    # Список типів для меню
    all_types = list(Trip.objects.values_list('train_type', flat=True).distinct())

    return render(request, 'web/dashboard.html', {
        'graphs': graphs,
        'min_revenue': int(min_revenue),
        'min_occupancy': int(min_occupancy),
        'top_n': top_n,
        'selected_type': filter_type,
        'all_types': all_types
    })

# ==========================================
# 3. DASHBOARD V2 (BOKEH) - MAXIMUM INTERACTIVITY
# ==========================================

def dashboard_bokeh_view(request):
    analytics = repo.get_complex_analytics()
    plots = {}
    
    # Отримуємо значення з GET, якщо пусто - ставимо 0
    try: min_revenue = float(request.GET.get('min_revenue', 0) or 0)
    except: min_revenue = 0.0

    try: min_occupancy = float(request.GET.get('min_occupancy', 0) or 0)
    except: min_occupancy = 0.0

    try: top_n = int(request.GET.get('top_n', 10) or 10)
    except: top_n = 10
    
    filter_type = request.GET.get('train_type', 'All')
    
    TOOLS = "pan,wheel_zoom,box_zoom,reset,save"

    # === 1. Прибуток (LOLLIPOP) ===
    raw_data = list(analytics['revenue_by_trip'].values('id', 'number', 'start_station', 'end_station', 'total_revenue'))
    
    # Фільтрація по прибутку
    raw_data = [d for d in raw_data if float(d['total_revenue'] or 0) >= min_revenue]

    if raw_data:
        x_axis = []
        routes = []
        revenues = []
        
        for i in raw_data:
            num = i['number']
            if num and str(num).lower() != 'none' and str(num).strip() != '':
                # ВАЖЛИВО: Додаємо ID, щоб назва була унікальною!
                # Інакше Bokeh зникне, якщо є два рейси з однаковим номером.
                display_num = f"{num} (id:{i['id']})"
            else:
                display_num = f"#{i['id']}"
            
            x_axis.append(display_num)
            routes.append(f"{i['start_station']}-{i['end_station']}")
            revenues.append(float(i['total_revenue'] or 0))
        
        source = ColumnDataSource(data=dict(x=x_axis, y=revenues, route=routes))
        p = figure(x_range=x_axis, height=350, title=f"1. Прибуток > {min_revenue} грн", 
                   toolbar_location="right", tools=TOOLS)
        
        p.segment(x0='x', y0=0, x1='x', y1='y', line_width=2, color="#390650", source=source)
        p.circle(x='x', y='y', size=15, fill_color="#390650", line_color="white", line_width=2, source=source)
        p.add_tools(HoverTool(tooltips=[("Рейс", "@x"), ("Маршрут", "@route"), ("Сума", "@y{0.00} грн")]))
        plots['s1'], plots['d1'] = components(p)

    # === 2. Касири (DONUT) ===
    raw_data = list(analytics['cashier_performance'].values('first_name', 'last_name', 'total_sales'))
    if raw_data:
        data = pd.DataFrame(raw_data)
        data['total_sales'] = data['total_sales'].astype(float).fillna(0)
        data['name'] = data['first_name'] + ' ' + data['last_name']
        data['angle'] = data['total_sales'] / data['total_sales'].sum() * 2 * pi
        
        # Безпечні кольори (щоб не було помилок індексу)
        colors_list = Category20c[20]
        data['color'] = [colors_list[i % 20] for i in range(len(data))]
        
        source = ColumnDataSource(data)
        p = figure(height=350, title="2. Частка продажів касирів", 
                   toolbar_location="right", tools=TOOLS, x_range=(-0.5, 1.0))
        
        p.wedge(x=0, y=1, radius=0.4, start_angle=cumsum('angle', include_zero=True), 
                end_angle=cumsum('angle'), line_color="white", fill_color='color', 
                legend_field='name', source=source)
        
        p.axis.visible = False
        p.grid.grid_line_color = None
        plots['s2'], plots['d2'] = components(p)

    # === 3. Завантаженість (H-BAR) ===
    raw_data = list(analytics['trip_occupancy'].values('id', 'number', 'occupancy_rate'))
    if raw_data:
        filtered_data = [d for d in raw_data if float(d['occupancy_rate'] or 0) >= min_occupancy]
        if filtered_data:
            routes = []
            rates = []
            for d in filtered_data:
                num = d['number']
                if num and str(num).lower() != 'none' and str(num).strip() != '':
                    # ВАЖЛИВО: Унікальна назва
                    display_num = f"{num} (id:{d['id']})"
                else:
                    display_num = f"#{d['id']}"
                
                routes.append(display_num)
                rates.append(float(d['occupancy_rate'] or 0))
            
            source = ColumnDataSource(data=dict(y_routes=routes, right=rates))
            p = figure(y_range=routes, height=350, title=f"3. Завантаженість > {min_occupancy}%", 
                       toolbar_location="right", tools=TOOLS)
            
            mapper = LinearColorMapper(palette=Viridis256, low=0, high=100)
            p.hbar(y='y_routes', right='right', height=0.6, source=source, fill_color=transform('right', mapper))
            p.add_tools(HoverTool(tooltips=[("Рейс", "@y_routes"), ("Заповнено", "@right{0.0}%")]))
            plots['s3'], plots['d3'] = components(p)

    # === 4. Типи (SCATTER) ===
    raw_data = list(analytics['train_type_stats'].values('train_type', 'avg_passenger_age', 'max_ticket_price'))
    if raw_data:
        if filter_type != 'All':
            raw_data = [d for d in raw_data if d['train_type'] == filter_type]
        ages = [float(i['avg_passenger_age'] or 0) for i in raw_data]
        prices = [float(i['max_ticket_price'] or 0) for i in raw_data]
        types = [i['train_type'] for i in raw_data]
        
        source = ColumnDataSource(data=dict(x=ages, y=prices, t_type=types))
        p = figure(height=350, title="4. Ціна vs Вік", toolbar_location="right", tools=TOOLS)
        
        p.circle(x='x', y='y', size=20, source=source, color="firebrick", alpha=0.6)
        p.add_tools(HoverTool(tooltips=[("Тип", "@t_type"), ("Вік", "@x{0.0}"), ("Ціна", "@y{0.00}")]))
        plots['s4'], plots['d4'] = components(p)

    # === 5. Місяці (LINE) ===
    raw_data = list(analytics['sales_by_month'].values('month', 'tickets_sold'))
    if raw_data:
        raw_data.sort(key=lambda x: x['month'])
        months = [i['month'] for i in raw_data]
        sold = [i['tickets_sold'] for i in raw_data]
        
        source = ColumnDataSource(data=dict(x=months, y=sold))
        p = figure(height=350, title="5. Динаміка продажів", toolbar_location="right", tools=TOOLS)
        
        p.line(x='x', y='y', line_width=3, color="green", source=source)
        p.circle(x='x', y='y', size=8, fill_color="white", source=source)
        p.add_tools(HoverTool(tooltips=[("Місяць", "@x"), ("Продано", "@y{0} шт")]))
        plots['s5'], plots['d5'] = components(p)

    # === 6. VIP (H-BAR) ===
    raw_data = list(analytics['top_passengers'].values('id', 'first_name', 'last_name', 'total_spent'))
    if raw_data:
        # Сортування
        raw_data.sort(key=lambda x: float(x['total_spent'] or 0), reverse=True)
        # Топ N
        raw_data = raw_data[:top_n]
        
        # Унікальні імена (додаємо ID)
        names = [f"{i['first_name']} {i['last_name']} (#{i['id']})" for i in raw_data]
        spent = [float(i['total_spent'] or 0) for i in raw_data]
        
        # Розвертаємо для графіка
        names.reverse()
        spent.reverse()

        source = ColumnDataSource(data=dict(y=names, right=spent))
        p = figure(y_range=names, height=350, title=f"6. Топ-{top_n} VIP Клієнтів", toolbar_location="right", tools=TOOLS)
        
        p.hbar(y='y', right='right', height=0.6, source=source, color="purple")
        p.add_tools(HoverTool(tooltips=[("Клієнт", "@y"), ("Витрачено", "@right{0.00} грн")]))
        plots['s6'], plots['d6'] = components(p)

    all_types = list(Trip.objects.values_list('train_type', flat=True).distinct())
    resources = CDN.render()

    return render(request, 'web/dashboard_bokeh.html', {
        'plots': plots, 
        'resources': resources,
        'min_occupancy': int(min_occupancy), 
        'min_revenue': int(min_revenue),
        'top_n': top_n,
        'selected_type': filter_type, 
        'all_types': all_types
    })

# ==========================================
# 4. PERFORMANCE VIEW
# ==========================================

def performance_view(request):
    # Параметри експерименту
    TOTAL_REQUESTS = 200  # Вимога: 100-200 запитів
    BATCH_SIZE = 20       # Розмір "пакету" даних в одному запиті
    
    results = []
    graph = None
    optimal_config = None
    
    if request.GET.get('run'):
        # Отримуємо поточний процес для заміру RAM
        process = psutil.Process(os.getpid())

        # Функція, що виконується в потоці
        def db_task(n):
            # Імітуємо реальну роботу: вибірка пакету даних
            # connection.close() обов'язковий, щоб не вичерпати ліміт з'єднань БД
            try:
                list(Ticket.objects.values_list('id', 'base_price')[:BATCH_SIZE])
            finally:
                connection.close() 

        # Варіанти кількості потоків для пошуку оптимуму
        thread_options = [1, 2, 4, 8, 16, 32, 64]
        
        print(f"Starting benchmark with {TOTAL_REQUESTS} requests...")

        for workers in thread_options:
            # 1. Фіксуємо пам'ять ДО
            mem_before = process.memory_info().rss / 1024 / 1024 # MB
            
            start_time = time.time()
            
            # 2. ЗАПУСК (Алгоритм багатопотоковості)
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                list(executor.map(db_task, range(TOTAL_REQUESTS)))
            
            duration = time.time() - start_time
            
            # 3. Фіксуємо пам'ять ПІСЛЯ
            mem_after = process.memory_info().rss / 1024 / 1024 # MB
            mem_diff = max(0, mem_after - mem_before) # Скільки "з'їли"
            
            # Зберігаємо метрики
            results.append({
                'workers': workers, 
                'time': round(duration, 3), 
                'ram': round(mem_diff, 2)
            })

        # --- АЛГОРИТМ ПОШУКУ ОПТИМАЛЬНОГО ПАРАМЕТРА ---
        # Шукаємо запис з мінімальним часом виконання
        if results:
            optimal_config = min(results, key=lambda x: x['time'])

        # --- ВІЗУАЛІЗАЦІЯ (Dual Axis Chart) ---
        df = pd.DataFrame(results)
        
        # Створюємо графік з двома осями Y
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Лінія 1: Час (Ліва вісь)
        fig.add_trace(
            go.Scatter(
                x=df['workers'], y=df['time'], name="Час (сек)",
                mode='lines+markers', line=dict(color='#dc3545', width=3)
            ),
            secondary_y=False,
        )

        # Лінія 2: RAM (Права вісь)
        fig.add_trace(
            go.Scatter(
                x=df['workers'], y=df['ram'], name="RAM (MB)",
                mode='lines+markers', line=dict(color='#0d6efd', width=3, dash='dot')
            ),
            secondary_y=True,
        )

        # Оформлення
        fig.update_layout(
            title_text=f"Результати тестування ({TOTAL_REQUESTS} запитів)",
            hovermode="x unified",
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
        )

        fig.update_xaxes(title_text="Кількість потоків (Threads)")
        fig.update_yaxes(title_text="<b>Час виконання (с)</b>", secondary_y=False)
        fig.update_yaxes(title_text="<b>Використання RAM (MB)</b>", secondary_y=True)

        graph = fig.to_html(full_html=False)

    return render(request, 'web/performance.html', {
        'graph': graph, 
        'results': results,
        'optimal': optimal_config,
        'request_count': TOTAL_REQUESTS
    })

# ==========================================
# 5. CRUD
# ==========================================

class PassengerListView(ListView):
    model = Passenger
    template_name = 'web/passenger_list.html'
    context_object_name = 'passengers'
    paginate_by = 20

class PassengerCreateView(CreateView):
    model = Passenger
    template_name = 'web/passenger_form.html'
    fields = ['first_name', 'last_name', 'passport', 'age', 'photo']
    success_url = reverse_lazy('passenger_list')

class PassengerUpdateView(UpdateView):
    model = Passenger
    template_name = 'web/passenger_form.html'
    fields = ['first_name', 'last_name', 'passport', 'age', 'photo']
    success_url = reverse_lazy('passenger_list')

class PassengerDeleteView(DeleteView):
    model = Passenger
    template_name = 'web/passenger_confirm_delete.html'
    success_url = reverse_lazy('passenger_list')

class CashierListView(ListView):
    model = Cashier
    template_name = 'web/cashier_list.html'
    context_object_name = 'cashiers'
    paginate_by = 20

class TripListView(ListView):
    model = Trip
    template_name = 'web/trip_list.html'
    context_object_name = 'trips'
    paginate_by = 20

class TicketsListView(ListView):
    model = Ticket
    template_name = 'web/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 20
    def get_queryset(self):
        return Ticket.objects.select_related('trip', 'passenger', 'cashier').all().order_by('-id')

class TicketsDetailView(DetailView):
    model = Ticket
    template_name = 'web/ticket_detail.html'
    context_object_name = 'ticket'

class TicketsCreateView(CreateView):
    model = Ticket
    template_name = 'web/ticket_form.html'
    fields = ['trip', 'passenger', 'cashier', 'base_price', 'payment_method']
    success_url = reverse_lazy('tickets_list')

class TicketsUpdateView(UpdateView):
    model = Ticket
    template_name = 'web/ticket_form.html'
    fields = ['trip', 'passenger', 'cashier', 'base_price', 'payment_method']
    success_url = reverse_lazy('tickets_list')

class TicketsDeleteView(DeleteView):
    model = Ticket
    template_name = 'web/ticket_confirm_delete.html'
    success_url = reverse_lazy('tickets_list')