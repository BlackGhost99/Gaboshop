from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import CategoryCommission


@receiver(pre_save, sender=CategoryCommission)
def store_old_rate(sender, instance, **kwargs):
    """Attach the current base_rate to the instance before save (if exists)."""
    if instance.pk:
        try:
            old = CategoryCommission.objects.get(pk=instance.pk)
            instance._old_base_rate = old.base_rate
        except CategoryCommission.DoesNotExist:
            instance._old_base_rate = None
    else:
        instance._old_base_rate = None
