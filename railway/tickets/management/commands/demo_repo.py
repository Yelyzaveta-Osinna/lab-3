# tickets/management/commands/demo_repo.py
from django.core.management.base import BaseCommand
from tickets.repositories import RepositoryManager
from django.utils import timezone
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = "Demo repository: create and read Passenger, Cashier, Trip"

    def handle(self, *args, **options):
        repo = RepositoryManager()

        # 1. Створення TicketOffice
        office = repo.offices.add(name="Залізнична каса Львів", location="м. Львів, пл. Двірцева 1", phone="+380441234567")
        self.stdout.write(self.style.SUCCESS(f"Створено TicketOffice id={office.id}"))

        # 2. Додавання Passenger
        p = repo.passengers.add(first_name="Олена", last_name="Мельник", passport="AB123456", age=17)
        self.stdout.write(self.style.SUCCESS(f"Додано Passenger id={p.id}: {p.full_name}, {p.passport}, {p.age}"))

        # 3. Додавання Cashier
        c = repo.cashiers.add(first_name="Ігор", last_name="Коваленко", hire_date="2020-05-10")
        self.stdout.write(self.style.SUCCESS(f"Додано Cashier id={c.id}: {c.full_name}, hire_date={c.hire_date}"))

        # 4. Додавання Trip
        dep = timezone.make_aware(datetime(2025, 10, 20, 8, 30))
        arr = timezone.make_aware(datetime(2025, 10, 20, 14, 30))
        t = repo.trips.add(start_station="Львів", end_station="Київ", distance_km=540, number="723A", train_type="Інтерсіті", departure=dep, arrival=arr)
        self.stdout.write(self.style.SUCCESS(f"Додано Trip id={t.id}: {t}"))

        # 5. Прочитати всі пасажири (вичитка)
        all_passengers = repo.passengers.all()
        self.stdout.write("Всі пасажири:")
        for pas in all_passengers:
            self.stdout.write(f" - {pas.id}: {pas.full_name} ({pas.age} років), паспорт {pas.passport}")

        # 6. Пошук по ID
        found = repo.passengers.get_by_id(p.id)
        self.stdout.write(f"Знайдено пасажира по id={p.id}: {found.full_name}, {found.age}")

        # 7. Оновлення (update)
        updated = repo.passengers.update(p.id, age=18)
        self.stdout.write(f"Оновлено пасажира id={p.id}: новий вік {updated.age}")

        # 8. Показати, що запис з'явився в БД (вивід для демонстрації)
        self.stdout.write(self.style.SUCCESS("Демо завершене. \nМожеш перевірити таблиці у MySQL:"))
        self.stdout.write("SELECT * FROM tickets_passenger;")
        self.stdout.write("SELECT * FROM tickets_cashier;")
        self.stdout.write("SELECT * FROM tickets_trip;")
