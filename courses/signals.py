from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from .models import StudyGroup
from .assignment_service import sync_group_membership


@receiver(m2m_changed, sender=StudyGroup.users.through)
def sync_group_assignments_on_membership_change(sender, instance, action, **kwargs):
    """
    Синхронизирует назначения курсов при изменении состава группы.
    Вызывается сервисный слой, ошибки не подавляются.
    """
    if action in ("post_add", "post_remove", "post_clear"):
        sync_group_membership(instance)
