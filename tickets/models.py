from decimal import Decimal
from django.db import models
from django.forms import ValidationError
from datetime import date
from decimal import Decimal

class TicketOffice(models.Model):
    name = models.CharField(max_length=255, default="Залізнична каса Львів")
    location = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)

    def __str__(self):
        return f"{self.name}, {self.location}, тел. {self.phone}"

class Person(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    # НОВЕ: Фото для людей
    photo = models.ImageField(upload_to='people/', blank=True, null=True, verbose_name="Фото")

    class Meta:
        abstract = True

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def greet(self):
        return f"Вітаю, я {self.full_name}!"

class Passenger(Person):
    passport = models.CharField(max_length=50)
    age = models.PositiveIntegerField()
    def __str__(self): return f"{self.full_name} ({self.passport})"

class Cashier(Person):
    hire_date = models.DateField()
    def __str__(self): return self.full_name

class Trip(models.Model):
    start_station = models.CharField(max_length=255)
    end_station = models.CharField(max_length=255)
    distance_km = models.PositiveIntegerField()
    # НОВЕ: Фото рейсу
    image = models.ImageField(upload_to='trips/', blank=True, null=True, verbose_name="Фото рейсу")
    
    price = models.PositiveIntegerField(default=100)
    capacity = models.PositiveIntegerField(default=100)
    number = models.CharField(max_length=50, default='None')
    train_type = models.CharField(max_length=100, default='Regular')
    departure = models.DateTimeField(auto_now_add=True) # Спрощено для прикладу
    arrival = models.DateTimeField(auto_now_add=True)

    @property
    def available_seats(self):
        return self.capacity - self.tickets.count()
    def __str__(self): return f"{self.start_station} - {self.end_station}"

class Ticket(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='tickets')
    passenger = models.ForeignKey(Passenger, on_delete=models.CASCADE, related_name='tickets')
    cashier = models.ForeignKey(Cashier, on_delete=models.SET_NULL, null=True, related_name='sold_tickets')
    purchase_date = models.DateTimeField(auto_now_add=True)
    
    # Використовуємо Decimal, щоб не було помилок валідації
    base_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50, blank=True, default="Cash")

    def save(self, *args, **kwargs):
        if not self.base_price:
            self.base_price = self.trip.price
        self.paid_amount = self.base_price # Спрощена логіка для Лаби 3
        super().save(*args, **kwargs)
