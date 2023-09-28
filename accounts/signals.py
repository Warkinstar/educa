from django.db.models.signals import post_save
from django.contrib.auth.models import Group
from django.dispatch import receiver
from .models import TeacherRequest


@receiver(post_save, sender=TeacherRequest)
def check_teacher_group_reguest(sender, instance, **kwargs):
    """Если TeacherRequest.status approved добавить пользователя в группу Преподаватели
       Если TeacherRequest.status rejected удалить его из группы или ничего не делать
    """
    group = "Преподаватели"
    if instance.status == "approved":
        instance.user.groups.add(Group.objects.get(name=group))
    elif instance.status == "rejected":
        instance.user.groups.remove(Group.objects.get(name=group))
