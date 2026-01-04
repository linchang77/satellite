# 云原生卫星网络可视化系统

这是一个基于云原生架构的卫星网络可视化系统，用于模拟和展示卫星星座的拓扑结构、轨道参数和网络连接关系。该系统采用前后端分离架构，后端使用Django框架提供RESTful API，前端使用Vue.js和Cesium进行3D可视化展示。

## 项目特性

- **卫星星座管理**：支持多种卫星星座场景的配置和管理
- **3D可视化**：基于Cesium的卫星轨道和拓扑3D展示
- **网络拓扑分析**：实时展示卫星间的连接关系和跳数
- **时间序列数据**：支持时间窗口内的卫星状态变化分析
- **路由数据集成**：包含详细的网络接口、QoS和路由表数据

## 技术栈

### 后端
- **Django**：Python Web框架
- **Django REST Framework**：API开发
- **PostgreSQL**：数据库（支持JSON字段）
- **Python 3.8+**

### 前端
- **Vue.js 3**：前端框架
- **Vite**：构建工具
- **Cesium**：3D地球和卫星可视化
- **V-Network-Graph**：网络拓扑图组件

## 安装和运行

### 环境要求

- Python 3.8+
- Node.js 16+
- PostgreSQL
### 前端设置

1. **进入前端目录**
   ```bash
   cd frontend
   ```

2. **安装依赖**
   ```bash
   npm install
   ```

3. **运行开发服务器**
   ```bash
   npm run dev
   ```
   
   前端将在 `http://localhost:5173/` 启动

### 后端设置

1. **进入后端目录**
   ```bash
   cd backend
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **数据库配置**
   
   编辑 `config/settings.py` 中的数据库配置：
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'satellite_db',
           'USER': 'your_username',
           'PASSWORD': 'your_password',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```

4. **数据库迁移**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
5. **运行后端服务器**
   ```bash
   python manage.py runserver
   ```
   
   服务器将在 `http://127.0.0.1:8000/` 启动



### 完整项目运行

1. **启动后端**（在backend目录）
   ```bash
   python manage.py runserver
   ```

2. **启动前端**（在frontend目录）
   ```bash
   npm run dev
   ```

3. **访问应用**
   
   打开浏览器访问 `http://localhost:5173/`

## API文档

后端提供以下主要API端点：

- `GET /api/scenarios/` - 获取所有场景
- `GET /api/scenarios/{id}/satellites/` - 获取场景下的卫星
- `GET /api/satellites/{id}/topology/` - 获取卫星拓扑数据

详细API文档请参考后端代码中的视图和序列化器。

## 数据说明

### 卫星数据
- **场景（Scenario）**：卫星星座的基本配置参数
- **卫星（Satellite）**：单个卫星的轨道参数和状态信息

### 网络数据
- **跳跃时间窗口**：卫星间的通信时间窗口
- **邻居关系**：卫星间的连接拓扑
- **路由器数据**：网络层的路由和QoS信息

## 开发指南

### 后端开发
- 使用Django REST Framework开发API
- 数据模型定义在 `satellites/models.py`
- API视图在 `satellites/views.py`

### 前端开发
- 组件放在 `src/components/` 目录
- API调用封装在 `src/api/` 目录
- 使用Cesium进行3D可视化

### 数据导入
运行 `backend/inser_data.py` 脚本导入CSV数据到数据库。
