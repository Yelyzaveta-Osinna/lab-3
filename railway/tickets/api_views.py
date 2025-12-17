from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Passenger, Cashier, Trip, TicketOffice, Ticket
from .serializers import (
    PassengerSerializer, CashierSerializer, TripSerializer, TicketOfficeSerializer, TicketSerializer
)
from .repositories import RepositoryManager

repo = RepositoryManager()

# ---- CRUD через репозиторій ----
class PassengerViewSet(viewsets.ViewSet):
    def list(self, request):
        data = repo.passengers.all()
        serializer = PassengerSerializer(data, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        obj = repo.passengers.get_by_id(pk)
        serializer = PassengerSerializer(obj)
        return Response(serializer.data)

    def create(self, request):
        obj = repo.passengers.add(**request.data)
        serializer = PassengerSerializer(obj)
        return Response(serializer.data)

    def update(self, request, pk=None):
        obj = repo.passengers.update(pk, **request.data)
        serializer = PassengerSerializer(obj)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        success = repo.passengers.delete(pk)
        return Response({'deleted': success})


class CashierViewSet(viewsets.ViewSet):
    def list(self, request):
        data = repo.cashiers.all()
        serializer = CashierSerializer(data, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        obj = repo.cashiers.get_by_id(pk)
        serializer = CashierSerializer(obj)
        return Response(serializer.data)

    def create(self, request):
        obj = repo.cashiers.add(**request.data)
        serializer = CashierSerializer(obj)
        return Response(serializer.data)

    def update(self, request, pk=None):
        obj = repo.cashiers.update(pk, **request.data)
        serializer = CashierSerializer(obj)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        success = repo.cashiers.delete(pk)
        return Response({'deleted': success})


class TripViewSet(viewsets.ViewSet):
    def list(self, request):
        data = repo.trips.all()
        serializer = TripSerializer(data, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        obj = repo.trips.get_by_id(pk)
        serializer = TripSerializer(obj)
        return Response(serializer.data)

    def create(self, request):
        obj = repo.trips.add(**request.data)
        serializer = TripSerializer(obj)
        return Response(serializer.data)

    def update(self, request, pk=None):
        obj = repo.trips.update(pk, **request.data)
        serializer = TripSerializer(obj)
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        success = repo.trips.delete(pk)
        return Response({'deleted': success})


# ---- Метод для агрегованого звіту ----
from django.db.models import Avg, Count

class ReportViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def summary(self, request):
        total_passengers = len(repo.passengers.all())
        total_cashiers = len(repo.cashiers.all())
        total_trips = len(repo.trips.all())
        avg_age_passenger = round(sum([p.age for p in repo.passengers.all()])/max(total_passengers,1), 2)

        return Response({
            'total_passengers': total_passengers,
            'total_cashiers': total_cashiers,
            'total_trips': total_trips,
            'average_passenger_age': avg_age_passenger
        })
