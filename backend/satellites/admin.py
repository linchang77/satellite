from django.contrib import admin
from .models import Scenario, Satellite


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'epoch', 'n_planes', 'n_sats_per_plane']
    list_filter = ['n_planes']
    search_fields = ['name']


@admin.register(Satellite)
class SatelliteAdmin(admin.ModelAdmin):
    list_display = ['id', 'sat_id', 'stk_name', 'scenario', 'plane_index', 'sat_index_in_plane']
    list_filter = ['scenario', 'plane_index']
    search_fields = ['sat_id', 'stk_name']

