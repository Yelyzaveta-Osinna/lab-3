from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
import plotly.express as px
import pandas as pd
from .models import Passenger, Cashier, Trip, Ticket
from .repositories import RepositoryManager
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.palettes import Spectral6
import math
import time
import concurrent.futures
from django.db import connection
# your_app/views.py
from django.contrib.auth.decorators import login_required

from django.contrib.auth.mixins import LoginRequiredMixin


repo = RepositoryManager()

@login_required
def my_protected_view(request):
    # Цей код буде доступний лише авторизованим користувачам
    
    def dashboard_bokeh_view(request):
        analytics_qs = repo.get_complex_analytics()
        plots = {}

        # === 1. Прибуток по рейсах (Bar) ===
        df1 = pd.DataFrame(list(analytics_qs['revenue_by_trip'].values('start_station', 'end_station', 'total_revenue')))
        df1 = df1.fillna(0) # Захист від пустих даних
        
        if not df1.empty:
            # ОБОВ'ЯЗКОВО: Decimal -> float
            df1['total_revenue'] = df1['total_revenue'].astype(float)
            df1['route'] = df1['start_station'] + " - " + df1['end_station']
            
            source1 = ColumnDataSource(df1)
            # x_range потрібен для текстових осей (категорій)
            p1 = figure(x_range=df1['route'], height=350, title="1. Прибуток рейсів (Bokeh)", toolbar_location="above")
            p1.vbar(x='route', top='total_revenue', width=0.5, source=source1, color="#390650")
            p1.add_tools(HoverTool(tooltips=[("Маршрут", "@route"), ("Сума", "@total_revenue")]))
            plots['script1'], plots['div1'] = components(p1)

        # === 2. Касири (Bar) ===
        df2 = pd.DataFrame(list(analytics_qs['cashier_performance'].values('first_name', 'last_name', 'total_sales')))
        df2 = df2.fillna(0)
        
        if not df2.empty:
            df2['total_sales'] = df2['total_sales'].astype(float)
            df2['cashier'] = df2['first_name'] + " " + df2['last_name']
            
            source2 = ColumnDataSource(df2)
            p2 = figure(x_range=df2['cashier'], height=350, title="2. Продажі касирів", toolbar_location="above")
            p2.vbar(x='cashier', top='total_sales', width=0.5, source=source2, color="teal")
            plots['script2'], plots['div2'] = components(p2)

        # === 3. Завантаженість (Bar) ===
        df3 = pd.DataFrame(list(analytics_qs['trip_occupancy'].values('start_station', 'end_station', 'occupancy_rate')))
        df3 = df3.fillna(0)
        
        if not df3.empty:
            df3['occupancy_rate'] = df3['occupancy_rate'].astype(float)
            df3['route'] = df3['start_station'] + "-" + df3['end_station']
            
            source3 = ColumnDataSource(df3)
            p3 = figure(x_range=df3['route'], height=350, title="3. Завантаженість (%)", y_range=(0, 100))
            p3.vbar(x='route', top='occupancy_rate', width=0.5, source=source3, color="orange")
            p3.add_tools(HoverTool(tooltips=[("Маршрут", "@route"), ("%", "@occupancy_rate")]))
            plots['script3'], plots['div3'] = components(p3)

        # === 4. Типи потягів (Scatter) ===
        df4 = pd.DataFrame(list(analytics_qs['train_type_stats'].values('train_type', 'avg_passenger_age', 'max_ticket_price')))
        df4 = df4.fillna(0)
        
        if not df4.empty:
            df4['max_ticket_price'] = df4['max_ticket_price'].astype(float)
            df4['avg_passenger_age'] = df4['avg_passenger_age'].astype(float)
            
            source4 = ColumnDataSource(df4)
            p4 = figure(height=350, title="4. Вік vs Ціна (Scatter)")
            p4.circle(x='avg_passenger_age', y='max_ticket_price', size=15, source=source4, color="firebrick", alpha=0.6)
            p4.add_tools(HoverTool(tooltips=[("Тип", "@train_type"), ("Ціна", "@max_ticket_price"), ("Вік", "@avg_passenger_age")]))
            plots['script4'], plots['div4'] = components(p4)

        # === 5. Продажі по місяцях (Line) ===
        df5 = pd.DataFrame(list(analytics_qs['sales_by_month'].values('month', 'tickets_sold')))
        df5 = df5.fillna(0)
        
        if not df5.empty:
            # Bokeh потребує, щоб x-axis був відсортований для лінійного графіка
            df5 = df5.sort_values('month')
            source5 = ColumnDataSource(df5)
            p5 = figure(height=350, title="5. Динаміка продажів")
            p5.line(x='month', y='tickets_sold', line_width=2, source=source5, color="blue")
            p5.circle(x='month', y='tickets_sold', size=8, source=source5, color="blue")
            plots['script5'], plots['div5'] = components(p5)

        # === 6. VIP Клієнти (Horizontal Bar) ===
        df6 = pd.DataFrame(list(analytics_qs['top_passengers'].values('first_name', 'last_name', 'total_spent')))
        df6 = df6.fillna(0)
        
        if not df6.empty:
            df6['total_spent'] = df6['total_spent'].astype(float)
            df6['person'] = df6['first_name'] + " " + df6['last_name']
            
            source6 = ColumnDataSource(df6)
            # y_range - список імен
            p6 = figure(y_range=df6['person'], height=350, title="6. VIP Клієнти")
            p6.hbar(y='person', right='total_spent', height=0.5, source=source6, color="purple")
            p6.add_tools(HoverTool(tooltips=[("Клієнт", "@person"), ("Витрачено", "@total_spent")]))
            plots['script6'], plots['div6'] = components(p6)

        return render(request, 'tickets/dashboard_bokeh.html', {'plots': plots})

    def heavy_db_query(n):
        # 1. Створюємо нове з'єднання для цього потоку (Django робить це автоматично при запиті)
        try:
            # Робимо "важкий" запит: витягуємо список ID, а не просто count
            # Це змушує базу даних реально працювати
            _ = list(Ticket.objects.values_list('id', flat=True))
            
            # Можна додати мікро-затримку, щоб імітувати "складну обробку" або мережеві лаги
            # time.sleep(0.01) 
        finally:
            # 2. ДУЖЕ ВАЖЛИВО: Закриваємо з'єднання після виконання в потоці!
            # Якщо цього не зробити, Django не звільнить конект, і база "ляже".
            connection.close()
        return n

    def performance_view(request):
        request_count = 100  # Кількість запитів
        worker_options = [1, 2, 4, 8, 10] # Кількість потоків
        results = []

        graph_html = None
        
        # Запускаємо тест тільки по кнопці
        if request.GET.get('run_test'):
            for max_workers in worker_options:
                start_time = time.time()
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Відправляємо завдання
                    futures = [executor.submit(heavy_db_query, i) for i in range(request_count)]
                    # Чекаємо виконання всіх
                    concurrent.futures.wait(futures)
                
                end_time = time.time()
                duration = end_time - start_time
                results.append({'workers': max_workers, 'time': duration})
                
                print(f"Threads: {max_workers}, Time: {duration:.4f}s") # Лог в консоль

            # Будуємо графік
            if results:
                df_perf = pd.DataFrame(results)
                fig = px.line(
                    df_perf, x='workers', y='time', markers=True, 
                    title=f'Час виконання {request_count} запитів до БД',
                    labels={'workers': 'Потоки', 'time': 'Час (сек)'}
                )
                graph_html = fig.to_html(full_html=False)

        return render(request, 'tickets/performance.html', {'graph': graph_html})


    # Головна сторінка
    def home(request):
        return render(request, 'tickets/home.html')

    def dashboard_view(request):
        analytics_qs = repo.get_complex_analytics()
        min_revenue_filter = request.GET.get('min_revenue')
        graphs = {}

        # === ГРАФІК 1: Прибуток (Bar) ===
        df1 = pd.DataFrame(list(analytics_qs['revenue_by_trip'].values(
            'start_station', 'end_station', 'total_revenue'
        )))
        df1 = df1.fillna(0)

        if not df1.empty:
            # Конвертуємо Decimal -> float
            df1['total_revenue'] = df1['total_revenue'].astype(float) 

            if min_revenue_filter:
                try:
                    val = float(min_revenue_filter)
                    df1 = df1[df1['total_revenue'] >= val]
                except ValueError:
                    pass 

            df1['route'] = df1['start_station'] + " - " + df1['end_station']
            fig1 = px.bar(df1, x='route', y='total_revenue', title="1. Прибуток рейсів", color='total_revenue')
            graphs['g1'] = fig1.to_html(full_html=False)

        # === ГРАФІК 2: Касири (Pie) ===
        df2 = pd.DataFrame(list(analytics_qs['cashier_performance'].values(
            'first_name', 'last_name', 'total_sales'
        )))
        df2 = df2.fillna(0)
        
        if not df2.empty:
            df2['total_sales'] = df2['total_sales'].astype(float) # Конвертація

            df2['cashier'] = df2['first_name'] + " " + df2['last_name']
            fig2 = px.pie(df2, values='total_sales', names='cashier', title="2. Доля продажів касирів")
            graphs['g2'] = fig2.to_html(full_html=False)

        # === ГРАФІК 3: Завантаженість (Bar) ===
        df3 = pd.DataFrame(list(analytics_qs['trip_occupancy'].values(
            'start_station', 'end_station', 'occupancy_rate'
        )))
        df3 = df3.fillna(0)

        if not df3.empty:
            df3['occupancy_rate'] = df3['occupancy_rate'].astype(float) # Конвертація

            df3['route'] = df3['start_station'] + "-" + df3['end_station']
            fig3 = px.bar(df3, x='route', y='occupancy_rate', title="3. Заповненість потягів (%)", 
                        range_y=[0, 100], color='occupancy_rate')
            graphs['g3'] = fig3.to_html(full_html=False)

        # === ГРАФІК 4: Типи потягів (Scatter) ===
        # САМЕ ТУТ БУЛА ПОМИЛКА
        df4 = pd.DataFrame(list(analytics_qs['train_type_stats'].values(
            'train_type', 'avg_passenger_age', 'max_ticket_price'
        )))
        df4 = df4.fillna(0)

        if not df4.empty:
            # Plotly вимагає float для 'size', Decimal не підходить
            df4['max_ticket_price'] = df4['max_ticket_price'].astype(float)
            df4['avg_passenger_age'] = df4['avg_passenger_age'].astype(float)

            fig4 = px.scatter(df4, x='avg_passenger_age', y='max_ticket_price', 
                            size='max_ticket_price', # Тепер це float, помилки не буде
                            color='train_type', 
                            title="4. Типи потягів: Вік vs Ціна (Bubble Chart)", 
                            size_max=60)
            graphs['g4'] = fig4.to_html(full_html=False)

        # === ГРАФІК 5: Продажі по місяцях (Line) ===
        df5 = pd.DataFrame(list(analytics_qs['sales_by_month'].values(
            'month', 'tickets_sold'
        )))
        df5 = df5.fillna(0)

        if not df5.empty:
            fig5 = px.line(df5, x='month', y='tickets_sold', markers=True, title="5. Продажі по місяцях")
            graphs['g5'] = fig5.to_html(full_html=False)

        # === ГРАФІК 6: Топ Пасажири (Bar) ===
        df6 = pd.DataFrame(list(analytics_qs['top_passengers'].values(
            'first_name', 'last_name', 'total_spent'
        )))
        df6 = df6.fillna(0)

        if not df6.empty:
            df6['total_spent'] = df6['total_spent'].astype(float) # Конвертація
            
            df6['person'] = df6['first_name'] + " " + df6['last_name']
            fig6 = px.bar(df6, x='total_spent', y='person', orientation='h', title="6. VIP Клієнти")
            graphs['g6'] = fig6.to_html(full_html=False)

        return render(request, 'tickets/dashboard.html', {'graphs': graphs})


    # --- Passenger ---
    class PassengerListView(ListView):
        model = Passenger
        template_name = 'tickets/passenger_list.html'
        context_object_name = 'passengers'
        
        def get_queryset(self):
            # Використовуємо репозиторій
            return repo.passengers.all()

    class PassengerCreateView(CreateView):
        model = Passenger
        template_name = 'tickets/passenger_form.html'
        fields = ['first_name', 'last_name', 'passport', 'age']
        success_url = reverse_lazy('passenger_list')

    class PassengerUpdateView(UpdateView):
        model = Passenger
        template_name = 'tickets/passenger_form.html'
        fields = ['first_name', 'last_name', 'passport', 'age']
        success_url = reverse_lazy('passenger_list')

    class PassengerDeleteView(DeleteView):
        model = Passenger
        template_name = 'tickets/passenger_confirm_delete.html'
        success_url = reverse_lazy('passenger_list')

    # --- Cashier ---
    class CashierListView(ListView):
        model = Cashier
        template_name = 'tickets/cashier_list.html'
        context_object_name = 'cashiers'

        def get_queryset(self):
            return repo.cashiers.all()

    # --- Trip ---
    class TripListView(ListView):
        model = Trip
        template_name = 'tickets/trip_list.html'
        context_object_name = 'trips'

        def get_queryset(self):
            return repo.trips.all()

    # --- Ticket ---
    @login_required
    class TicketsListView(ListView, LoginRequiredMixin):
        model = Ticket
        template_name = 'tickets/tickets_list.html'
        context_object_name = 'tickets'

        def get_queryset(self):
            qs = repo.tickets.all()
            # if repo returns a Django QuerySet of Ticket objects, try to eager-load relations
            try:
                return qs.select_related('trip', 'passenger', 'cashier')
            except Exception:
                # repo may return plain objects or lists — return as-is (list) so we can attach related objects later
                return list(qs)

        def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)
            tickets = list(ctx.get('tickets', []))

            # collect ids from tickets (supports both ORM objects and plain objects with *_id attrs)
            trip_ids = {getattr(t, 'trip_id', None) for t in tickets if getattr(t, 'trip_id', None) is not None}
            passenger_ids = {getattr(t, 'passenger_id', None) for t in tickets if getattr(t, 'passenger_id', None) is not None}
            cashier_ids = {getattr(t, 'cashier_id', None) for t in tickets if getattr(t, 'cashier_id', None) is not None}

            if trip_ids:
                trips = Trip.objects.in_bulk(trip_ids)
            else:
                trips = {}

            if passenger_ids:
                passengers = Passenger.objects.in_bulk(passenger_ids)
            else:
                passengers = {}

            if cashier_ids:
                cashiers = Cashier.objects.in_bulk(cashier_ids)
            else:
                cashiers = {}

            # attach related objects so templates can use ticket.trip, ticket.passenger, ticket.cashier
            for t in tickets:
                # prefer existing related object if present, otherwise set from in_bulk map
                if not getattr(t, 'trip', None):
                    setattr(t, 'trip', trips.get(getattr(t, 'trip_id', None)))
                if not getattr(t, 'passenger', None):
                    setattr(t, 'passenger', passengers.get(getattr(t, 'passenger_id', None)))
                if not getattr(t, 'cashier', None):
                    setattr(t, 'cashier', cashiers.get(getattr(t, 'cashier_id', None)))

            ctx['tickets'] = tickets
            return ctx
        
    class TicketsDetailsView(DetailView):
        model = Ticket
        template_name = 'tickets/ticket_details.html'
        context_object_name = 'ticket' # Однина, бо це один квиток

        def get_object(self, queryset=None):
            """
            Замість get_queryset (для списку), DetailView використовує get_object.
            Ми беремо ID з URL (self.kwargs['pk']) і питаємо репо.
            """
            ticket_id = self.kwargs.get('pk')
            
            # Отримуємо об'єкт з репозиторія
            # Припускаємо, що get_by_id повертає один об'єкт або None
            obj = repo.tickets.get_by_id(ticket_id) 
            
            if not obj:
                raise Http404("Квиток не знайдено")
                
            return obj

        def get_context_data(self, **kwargs):
            """
            Тут ми вручну додаємо зв'язки (Trip, Passenger), 
            оскільки репозиторій може повертати "голий" об'єкт без ORM-зв'язків.
            """
            ctx = super().get_context_data(**kwargs)
            ticket = ctx['ticket'] # Це наш об'єкт, отриманий в get_object

            # 1. Підтягуємо Рейс (Trip)
            trip_id = getattr(ticket, 'trip_id', None)
            if trip_id:
                # Використовуємо filter().first(), щоб не було помилки, якщо ID битий
                ticket.trip = Trip.objects.filter(pk=trip_id).first()

            # 2. Підтягуємо Пасажира (Passenger)
            passenger_id = getattr(ticket, 'passenger_id', None)
            if passenger_id:
                ticket.passenger = Passenger.objects.filter(pk=passenger_id).first()

            # 3. Підтягуємо Касира (Cashier)
            cashier_id = getattr(ticket, 'cashier_id', None)
            if cashier_id:
                ticket.cashier = Cashier.objects.filter(pk=cashier_id).first()

            return ctx
        
    class TicketsAddView(CreateView):
        model = Ticket
        template_name = 'tickets/ticket_form.html'
        fields = ['trip', 'passenger', 'cashier', 'base_price', 'payment_method']
        success_url = reverse_lazy('tickets_list')

        def get_queryset(self):
            return repo.tickets.all()

    class TicketsEditView(UpdateView):
        model = Ticket
        template_name = 'tickets/ticket_form.html'
        fields = ['trip', 'passenger', 'cashier', 'base_price', 'payment_method']
        success_url = reverse_lazy('tickets_list')

    class TicketsDeleteView(DeleteView):
        model = Ticket
        template_name = 'tickets/ticket_confirm_delete.html'
        success_url = reverse_lazy('tickets_list')
    return render(request, 'my_template.html', {'user': request.user})

