from django.urls import path
from .views import guide_list, guide_detail, user_drafts, edit_draft, delete_draft

app_name = 'sustainableguides'

urlpatterns = [
    path('', guide_list, name='list'),
    path('<int:id>/', guide_detail, name='detail'),
    path('drafts/', user_drafts, name='drafts'),
    path('drafts/<int:id>/edit/', edit_draft, name='edit_draft'),
    path('drafts/<int:id>/delete/', delete_draft, name='delete_draft'),
]