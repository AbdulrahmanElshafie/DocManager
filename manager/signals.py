from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Permission, Document, Folder
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

"""
new doc in folder
moved doc to new folder
moved doc to root
new folder
moved folder to new folder
moved folder to root
"""

@receiver(pre_save, sender=Document)
def notify_user_document(sender, instance, created, raw, update_fields, **kwargs):
    # new doc in folder
    # moved doc to new folder
    # give the doc the same level as the parent folder


    new_folder_users = Permission.objects.filter(folder=instance.folder).values_list('user', flat=True).distinct()
    if instance.folder:
        for user in new_folder_users:
            Permission.objects.update_or_create(
                user=user,
                document=instance,
                defaults={'level': Permission.objects.get(user=user, folder=instance.folder).level, 'folder': None}
            )

    old_folder_users = Permission.objects.filter(document=instance).values_list('user', flat=True).distinct()
    if instance.folder:
        for user in old_folder_users:
            Permission.objects.filter(user=user, document=instance).delete()

    # moved doc to root
    # remove the doc from the previous folder and remove the permission
    if not instance.folder:
        Permission.objects.filter(user__in=old_folder_users, document=instance).delete()

@receiver(post_save, sender=Folder)
def notify_user_folder(sender, instance, created, raw, update_fields, **kwargs):
    # new folder
    # moved folder to new folder
    # give the folder the same level as the parent folder
    users = Permission.objects.filter(folder=instance.parent).values_list('user', flat=True).distinct()
    if instance.parent:
        for user in users:
            Permission.objects.update_or_create(
                user=user,
                folder=instance,
                defaults={'level': Permission.objects.get(user=user, folder=instance.parent).level, 'document': None}
            )

    # moved folder to root
    # remove the folder and all its children and remove the permission
    if not instance.parent:
        Permission.objects.filter(user__in=users, folder__parent=instance).delete()
