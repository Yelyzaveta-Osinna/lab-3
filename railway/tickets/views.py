from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Passenger, Cashier, Trip
from .repositories import RepositoryManager

repo = RepositoryManager()

# Головна сторінка
def home(request):
    return render(request, 'tickets/home.html')

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
