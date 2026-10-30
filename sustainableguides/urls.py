from django.urls import path
from .views import guide_list, guide_detail, user_drafts, submit_draft, edit_draft, delete_draft

app_name = 'sustainableguides'

urlpatterns = [
    path('', guide_list, name='list'),
    path('<int:id>/', guide_detail, name='detail'),
    path('my-submissions/', user_drafts, name='my_submissions'),
    path('submit/', submit_draft, name='submit_draft'),
    path('submissions/<int:id>/edit/', edit_draft, name='edit_draft'),
    path('submissions/<int:id>/delete/', delete_draft, name='delete_draft'),
]