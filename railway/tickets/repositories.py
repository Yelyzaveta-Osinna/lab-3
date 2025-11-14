# tickets/repositories.py
from abc import ABC, abstractmethod
from typing import Type, List, Optional
from django.db import models

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
    def __init__(self):
        self.passengers = PassengerRepository()
        self.cashiers = CashierRepository()
        self.trips = TripRepository()
        self.offices = TicketOfficeRepository()
        self.tickets = TicketRepository()
