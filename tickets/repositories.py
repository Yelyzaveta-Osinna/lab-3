# tickets/repositories.py
from abc import ABC, abstractmethod
from typing import Type, List, Optional
from django.db import models
from django.db.models import Count, Sum, Avg, Max, F, ExpressionWrapper, FloatField
from django.db.models.functions import ExtractMonth
from .models import Trip, Ticket, Cashier, Passenger
from django.db import connection
import concurrent.futures
# --- Інтерфейс базового репозиторію ---
class BaseRepository(ABC):
    model: Type[models.Model]

    def __init__(self, model):
        self.model = model

    def all(self) -> List[models.Model]:
        return list(self.model.objects.all())

    def get_by_id(self, pk: int) -> Optional[models.Model]:
        try:
            return self.model.objects.get(pk=pk)
        except self.model.DoesNotExist:
            return None

    def add(self, **kwargs) -> models.Model:
        # Створюємо і повертаємо інстанс
        instance = self.model.objects.create(**kwargs)
        return instance

    def update(self, pk: int, **kwargs) -> Optional[models.Model]:
        obj = self.get_by_id(pk)
        if obj is None:
            return None
        for k, v in kwargs.items():
            setattr(obj, k, v)
        obj.save()
        return obj

    def delete(self, pk: int) -> bool:
        obj = self.get_by_id(pk)
        if obj is None:
            return False
        obj.delete()
        return True

# --- Конкретні репозиторії ---
from .models import Passenger, Cashier, Trip, TicketOffice, Ticket

class PassengerRepository(BaseRepository):
    def __init__(self):
        super().__init__(Passenger)

    # можна додати domain-specific методи
    def find_by_passport(self, passport: str):
        return list(self.model.objects.filter(passport=passport))


class CashierRepository(BaseRepository):
    def __init__(self):
        super().__init__(Cashier)


class TripRepository(BaseRepository):
    def __init__(self):
        super().__init__(Trip)

    def upcoming(self, from_datetime):
        return list(self.model.objects.filter(departure__gte=from_datetime))


class TicketOfficeRepository(BaseRepository):
    def __init__(self):
        super().__init__(TicketOffice)


class TicketRepository(BaseRepository):
    def __init__(self):
        super().__init__(Ticket)

    def by_passenger(self, passenger_id):
        return list(self.model.objects.filter(passenger_id=passenger_id))


# --- Єдина точка доступу (Repository Manager / Unit of Work) ---
class RepositoryManager:
    @property
    def passengers(self): return Passenger.objects.all()
    @property
    def cashiers(self): return Cashier.objects.all()
    @property
    def trips(self): return Trip.objects.all()
    @property
    def tickets(self): return Ticket.objects.all()

    def get_complex_analytics(self):
        # 1. Визначаємо функції для кожного запиту
        def get_revenue():
            # Важливо: list(), щоб виконати запит прямо тут, у потоці
            return Trip.objects.annotate(
                total_revenue=Sum('tickets__paid_amount'),
                tickets_sold=Count('tickets')
            ).order_by('-total_revenue')

        def get_cashiers():
            return Cashier.objects.annotate(
                tickets_count=Count('sold_tickets'),
                total_sales=Sum('sold_tickets__paid_amount')
            ).filter(tickets_count__gt=0).order_by('-total_sales')

        def get_occupancy():
            return Trip.objects.annotate(
                sold_count=Count('tickets')
            ).annotate(
                occupancy_rate=ExpressionWrapper(
                    F('sold_count') * 100.0 / F('capacity'),
                    output_field=FloatField()
                )
            ).order_by('-occupancy_rate')

        def get_types():
            return Trip.objects.values('train_type').annotate(
                avg_passenger_age=Avg('tickets__passenger__age'),
                max_ticket_price=Max('tickets__paid_amount')
            ).order_by('train_type')

        def get_months():
            return Ticket.objects.annotate(
                month=ExtractMonth('purchase_date')
            ).values('month').annotate(
                tickets_sold=Count('id'),
                monthly_revenue=Sum('paid_amount')
            ).order_by('month')

        def get_passengers():
            return Passenger.objects.annotate(
                total_spent=Sum('tickets__paid_amount')
            ).filter(total_spent__isnull=False).order_by('-total_spent')[:10]

        # 2. Запускаємо їх одночасно
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Словник: {Future об'єкт: 'ключ_результату'}
            future_to_key = {
                executor.submit(get_revenue): 'revenue_by_trip',
                executor.submit(get_cashiers): 'cashier_performance',
                executor.submit(get_occupancy): 'trip_occupancy',
                executor.submit(get_types): 'train_type_stats',
                executor.submit(get_months): 'sales_by_month',
                executor.submit(get_passengers): 'top_passengers',
            }

            for future in concurrent.futures.as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    results[key] = future.result()
                except Exception as exc:
                    print(f'{key} generated an exception: {exc}')
                    results[key] = []
                finally:
                    # Закриваємо з'єднання потоку, щоб не висіло
                    connection.close()

        return results