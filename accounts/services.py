"""Account-owned updates and deletion of the currently supported account data."""

from datetime import timedelta

from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from accounts.models import AccountDeletionAttempt


class ConfirmationThrottled(Exception):
    pass


CONFIRMATION_ERROR = "Konfirmasi gagal. Periksa username dan password saat ini."


@sensitive_variables()
@transaction.atomic
def delete_confirmed_account(user_id, username, password):
    user = User.objects.select_for_update().filter(pk=user_id).first()
    if user is None or user.is_staff or user.is_superuser:
        return False
    now = timezone.now()
    attempt, _ = AccountDeletionAttempt.objects.get_or_create(
        user=user, defaults={"started_at": now},
    )
    if now - attempt.started_at >= timedelta(minutes=15):
        attempt.started_at = now
        attempt.failures = 0
    if attempt.failures >= 5:
        raise ConfirmationThrottled
    password_valid = user.check_password(password)
    if username != user.username or not password_valid:
        attempt.failures += 1
        attempt.save(update_fields=["started_at", "failures"])
        return False
    session_keys = [
        session.session_key
        for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator()
        if session.get_decoded().get(SESSION_KEY) == str(user.pk)
    ]
    Session.objects.filter(session_key__in=session_keys).delete()
    user.delete()
    return True


def update_account_email(user, email):
    user.email = email
    user.save(update_fields=["email"])
