from django.db import models
from django.conf import settings


class ChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_label = getattr(self.user, "email", None) or getattr(self.user, "username", str(self.user_id))
        return f"{user_label} - {self.created_at}"
