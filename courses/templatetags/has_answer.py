from django import template


register = template.Library()


@register.filter(name="has_answer")
def has_answer(user, task):
    """Если пользователь давал answer на task, вернуть answer, иначе False"""
    answer = user.task_answers.filter(task=task).first
    if answer:
        return answer
    else:
        return False
