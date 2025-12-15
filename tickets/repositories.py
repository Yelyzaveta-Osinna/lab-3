# tickets/repositories.py
from abc import ABC, abstractmethod
from typing import Type, List, Optional
from django.db import models
from django.db.models import Count, Sum, Avg, Max, F, ExpressionWrapper, FloatField
from django.db.models.functions import ExtractMonth
from .models import Trip, Ticket, Cashier, Passenger
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

    def get_by_id(self, model_manager, id):
        return model_manager.filter(id=id).first()

    def get_complex_analytics(self):
        """6 складних запитів для Лаби 4"""
        return {
            # 1. Прибуток по рейсах
            'revenue_by_trip': Trip.objects.annotate(
                total_revenue=Sum('tickets__paid_amount')
            ).order_by('-total_revenue'),

            # 2. Ефективність касирів
            'cashier_performance': Cashier.objects.annotate(
                tickets_count=Count('sold_tickets'),
                total_sales=Sum('sold_tickets__paid_amount')
            ).filter(tickets_count__gt=0).order_by('-total_sales'),

            # 3. Завантаженість (%)
            'trip_occupancy': Trip.objects.annotate(
                sold_count=Count('tickets')
            ).annotate(
                occupancy_rate=ExpressionWrapper(
                    F('sold_count') * 100.0 / F('capacity'),
                    output_field=FloatField()
                )
            ).order_by('-occupancy_rate'),

            # 4. Типи потягів
            'train_type_stats': Trip.objects.values('train_type').annotate(
                avg_passenger_age=Avg('tickets__passenger__age'),
                max_ticket_price=Max('tickets__paid_amount')
            ).order_by('train_type'),

            # 5. Продажі по місяцях
            'sales_by_month': Ticket.objects.annotate(
                month=ExtractMonth('purchase_date')
            ).values('month').annotate(
                tickets_sold=Count('id')
            ).order_by('month'),

            # 6. VIP Пасажири
            'top_passengers': Passenger.objects.annotate(
                total_spent=Sum('tickets__paid_amount')
            ).filter(total_spent__isnull=False).order_by('-total_spent')[:10]
        }