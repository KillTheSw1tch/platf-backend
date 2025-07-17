from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator

from django.core.exceptions import ValidationError
from PIL import Image
import os

from django.db.models import Q, UniqueConstraint

from .utils import get_company_code

from django.utils import timezone
from django.conf import settings



def validate_company_file(file):
    max_size_mb = 2
    valid_extensions = ['jpg', 'jpeg', 'png', 'webp', 'pdf', 'svg']

    ext = os.path.splitext(file.name)[1][1:].lower()
    
    if ext == 'svg':
        return  # ⬅️ SVG пропускаем из проверки PIL

    if ext not in valid_extensions:
        raise ValidationError("Дозволені формати: JPG, JPEG, PNG, WEBP, PDF.")

    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Розмір файлу не повинен перевищувати {max_size_mb}MB.")

    # Проверка разрешения только для изображений (не для SVG и PDF)
    if ext in ['jpg', 'jpeg', 'png', 'webp']:
        try:
            image = Image.open(file)
            max_width, max_height = 1024, 1024
            if image.width > max_width or image.height > max_height:
                raise ValidationError("Максимальні розміри зображення: 1024x1024 пікселів.")
        except Exception:
            raise ValidationError("Файл має бути коректним зображенням або PDF.")


class Cargo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cargos', null=True, blank=True)
    loading_city_primary = models.CharField(max_length=255)
    loading_postal_primary = models.CharField(max_length=20, blank=True, null=True)
    loading_city_secondary = models.CharField(max_length=255, blank=True, null=True)
    loading_postal_secondary = models.CharField(max_length=20, blank=True, null=True)
    unloading_city_primary = models.CharField(max_length=255)
    unloading_postal_primary = models.CharField(max_length=20, blank=True, null=True)
    unloading_city_secondary = models.CharField(max_length=255, blank=True, null=True)
    unloading_city_secondary = models.CharField(max_length=255, blank=True, null=True)
    cargo_unloading_street = models.CharField(max_length=255, blank=True, null=True)
    cargo_loading_street = models.CharField(max_length=20, blank=True, null=True)
    date_from = models.DateField()
    email = models.EmailField(max_length=40, blank=True, null=True)
    date_to = models.DateField(blank=True, null=True)
    cargo_type = models.CharField(max_length=255)
    weight = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    volume = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    length = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    height = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    transport_type = models.CharField(max_length=30, blank=True, null=True)
    truck_count = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    price_currency = models.CharField(max_length=10, blank=True, null=True)
    price_per_unit = models.CharField(max_length=20, blank=True, null=True)
    humanitarian_aid = models.BooleanField(default=False)
    extra_info = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    loading_canton = models.CharField(max_length=100, null=True)    # Новое поле
    unloading_canton = models.CharField(max_length=100, null=True)  # Новое поле
    phone_number = models.CharField(max_length=20, null=True)        # Новое поле
    viber_whatsapp_number = models.CharField(max_length=20, null=True)  # Новое поле
    hidden = models.BooleanField(default=False)  # ⬅️ Добавь это поле
    show_on_main = models.BooleanField(default=False)
    show_in_available_cargo = models.BooleanField(default=False)

    order_number = models.CharField(max_length=20, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        from .utils import get_company_code
        from .models import CargoAdmin

        if not self.order_number:
            company_code = get_company_code(self.user)
            if not company_code:
                raise Exception("Не удалось получить код компании")

            prefix = f"C{company_code}"

            # Получаем последнее число из Cargo
            last_cargo = Cargo.objects.filter(order_number__startswith=prefix).order_by('-id').first()
            cargo_number = int(last_cargo.order_number[-6:]) if last_cargo and last_cargo.order_number else 0

            # Получаем последнее число из CargoAdmin
            last_admin = CargoAdmin.objects.filter(order_number__startswith=prefix).order_by('-id').first()
            if last_admin and last_admin.order_number:
                try:
                    admin_number = int(last_admin.order_number[len(prefix):len(prefix)+6])
                except:
                    admin_number = 0
            else:
                admin_number = 0

            # Берём максимальное число и увеличиваем
            max_number = max(cargo_number, admin_number) + 1
            self.order_number = f"{prefix}{max_number:06d}"

        super().save(*args, **kwargs)

    
    def __str__(self):
        return f"{self.loading_city_primary} -> {self.unloading_city_primary}"
    
class EmailVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f'{self.user.username} - {self.code}'
    
class Truck(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trucks', null=True, blank=True)
    loading_date_from = models.DateField()
    loading_date_to = models.DateField()
    loading_location = models.CharField(max_length=255)
    additional_loading_location = models.CharField(max_length=255, blank=True, null=True)
    vehicle_type = models.CharField(max_length=100)
    loading_canton = models.CharField(max_length=100, null=True)
    unloading_canton = models.CharField(max_length=100, null=True)
    loading_city = models.CharField(max_length=100, null=True)
    unloading_city = models.CharField(max_length=100, null=True)
    truck_unloading_street = models.CharField(max_length=255, blank=True, null=True)
    truck_loading_street = models.CharField(max_length=20, blank=True, null=True)
    number_of_vehicles = models.PositiveIntegerField()
    carrying_capacity = models.FloatField(blank=True, null=True)
    useful_volume = models.FloatField(blank=True, null=True)
    length = models.FloatField(blank=True, null=True)
    width = models.FloatField(blank=True, null=True)
    height = models.FloatField(blank=True, null=True)
    email = models.EmailField(max_length=40, blank=True, null=True)
    phone = models.CharField(max_length=20)
    unloading_postal = models.CharField(max_length=20, blank=True, null=True)
    loading_postal = models.CharField(max_length=20, blank=True, null=True)
    whatsapp = models.CharField(max_length=100, blank=True, null=True)
    has_gps = models.BooleanField(default=False)
    additional_info = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    hidden = models.BooleanField(default=False)
    show_on_main = models.BooleanField(default=False)
    show_in_available_vehicles = models.BooleanField(default=False)
    
    order_number = models.CharField(max_length=20, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        from .utils import get_company_code
        from .models import TruckAdmin

        if not self.order_number:
            company_code = get_company_code(self.user)
            if not company_code:
                raise Exception("Не удалось получить код компании")

            prefix = f"V{company_code}"

            # Последний номер из Truck
            last_truck = Truck.objects.filter(order_number__startswith=prefix).order_by('-id').first()
            truck_number = int(last_truck.order_number[-6:]) if last_truck and last_truck.order_number else 0

            # Последний номер из TruckAdmin
            last_admin = TruckAdmin.objects.filter(order_number__startswith=prefix).order_by('-id').first()
            if last_admin and last_admin.order_number:
                try:
                    admin_number = int(last_admin.order_number[len(prefix):len(prefix)+6])
                except:
                    admin_number = 0
            else:
                admin_number = 0

            max_number = max(truck_number, admin_number) + 1
            self.order_number = f"{prefix}{max_number:06d}"

        super().save(*args, **kwargs)



    def __str__(self):
        return f"Грузовик → {self.loading_city} -> {self.unloading_city}"
    
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    preferred_language = models.CharField(max_length=20, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    zip_code = models.CharField(max_length=10, blank=True, null=True)
    canton = models.CharField(max_length=50, blank=True, null=True)
    client_type = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)  
    viber_whatsapp_number = models.CharField(max_length=100, blank=True, null=True) 
    full_name = models.CharField(max_length=100, blank=True, null=True) 

    two_factor_secret = models.CharField(max_length=32, blank=True, null=True)
    is_two_factor_enabled = models.BooleanField(default=False)
    is_2fa_enabled = models.BooleanField(default=False)

    company_photo = models.ImageField(
        upload_to='company_photos/',
        blank=True,
        null=True,
        validators=[validate_company_file]
    )

    # 🟢 Вот это — новое поле:
    notifications_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.user.username} Profile'


def user_directory_path(instance, filename):
    # файлы будут сохраняться, например: company_docs/user_7/название_файла.pdf
    return f'company_docs/user_{instance.user.id}/{filename}'

class CompanyDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to=user_directory_path)  # вот здесь меняем
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.file.name}"

