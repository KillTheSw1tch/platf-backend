from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile

from django.db.models.signals import pre_save
from django.utils import timezone
from .models import BookingRequest

from .models import CargoAdmin, TruckAdmin

@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)

@receiver(pre_save, sender=BookingRequest)
def set_booking_timestamps(sender, instance, **kwargs):
    if not instance.pk:
        # Новый запрос
        instance.sent_at = timezone.now()
    else:
        # Обновление
        try:
            previous = BookingRequest.objects.get(pk=instance.pk)
        except BookingRequest.DoesNotExist:
            previous = None

        if previous:
            # accepted_at
            if previous.status != 'Accepted' and instance.status == 'Accepted':
                instance.accepted_at = timezone.now()

            # finished_at + finished_by
            if previous.status != 'Finished' and instance.status == 'Finished':
                instance.finished_at = timezone.now()
                if not instance.finished_by:
                    instance.finished_by = instance.receiver

            # archived_at (если статус сменился на Finished или Cancelled)
            if previous.status != instance.status and instance.status in ['Finished', 'Cancelled']:
                instance.archived_at = timezone.now()

@receiver(post_save, sender=BookingRequest)
def update_admin_records(sender, instance, **kwargs):
    # Для CargoAdmin
    if instance.cargo:
        try:
            admin = instance.cargo.admin_copy
            if admin:
                admin.sender = instance.sender
                admin.receiver = instance.receiver
                admin.sent_at = instance.sent_at
                admin.accepted_at = instance.accepted_at
                admin.finished_at = instance.finished_at
                admin.finished_by = instance.finished_by
                admin.archived_at = instance.archived_at
                admin.status = instance.status
                admin.save()
        except CargoAdmin.DoesNotExist:
            pass

    # Для TruckAdmin
    if instance.truck:
        try:
            admin = instance.truck.admin_copy
            if admin:
                admin.sender = instance.sender
                admin.receiver = instance.receiver
                admin.sent_at = instance.sent_at
                admin.accepted_at = instance.accepted_at
                admin.finished_at = instance.finished_at
                admin.finished_by = instance.finished_by
                admin.archived_at = instance.archived_at
                admin.status = instance.status
                admin.save()
        except TruckAdmin.DoesNotExist:
            pass
