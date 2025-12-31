# Django 后端项目

这是一个使用Django框架开发的卫星数据管理后端项目。

## 项目结构

```
backend/
├── config/              # Django项目配置
│   ├── settings.py     # 项目设置（包含数据库配置）
│   ├── urls.py         # 主URL配置
│   └── ...
├── satellites/         # 卫星数据应用
│   ├── models.py       # 数据模型（Scenario, Satellite）
│   ├── views.py        # API视图
│   ├── serializers.py  # 序列化器
│   └── urls.py         # 应用URL配置
├── manage.py           # Django管理脚本
├── requirements.txt    # Python依赖
└── inser_data.py       # 数据导入脚本（保留）
```

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 数据库迁移

```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. 创建超级用户（可选）

```bash
python manage.py createsuperuser
```

### 4. 运行开发服务器

```bash
python manage.py runserver
```

服务器将在 `http://127.0.0.1:8000/` 启动

## API 端点

- `GET /api/scenarios/` - 获取所有场景列表
- `POST /api/scenarios/` - 创建新场景
- `GET /api/scenarios/{id}/` - 获取场景详情
- `GET /api/scenarios/{id}/satellites/` - 获取场景下的所有卫星
- `GET /api/satellites/` - 获取所有卫星（支持?scenario_id=过滤）
- `GET /api/satellites/{id}/` - 获取卫星详情

## 数据库配置

数据库配置在 `config/settings.py` 中：

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': 'weixingyunyuansheng',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 数据模型

- **Scenario（场景）**: 存储卫星场景配置信息
- **Satellite（卫星）**: 存储卫星轨道参数信息

