# tickets/models.py
from django.db import models

class TicketOffice(models.Model):
    name = models.CharField(max_length=255, default="Залізнична каса Львів")
    location = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)

    def __str__(self):
        return f"{self.name}, {self.location}, тел. {self.phone}"


class Person(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    class Meta:
        abstract = True

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def initials(self):
        return f"{self.first_name[0]}.{self.last_name[0]}."

    def greet(self):
        return f"Вітаю, я {self.full_name}!"


class Passenger(Person):
    passport = models.CharField(max_length=50)
    age = models.PositiveIntegerField()

    def passport_info(self):
        return f"Паспорт: {self.passport}"

    def age_group(self):
        if self.age < 18:
            return "неповнолітній"
        elif self.age > 60:
            return "пенсіонер"
        return "дорослий"


class Cashier(Person):
    hire_date = models.DateField()

    def work_years(self):
        from datetime import date
        return date.today().year - self.hire_date.year

    def introduce(self):
        return f"Я касир {self.full_name}, працюю {self.work_years()} років."


class Trip(models.Model):
    start_station = models.CharField(max_length=255)
    end_station = models.CharField(max_length=255)
    distance_km = models.PositiveIntegerField()
    number = models.CharField(max_length=50)
    train_type = models.CharField(max_length=100)
    departure = models.DateTimeField()
    arrival = models.DateTimeField()

    def duration_minutes(self):
        delta = self.arrival - self.departure
        return int(delta.total_seconds() // 60)

    def duration_str(self):
        mins = self.duration_minutes()
        hours = mins // 60
        minutes = mins % 60
        return f"{hours} год {minutes} хв"

    def __str__(self):
        return f"{self.start_station} — {self.end_station} ({self.distance_km} км)"


class Ticket(models.Model):
    TAX = 0.2
    passenger = models.ForeignKey(Passenger, on_delete=models.CASCADE, related_name='tickets')
    cashier = models.ForeignKey(Cashier, on_delete=models.SET_NULL, null=True, related_name='sold_tickets')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='tickets')
    purchase_date = models.DateTimeField(auto_now_add=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    # payment fields could be expanded
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @staticmethod
    def calculate_discount(age):
        if age < 18:
            return 0.5
        elif age > 60:
            return 0.7
        return 1.0

    @property
    def price(self):
        discount = self.calculate_discount(self.passenger.age)
        discounted_price = float(self.base_price) * discount
        return round(discounted_price * (1 + self.TAX), 2)
