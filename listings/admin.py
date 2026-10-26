from django.contrib import admin

from listings.models import Listing


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "category", "size", "condition", "price", "city", "status", "created_at")
    list_filter = ("status", "category", "size", "condition", "city")
    search_fields = ("title", "brand", "city", "seller__username")
    readonly_fields = ("sold_at", "created_at", "updated_at")
    actions = ["hide_listings"]

    @admin.action(description="Sembunyikan listing terpilih (moderasi)")
    def hide_listings(self, request, queryset):
        queryset.update(status=Listing.Status.HIDDEN)
