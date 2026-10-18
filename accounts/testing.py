"""Reusable account fixtures, independent of individual test modules."""
PASSWORD = "Preloved!Strong9382"


def registration_data(**overrides):
    data = {
        "username": "nina.arum",
        "password1": PASSWORD,
        "password2": PASSWORD,
    }
    data.update(overrides)
    return data
