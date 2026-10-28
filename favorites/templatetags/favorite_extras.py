from django import template

from favorites.presentation import button_context

register = template.Library()


@register.inclusion_tag("favorites/components/button.html", takes_context=True)
def favorite_button(context, listing, slot="card"):
    return {
        **button_context(context["request"], listing, member=context.get("favorite_member", False), slot=slot),
        "csrf_token": context.get("csrf_token"),
    }
