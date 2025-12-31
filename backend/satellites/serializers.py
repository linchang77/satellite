from rest_framework import serializers
from .models import Scenario, Satellite


class SatelliteSerializer(serializers.ModelSerializer):
    """卫星序列化器"""
    class Meta:
        model = Satellite
        fields = '__all__'


class ScenarioSerializer(serializers.ModelSerializer):
    """场景序列化器"""
    satellites_count = serializers.SerializerMethodField()

    class Meta:
        model = Scenario
        fields = '__all__'

    def get_satellites_count(self, obj):
        """获取该场景下的卫星数量"""
        return obj.satellites.count()


class ScenarioListSerializer(serializers.ModelSerializer):
    """场景列表序列化器（不包含卫星详情）"""
    satellites_count = serializers.SerializerMethodField()

    class Meta:
        model = Scenario
        fields = ['id', 'name', 'epoch', 'start_time', 'end_time', 
                  'alt_km', 'inc_deg', 'n_planes', 'n_sats_per_plane',
                  'satellites_count']

    def get_satellites_count(self, obj):
        """获取该场景下的卫星数量"""
        return obj.satellites.count()