class RegisteredCompany(models.Model):
    country = models.CharField(max_length=100)
    code = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.country} | {self.code}"


class SuspiciousAttempt(models.Model):
    country = models.CharField(max_length=100)
    code = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attempt: {self.country} {self.code} ({self.ip_address})"

# models.py
class BookingRequest(models.Model):
    STATUS_CHOICES = [
        ('Waiting', 'Waiting'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
        ('Finished', 'Finished'),
        ('Cancelled', 'Cancelled'),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests', null=True, blank=True)  # ✅ добавь это
    cargo = models.ForeignKey(Cargo, on_delete=models.CASCADE, related_name='booking_requests', null=True, blank=True)
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name='booking_requests', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Waiting')
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)    
    updated_at = models.DateTimeField(auto_now=True)
    sender_deleted = models.BooleanField(default=False)
    receiver_deleted = models.BooleanField(default=False)

    sent_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    finished_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finished_booking_requests'
    )
    archived_at = models.DateTimeField(null=True, blank=True)


    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['sender', 'cargo'], name='unique_sender_cargo', condition=Q(cargo__isnull=False)),
            models.UniqueConstraint(fields=['sender', 'truck'], name='unique_sender_truck', condition=Q(truck__isnull=False)),
            models.UniqueConstraint(fields=['sender', 'cargo'], condition=Q(status__in=['Waiting', 'Accepted']), name='unique_active_cargo_request'),
            models.UniqueConstraint(fields=['sender', 'truck'], condition=Q(status__in=['Waiting', 'Accepted']), name='unique_active_truck_request'),
        ]

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['sender', 'cargo'],
                condition=Q(status__in=['Waiting', 'Accepted']),
                name='unique_active_cargo_request'
            ),
            UniqueConstraint(
                fields=['sender', 'truck'],
                condition=Q(status__in=['Waiting', 'Accepted']),
                name='unique_active_truck_request'
            ),
        ]

class Notification(models.Model):
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'📩 {self.receiver.username}: {self.message[:30]}'

