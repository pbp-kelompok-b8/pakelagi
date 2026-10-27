from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    listing = models.ForeignKey("listings.Listing", on_delete=models.CASCADE, related_name="favorites")
    note = models.TextField("Catatan pribadi", blank=True, max_length=1000, validators=[MaxLengthValidator(1000)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["user", "listing"], name="unique_user_listing_favorite")]

    def __str__(self):
        return f"Favorite {self.pk} (user={self.user_id}, listing={self.listing_id})"
