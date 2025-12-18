from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views
from django.contrib.auth.decorators import login_required


urlpatterns = [
    path('', views.home, name='home'),
    
    # Auth
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', views.register_view, name='register'),

    # Списки (для перегляду картинок)
    path('passengers/', login_required(views.PassengerListView.as_view()), name='passenger_list'),
    path('passenger/add/', login_required(views.PassengerCreateView.as_view()), name='passenger_add'),
    path('passenger/<int:pk>/edit/', login_required(views.PassengerUpdateView.as_view()), name='passenger_edit'),
    path('passenger/<int:pk>/delete/', login_required(views.PassengerDeleteView.as_view()), name='passenger_delete'),
    path('trips/', login_required(views.TripListView.as_view()), name='trip_list'),
    path('cashiers/', login_required(views.CashierListView.as_view()), name='cashier_list'),

    # CRUD Tickets (Вимога Лаби)
    path('tickets/', login_required(views.TicketsListView.as_view()), name='tickets_list'),
    path('tickets/add/', login_required(views.TicketsCreateView.as_view()), name='ticket_add'),
    path('tickets/<int:pk>/', login_required(views.TicketsDetailView.as_view()), name='ticket_detail'),
    path('tickets/<int:pk>/edit/', login_required(views.TicketsUpdateView.as_view()), name='ticket_edit'),
    path('tickets/<int:pk>/delete/', login_required(views.TicketsDeleteView.as_view()), name='ticket_delete'),


    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/v2/', views.dashboard_bokeh_view, name='dashboard_bokeh'),
    path('performance/', views.performance_view, name='performance'),
]