from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, F
from .models import Trip, Ticket, Cashier, Passenger
from .models import Passenger, Cashier, Trip, TicketOffice, Ticket
import pandas as pd
import numpy as np
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
    


repo = RepositoryManager()

class AnalyticsAPIView(APIView):
    def get(self, request):
        analytics_qs = repo.get_complex_analytics()
        response_data = {}

        # Допоміжна функція для безпечної статистики
        def safe_stat(value):
            if pd.isna(value) or value is None:
                return 0.0
            return float(value)

        # --- 1. Прибуток по рейсах ---
        df_revenue = pd.DataFrame(list(analytics_qs['revenue_by_trip'].values(
            'start_station', 'end_station', 'total_revenue', 'tickets_sold'
        )))
        # ЗАМІНЮЄМО None на 0
        df_revenue = df_revenue.fillna(0) 
        
        if not df_revenue.empty:
            response_data['revenue_by_trip'] = {
                "data": df_revenue.to_dict(orient="records"),
                "stats": {
                    "total_revenue_sum": safe_stat(df_revenue['total_revenue'].sum()),
                    "avg_ticket_sales": safe_stat(df_revenue['tickets_sold'].mean())
                }
            }

        # --- 2. Ефективність касирів ---
        df_cashiers = pd.DataFrame(list(analytics_qs['cashier_performance'].values(
            'first_name', 'last_name', 'tickets_count', 'total_sales'
        )))
        df_cashiers = df_cashiers.fillna(0)

        if not df_cashiers.empty:
            response_data['cashier_performance'] = {
                "data": df_cashiers.to_dict(orient="records"),
                "stats": {
                    "best_cashier": df_cashiers.iloc[0]['last_name'] if not df_cashiers.empty else "N/A",
                    "avg_sales": safe_stat(df_cashiers['total_sales'].mean())
                }
            }

        # --- 3. Завантаженість ---
        df_occupancy = pd.DataFrame(list(analytics_qs['trip_occupancy'].values(
            'start_station', 'end_station', 'occupancy_rate', 'capacity'
        )))
        df_occupancy = df_occupancy.fillna(0)

        if not df_occupancy.empty:
            response_data['trip_occupancy'] = {
                "data": df_occupancy.to_dict(orient="records"),
                "stats": {
                    "avg_occupancy": safe_stat(df_occupancy['occupancy_rate'].mean())
                }
            }

        # --- 4. Типи потягів ---
        df_trains = pd.DataFrame(list(analytics_qs['train_type_stats'].values(
            'train_type', 'avg_passenger_age', 'max_ticket_price'
        )))
        df_trains = df_trains.fillna(0)

        if not df_trains.empty:
            response_data['train_type_stats'] = {
                "data": df_trains.to_dict(orient="records")
            }

        # --- 5. Продажі по місяцях ---
        df_months = pd.DataFrame(list(analytics_qs['sales_by_month'].values(
            'month', 'monthly_revenue', 'tickets_sold'
        )))
        df_months = df_months.fillna(0)

        if not df_months.empty:
            response_data['sales_by_month'] = {
                "data": df_months.to_dict(orient="records")
            }
            
        # --- 6. Топ пасажири ---
        df_passengers = pd.DataFrame(list(analytics_qs['top_passengers'].values(
            'first_name', 'last_name', 'total_spent'
        )))
        df_passengers = df_passengers.fillna(0)

        if not df_passengers.empty:
            response_data['top_passengers'] = {
                "data": df_passengers.to_dict(orient="records")
            }

        return Response(response_data)