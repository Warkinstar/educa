from django import template


register = template.Library()


@register.filter(name="has_answer")
def has_answer(user, task):
    """Если пользоваетль дава answer на task, вернуть answer, иначе False"""
    answer = user.task_answers.filter(task=task)
    if answer.exists():
        return answer
    else:
        return False
