from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db import connection

# --- ІМПОРТИ АНАЛІТИКИ ---
import pandas as pd
import plotly.express as px
import time
import concurrent.futures

# Імпорти для Bokeh
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.resources import CDN
# Імпорти моделей
from tickets.models import Passenger, Cashier, Trip, Ticket
from tickets.repositories import RepositoryManager

repo = RepositoryManager()
from django.shortcuts import redirect

def my_view(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    return render(request, 'web/login.html')


# ==========================================
# 1. АВТОРИЗАЦІЯ
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

# ==========================================
# 2. ГОЛОВНА
# ==========================================

def home(request):
    return render(request, 'web/home.html')

# ==========================================
# 3. DASHBOARD V1 (PLOTLY)
# ==========================================

def dashboard_view(request):
    analytics = repo.get_complex_analytics()
    min_rev = request.GET.get('min_revenue')
    graphs = {}

    # 1. Прибуток (Bar)
    df1 = pd.DataFrame(list(analytics['revenue_by_trip'].values('start_station', 'end_station', 'total_revenue')))
    df1 = df1.fillna(0)
    if not df1.empty:
        df1['total_revenue'] = df1['total_revenue'].astype(float)
        if min_rev:
            try: df1 = df1[df1['total_revenue'] >= float(min_rev)]
            except: pass
        df1['route'] = df1['start_station'] + "-" + df1['end_station']
        fig = px.bar(df1, x='route', y='total_revenue', title="1. Прибуток рейсів", color='total_revenue')
        graphs['g1'] = fig.to_html(full_html=False)

    # 2. Касири (Pie)
    df2 = pd.DataFrame(list(analytics['cashier_performance'].values('first_name', 'last_name', 'total_sales')))
    df2 = df2.fillna(0)
    if not df2.empty:
        df2['total_sales'] = df2['total_sales'].astype(float)
        df2['name'] = df2['first_name'] + " " + df2['last_name']
        fig = px.pie(df2, values='total_sales', names='name', title="2. Продажі касирів")
        graphs['g2'] = fig.to_html(full_html=False)

    # 3. Завантаженість (Bar)
    df3 = pd.DataFrame(list(analytics['trip_occupancy'].values('start_station', 'end_station', 'occupancy_rate')))
    df3 = df3.fillna(0)
    if not df3.empty:
        df3['occupancy_rate'] = df3['occupancy_rate'].astype(float)
        df3['route'] = df3['start_station'] + "-" + df3['end_station']
        fig = px.bar(df3, x='route', y='occupancy_rate', title="3. Завантаженість %", range_y=[0, 100])
        graphs['g3'] = fig.to_html(full_html=False)

    # 4. Типи (Scatter)
    df4 = pd.DataFrame(list(analytics['train_type_stats'].values('train_type', 'avg_passenger_age', 'max_ticket_price')))
    df4 = df4.fillna(0)
    if not df4.empty:
        df4['max'] = df4['max_ticket_price'].astype(float)
        df4['age'] = df4['avg_passenger_age'].astype(float)
        fig = px.scatter(df4, x='age', y='max', size='max', color='train_type', title="4. Вік vs Ціна", size_max=50)
        graphs['g4'] = fig.to_html(full_html=False)

    # 5. Місяці (Line)
    df5 = pd.DataFrame(list(analytics['sales_by_month'].values('month', 'tickets_sold')))
    df5 = df5.fillna(0)
    if not df5.empty:
        df5 = df5.sort_values('month')
        fig = px.line(df5, x='month', y='tickets_sold', markers=True, title="5. Продажі по місяцях")
        graphs['g5'] = fig.to_html(full_html=False)

    # 6. VIP (Horizontal Bar)
    df6 = pd.DataFrame(list(analytics['top_passengers'].values('first_name', 'last_name', 'total_spent')))
    df6 = df6.fillna(0)
    if not df6.empty:
        df6['sum'] = df6['total_spent'].astype(float)
        df6['name'] = df6['first_name'] + " " + df6['last_name']
        fig = px.bar(df6, x='sum', y='name', orientation='h', title="6. VIP Клієнти")
        graphs['g6'] = fig.to_html(full_html=False)

    return render(request, 'web/dashboard.html', {'graphs': graphs})

# ==========================================
# 4. DASHBOARD V2 (BOKEH) - ВИПРАВЛЕНО
# ==========================================

def dashboard_bokeh_view(request):
    analytics = repo.get_complex_analytics()
    plots = {}

    # === 1. Прибуток (Bar) ===
    raw_data = list(analytics['revenue_by_trip'].values('id', 'start_station', 'end_station', 'total_revenue'))
    if raw_data:
        routes = [f"{i['start_station']}-{i['end_station']} (#{i['id']})" for i in raw_data]
        revenues = [float(i['total_revenue'] or 0) for i in raw_data]
        
        source = ColumnDataSource(data=dict(x=routes, y=revenues))
        p = figure(x_range=routes, height=300, title="1. Прибуток (Bokeh)")
        p.vbar(x='x', top='y', width=0.5, source=source, color="#390650")
        p.add_tools(HoverTool(tooltips=[("Рейс", "@x"), ("Сума", "@y")]))
        plots['s1'], plots['d1'] = components(p)

    # === 2. Касири (Bar) ===
    raw_data = list(analytics['cashier_performance'].values('first_name', 'last_name', 'total_sales'))
    if raw_data:
        names = [f"{i['first_name']} {i['last_name']}" for i in raw_data]
        sales = [float(i['total_sales'] or 0) for i in raw_data]
        
        source = ColumnDataSource(data=dict(x=names, y=sales))
        p = figure(x_range=names, height=300, title="2. Касири")
        p.vbar(x='x', top='y', width=0.5, source=source, color="teal")
        plots['s2'], plots['d2'] = components(p)

    # === 3. Завантаженість (Bar) ===
    raw_data = list(analytics['trip_occupancy'].values('id', 'start_station', 'end_station', 'occupancy_rate'))
    if raw_data:
        routes = [f"{i['start_station']}-{i['end_station']} (#{i['id']})" for i in raw_data]
        rates = [float(i['occupancy_rate'] or 0) for i in raw_data]
        
        source = ColumnDataSource(data=dict(x=routes, y=rates))
        p = figure(x_range=routes, height=300, title="3. Завантаженість %")
        p.vbar(x='x', top='y', width=0.5, source=source, color="orange")
        plots['s3'], plots['d3'] = components(p)

    # === 4. Типи (Scatter) ===
    raw_data = list(analytics['train_type_stats'].values('train_type', 'avg_passenger_age', 'max_ticket_price'))
    if raw_data:
        ages = [float(i['avg_passenger_age'] or 0) for i in raw_data]
        prices = [float(i['max_ticket_price'] or 0) for i in raw_data]
        types = [i['train_type'] for i in raw_data]
        
        source = ColumnDataSource(data=dict(x=ages, y=prices, t_type=types))
        p = figure(height=300, title="4. Ціна vs Вік")
        p.circle(x='x', y='y', size=15, source=source, color="firebrick", alpha=0.6)
        p.add_tools(HoverTool(tooltips=[("Тип", "@t_type"), ("Вік", "@x"), ("Ціна", "@y")]))
        plots['s4'], plots['d4'] = components(p)

    # === 5. Місяці (Line) ===
    raw_data = list(analytics['sales_by_month'].values('month', 'tickets_sold'))
    if raw_data:
        raw_data.sort(key=lambda x: x['month'])
        months = [i['month'] for i in raw_data]
        sold = [i['tickets_sold'] for i in raw_data]
        
        source = ColumnDataSource(data=dict(x=months, y=sold))
        p = figure(height=300, title="5. Продажі по місяцях")
        p.line(x='x', y='y', line_width=2, source=source)
        p.circle(x='x', y='y', size=8, source=source)
        plots['s5'], plots['d5'] = components(p)

    # === 6. VIP (H-Bar) ===
    raw_data = list(analytics['top_passengers'].values('first_name', 'last_name', 'total_spent'))
    if raw_data:
        names = [f"{i['first_name']} {i['last_name']}" for i in raw_data]
        spent = [float(i['total_spent'] or 0) for i in raw_data]
        
        source = ColumnDataSource(data=dict(y=names, right=spent))
        p = figure(y_range=names, height=300, title="6. VIP Клієнти")
        p.hbar(y='y', right='right', height=0.5, source=source, color="purple")
        plots['s6'], plots['d6'] = components(p)

    # 1. ГЕНЕРУЄМО ПРАВИЛЬНИЙ JS СКРИПТ (Автоматично)
    resources = CDN.render()

    return render(request, 'web/dashboard_bokeh.html', {'plots': plots, 'resources': resources})
# ==========================================
# 5. PERFORMANCE
# ==========================================

def performance_view(request):
    request_count = 100
    results = []
    graph = None
    
    if request.GET.get('run'):
        def task(n):
            _ = list(Ticket.objects.values_list('id', flat=True))
            connection.close() 

        for workers in [1, 2, 4, 8]:
            start = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
                list(ex.map(task, range(request_count)))
            results.append({'workers': workers, 'time': time.time() - start})
        
        df = pd.DataFrame(results)
        fig = px.line(df, x='workers', y='time', markers=True, title=f"Час виконання {request_count} запитів")
        graph = fig.to_html(full_html=False)

    return render(request, 'web/performance.html', {'graph': graph})

# ==========================================
# 6. CRUD VIEWS
# ==========================================

class PassengerListView(ListView):
    model = Passenger
    template_name = 'web/passenger_list.html'
    context_object_name = 'passengers'
    paginate_by = 40

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
    paginate_by = 40

class TripListView(ListView):
    model = Trip
    template_name = 'web/trip_list.html'
    context_object_name = 'trips'
    paginate_by = 40

class TicketsListView(ListView):
    model = Ticket
    template_name = 'web/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 40
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