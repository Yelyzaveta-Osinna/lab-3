# tickets/admin.py
from django.contrib import admin
from .models import TicketOffice, Passenger, Cashier, Trip, Ticket

admin.site.register(TicketOffice)
admin.site.register(Passenger)
admin.site.register(Cashier)
admin.site.register(Trip)
admin.site.register(Ticket)
