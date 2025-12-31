from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScenarioViewSet, SatelliteViewSet

router = DefaultRouter()
router.register(r'scenarios', ScenarioViewSet, basename='scenario')
router.register(r'satellites', SatelliteViewSet, basename='satellite')

urlpatterns = [
    path('', include(router.urls)),
]

