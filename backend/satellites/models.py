from django.db import models
from django.contrib.postgres.fields import JSONField


class Scenario(models.Model):
    """场景模型"""
    name = models.CharField(max_length=255, verbose_name='场景名称')
    epoch = models.CharField(max_length=100, verbose_name='历元时间')
    start_time = models.CharField(max_length=100, verbose_name='开始时间')
    end_time = models.CharField(max_length=100, verbose_name='结束时间')
    alt_km = models.FloatField(verbose_name='高度(km)')
    inc_deg = models.FloatField(verbose_name='倾角(度)')
    n_planes = models.IntegerField(verbose_name='轨道面数量')
    n_sats_per_plane = models.IntegerField(verbose_name='每轨道面卫星数')
    sensor_config = models.JSONField(verbose_name='传感器配置', null=True, blank=True)

    class Meta:
        db_table = 'scenarios'
        verbose_name = '场景'
        verbose_name_plural = '场景'

    def __str__(self):
        return self.name


class Satellite(models.Model):
    """卫星模型"""
    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name='satellites',
        verbose_name='所属场景'
    )
    sat_id = models.CharField(max_length=100, verbose_name='卫星ID')
    stk_name = models.CharField(max_length=255, verbose_name='STK名称')
    plane_index = models.IntegerField(verbose_name='轨道面索引')
    sat_index_in_plane = models.IntegerField(verbose_name='轨道面内卫星索引')
    alt_km = models.FloatField(verbose_name='高度(km)')
    sma_km = models.FloatField(verbose_name='半长轴(km)')
    ecc = models.FloatField(verbose_name='偏心率')
    inc_deg = models.FloatField(verbose_name='倾角(度)')
    raan_deg = models.FloatField(verbose_name='升交点赤经(度)')
    argp_deg = models.FloatField(verbose_name='近地点幅角(度)')
    ta_deg = models.FloatField(verbose_name='真近点角(度)')

    class Meta:
        db_table = 'satellites'
        verbose_name = '卫星'
        verbose_name_plural = '卫星'
        indexes = [
            models.Index(fields=['scenario', 'sat_id']),
            models.Index(fields=['plane_index', 'sat_index_in_plane']),
        ]

    def __str__(self):
        return f"{self.stk_name} ({self.sat_id})"

