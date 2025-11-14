from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('passengers/', views.PassengerListView.as_view(), name='passenger_list'),
    path('passenger/add/', views.PassengerCreateView.as_view(), name='passenger_add'),
    path('passenger/<int:pk>/edit/', views.PassengerUpdateView.as_view(), name='passenger_edit'),
    path('passenger/<int:pk>/delete/', views.PassengerDeleteView.as_view(), name='passenger_delete'),
    
    path('cashiers/', views.CashierListView.as_view(), name='cashier_list'),
    path('trips/', views.TripListView.as_view(), name='trip_list'),
]
