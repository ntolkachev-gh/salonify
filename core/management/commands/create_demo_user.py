from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Salon, Master, Service, Client, Appointment
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Create demo user and data for testing'

    def handle(self, *args, **options):
        # Create superuser
        if not User.objects.filter(username='admin').exists():
            user = User.objects.create_superuser(
                username='admin',
                email='admin@salonify.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )
            self.stdout.write(self.style.SUCCESS('Created superuser: admin / admin123'))
        else:
            user = User.objects.get(username='admin')
            self.stdout.write(self.style.WARNING('Superuser already exists'))

        # Create demo salon
        salon, created = Salon.objects.get_or_create(
            user=user,
            name='Beauty Salon Demo',
            defaults={
                'address': 'ул. Красоты, 123, Москва',
                'phone': '+7 (495) 123-45-67',
                'email': 'info@beautysalon.ru',
                'working_hours': {
                    'monday': '9:00-18:00',
                    'tuesday': '9:00-18:00',
                    'wednesday': '9:00-18:00',
                    'thursday': '9:00-18:00',
                    'friday': '9:00-18:00',
                    'saturday': '10:00-16:00',
                    'sunday': 'Выходной'
                },
                'timezone': 'Europe/Moscow'
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created salon: {salon.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Salon already exists: {salon.name}'))

        # Create demo masters
        masters_data = [
            {
                'full_name': 'Анна Иванова',
                'phone': '+7 (495) 111-11-11',
                'specialization': 'Стрижки и укладки',
                'working_hours': {'monday': '9:00-17:00', 'tuesday': '9:00-17:00'}
            },
            {
                'full_name': 'Мария Петрова',
                'phone': '+7 (495) 222-22-22',
                'specialization': 'Маникюр и педикюр',
                'working_hours': {'wednesday': '10:00-18:00', 'thursday': '10:00-18:00'}
            },
            {
                'full_name': 'Елена Сидорова',
                'phone': '+7 (495) 333-33-33',
                'specialization': 'Косметология',
                'working_hours': {'friday': '9:00-16:00', 'saturday': '10:00-15:00'}
            }
        ]

        for master_data in masters_data:
            master, created = Master.objects.get_or_create(
                salon=salon,
                full_name=master_data['full_name'],
                defaults=master_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created master: {master.full_name}'))

        # Create demo services
        masters = Master.objects.filter(salon=salon)
        services_data = [
            {
                'name': 'Женская стрижка',
                'description': 'Стрижка для женщин любой длины волос',
                'price': Decimal('2500.00'),
                'duration_minutes': 60,
                'category': 'haircut',
                'master': masters.filter(specialization__icontains='Стрижки').first()
            },
            {
                'name': 'Мужская стрижка',
                'description': 'Классическая мужская стрижка',
                'price': Decimal('1500.00'),
                'duration_minutes': 45,
                'category': 'haircut',
                'master': masters.filter(specialization__icontains='Стрижки').first()
            },
            {
                'name': 'Маникюр классический',
                'description': 'Классический маникюр с покрытием',
                'price': Decimal('2000.00'),
                'duration_minutes': 90,
                'category': 'manicure',
                'master': masters.filter(specialization__icontains='Маникюр').first()
            },
            {
                'name': 'Педикюр',
                'description': 'Классический педикюр',
                'price': Decimal('2500.00'),
                'duration_minutes': 120,
                'category': 'pedicure',
                'master': masters.filter(specialization__icontains='Маникюр').first()
            },
            {
                'name': 'Чистка лица',
                'description': 'Глубокая чистка лица',
                'price': Decimal('3500.00'),
                'duration_minutes': 90,
                'category': 'facial',
                'master': masters.filter(specialization__icontains='Косметология').first()
            }
        ]

        for service_data in services_data:
            service, created = Service.objects.get_or_create(
                salon=salon,
                name=service_data['name'],
                defaults=service_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created service: {service.name}'))

        # Create demo clients
        clients_data = [
            {
                'full_name': 'Екатерина Смирнова',
                'phone': '+7 (495) 777-77-77',
                'email': 'kate@example.com',
                'visits_count': 5,
                'total_spent': Decimal('12500.00')
            },
            {
                'full_name': 'Ольга Козлова',
                'phone': '+7 (495) 888-88-88',
                'email': 'olga@example.com',
                'visits_count': 3,
                'total_spent': Decimal('7500.00')
            },
            {
                'full_name': 'Дмитрий Волков',
                'phone': '+7 (495) 999-99-99',
                'email': 'dmitry@example.com',
                'visits_count': 2,
                'total_spent': Decimal('3000.00')
            }
        ]

        for client_data in clients_data:
            client, created = Client.objects.get_or_create(
                salon=salon,
                full_name=client_data['full_name'],
                defaults=client_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created client: {client.full_name}'))

        # Create demo appointments
        services = Service.objects.filter(salon=salon)
        clients = Client.objects.filter(salon=salon)
        
        if services.exists() and clients.exists():
            # Future appointment
            future_appointment = Appointment.objects.create(
                salon=salon,
                client=clients.first(),
                service=services.first(),
                master=services.first().master,
                scheduled_at=timezone.now() + timedelta(days=1, hours=2),
                status='planned',
                price=services.first().price
            )
            self.stdout.write(self.style.SUCCESS(f'Created future appointment for {future_appointment.client.full_name}'))

            # Past appointment
            past_appointment = Appointment.objects.create(
                salon=salon,
                client=clients.last(),
                service=services.last(),
                master=services.last().master,
                scheduled_at=timezone.now() - timedelta(days=7),
                status='completed',
                price=services.last().price
            )
            self.stdout.write(self.style.SUCCESS(f'Created past appointment for {past_appointment.client.full_name}'))

        self.stdout.write(self.style.SUCCESS('\n=== DEMO DATA CREATED ==='))
        self.stdout.write(self.style.SUCCESS('Admin panel: http://localhost:8000/admin/'))
        self.stdout.write(self.style.SUCCESS('Username: admin'))
        self.stdout.write(self.style.SUCCESS('Password: admin123'))
        self.stdout.write(self.style.SUCCESS('API: http://localhost:8000/api/'))
        self.stdout.write(self.style.SUCCESS('========================')) 