from django.conf import settings
from django.db import models


class AccountDeletionAttempt(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    failures = models.PositiveSmallIntegerField(default=0)
    started_at = models.DateTimeField()