class TeamCompany(models.Model):
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_companies')
    created_at = models.DateTimeField(auto_now_add=True)
    registered_company = models.OneToOneField(
        'RegisteredCompany',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='team_company'
    )
    def __str__(self):
        return f"{self.name} (by {self.created_by.username})"


class TeamMember(models.Model):
    company = models.ForeignKey(TeamCompany, on_delete=models.CASCADE, related_name='members')
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=[('manager', 'Manager'), ('worker', 'Worker')], default='worker')
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    full_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.full_name} ({self.role}) – {self.company.name}"


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)

class CargoAdmin(models.Model):
    original = models.OneToOneField(Cargo, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_copy')
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    order_number = models.CharField(max_length=30, unique=True)

    # Ключевые данные
    loading_city_primary = models.CharField(max_length=255)
    unloading_city_primary = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    # ➕ Новые поля для хранения информации независимо от original:
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cargo_admin_senders')
    receiver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cargo_admin_receivers')
    sent_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    finished_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cargo_admin_finishers')
    archived_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.order_number} [ARCHIVED]"


class TruckAdmin(models.Model):
    original = models.OneToOneField(Truck, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_copy')

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    order_number = models.CharField(max_length=30, unique=True)

    # Основные поля
    loading_city = models.CharField(max_length=100, null=True)
    unloading_city = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ➕ Новые поля:
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='truck_admin_senders')
    receiver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='truck_admin_receivers')
    sent_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    finished_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='truck_admin_finishers')
    archived_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.order_number} [ARCHIVED]"


@receiver(post_save, sender=Cargo)
def sync_cargo_admin_copy(sender, instance, created, **kwargs):
    from .models import CargoAdmin

    if created:
        if not hasattr(instance, 'admin_copy'):
            CargoAdmin.objects.create(
                original=instance,
                user=instance.user,
                order_number=f"{instance.order_number}_1",
                loading_city_primary=instance.loading_city_primary,
                unloading_city_primary=instance.unloading_city_primary,
                created_at=instance.created_at,
            )
    else:
        try:
            admin_copy = instance.admin_copy  # 🟢 вот это ты пропустил
            admin_copy.loading_city_primary = instance.loading_city_primary
            admin_copy.unloading_city_primary = instance.unloading_city_primary
            admin_copy.date_from = instance.date_from
            admin_copy.cargo_type = instance.cargo_type
            admin_copy.price = instance.price
            admin_copy.save()
        except CargoAdmin.DoesNotExist:
            pass



@receiver(post_save, sender=Truck)
def sync_truck_admin_copy(sender, instance, created, **kwargs):
    from .models import TruckAdmin

    if created:
        if not hasattr(instance, 'admin_copy'):
            TruckAdmin.objects.create(
                original=instance,
                user=instance.user,
                order_number=f"{instance.order_number}_1",
                loading_city=instance.loading_city,
                unloading_city=instance.unloading_city,
                created_at=instance.created_at,
            )
    else:
        try:
            admin_copy = instance.admin_copy
            admin_copy.loading_city = instance.loading_city
            admin_copy.unloading_city = instance.unloading_city
            admin_copy.vehicle_type = instance.vehicle_type
            admin_copy.loading_date_from = instance.loading_date_from
            admin_copy.loading_date_to = instance.loading_date_to
            admin_copy.price = instance.price
            admin_copy.save()
        except TruckAdmin.DoesNotExist:
            pass 

class Review(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_left')
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    booking = models.ForeignKey(BookingRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')

    cargo_order_number = models.CharField(max_length=30, null=True, blank=True)
    cargo_loading_city = models.CharField(max_length=255, null=True, blank=True)
    cargo_unloading_city = models.CharField(max_length=255, null=True, blank=True)
    cargo_type = models.CharField(max_length=255, null=True, blank=True)
    cargo_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    truck_order_number = models.CharField(max_length=30, null=True, blank=True)
    truck_loading_city = models.CharField(max_length=255, null=True, blank=True)
    truck_unloading_city = models.CharField(max_length=255, null=True, blank=True)
    truck_type = models.CharField(max_length=255, null=True, blank=True)
    truck_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)


    rating = models.PositiveSmallIntegerField()  # 1–5
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_visible = models.BooleanField(default=False)  # Видно ли второму пользователю

    class Meta:
        unique_together = ('author', 'target_user', 'booking')

    def __str__(self):
        return f"{self.author.username} → {self.target_user.username} ({self.rating}★)"

    def save(self, *args, **kwargs):
        if self.booking:
            if self.booking.cargo:
                self.cargo_order_number = self.booking.cargo.order_number
                self.cargo_loading_city = self.booking.cargo.loading_city_primary
                self.cargo_unloading_city = self.booking.cargo.unloading_city_primary
                self.cargo_type = self.booking.cargo.cargo_type
                self.cargo_price = self.booking.cargo.price

            if self.booking.truck:
                self.truck_order_number = self.booking.truck.order_number
                self.truck_loading_city = self.booking.truck.loading_city
                self.truck_unloading_city = self.booking.truck.unloading_city
                self.truck_type = self.booking.truck.vehicle_type
                self.truck_price = self.booking.truck.price

        super().save(*args, **kwargs)



