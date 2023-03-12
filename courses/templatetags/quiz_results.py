from django import template
from accounts.models import StudentQuizResult
from django.db.models import Avg

register = template.Library()


@register.simple_tag(name="quiz_results")
def quiz_results(user, quiz):
    results = StudentQuizResult.objects.filter(quiz=quiz, user=user)
    if results.exists():
        first_result = results.first().score
        last_result = results.last().score
        avg_result = results.aggregate(avg=Avg("score"))["avg"]
        return {
            "results": results,
            "first_result": first_result,
            "last_result": last_result,
            "avg_result": avg_result,
        }
    return None
