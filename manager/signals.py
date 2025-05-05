from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Permission
from django.core.mail import send_mail
from django.conf import settings

@receiver(post_save, sender=Permission)
def notify_user(sender, instance, created, raw, update_fields, **kwargs):
    subject = "Document Permission Notification"
    body = f"""
            Hey {instance.user.username},
            You've been granted {instance.level} access to {instance.document.name if instance.document else instance.folder.name}.
            """
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [instance.user.email],
        fail_silently=False
    )