from django.urls import path

from .views import GuideDetailAPIView, GuideListCreateAPIView, MyGuideSubmissionsAPIView

app_name = 'guides_api'
urlpatterns = [
    path('', GuideListCreateAPIView.as_view(), name='list'),
    path('my-submissions/', MyGuideSubmissionsAPIView.as_view(), name='my_submissions'),
    path('<int:id>/', GuideDetailAPIView.as_view(), name='detail'),
]
