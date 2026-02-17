from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser

@receiver(post_save, sender=CustomUser)
def authorize_new_user(sender, instance, created, **kwargs):
    if created and not instance.is_authorized:
        # Keep newly created accounts login-ready by default in this setup.
        CustomUser.objects.filter(pk=instance.pk).update(is_authorized=True)
