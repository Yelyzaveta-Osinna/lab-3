from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import PassengerViewSet, CashierViewSet, TripViewSet, ReportViewSet

router = DefaultRouter()
router.register(r'passengers', PassengerViewSet, basename='passengers')
router.register(r'cashiers', CashierViewSet, basename='cashiers')
router.register(r'trips', TripViewSet, basename='trips')
router.register(r'reports', ReportViewSet, basename='reports')

urlpatterns = [
    path('', include(router.urls)),
]
