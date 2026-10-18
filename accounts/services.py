"""Account-owned updates used by profile editing within its transaction."""


def update_account_email(user, email):
    user.email = email
    user.save(update_fields=["email"])
