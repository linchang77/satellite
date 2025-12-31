from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Scenario, Satellite
from .serializers import (
    ScenarioSerializer,
    ScenarioListSerializer,
    SatelliteSerializer
)


class ScenarioViewSet(viewsets.ModelViewSet):
    """场景视图集"""
    queryset = Scenario.objects.all().order_by('-id')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ScenarioListSerializer
        return ScenarioSerializer

    @action(detail=True, methods=['get'])
    def satellites(self, request, pk=None):
        """获取指定场景下的所有卫星"""
        scenario = self.get_object()
        satellites = scenario.satellites.all()
        serializer = SatelliteSerializer(satellites, many=True)
        return Response(serializer.data)


class SatelliteViewSet(viewsets.ModelViewSet):
    """卫星视图集"""
    queryset = Satellite.objects.all().order_by('plane_index', 'sat_index_in_plane')
    serializer_class = SatelliteSerializer

    def get_queryset(self):
        """支持通过场景ID过滤卫星"""
        queryset = super().get_queryset()
        scenario_id = self.request.query_params.get('scenario_id', None)
        if scenario_id:
            queryset = queryset.filter(scenario_id=scenario_id)
        return queryset

