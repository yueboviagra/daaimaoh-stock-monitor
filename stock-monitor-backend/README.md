# 大魔王库存监控 - 后端服务

每天中午 12:00（日本时间）自动抓取 [daimaoh.co.jp](https://daimaoh.co.jp) 上 14 个商品的库存情况。

## 功能

- 🔄 每天 12:00 自动检查所有商品库存
- 📊 Web 仪表盘查看最新库存状态
- 📋 历史记录追踪库存变化
- 🔔 自动对比上次检查，高亮库存变化
- 🐳 Docker 部署，一键运行

## 本地开发

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 运行

```bash
cd stock-monitor-backend
python -m uvicorn app.main:app --reload --port 8000
```

### 3. 访问

打开浏览器访问 http://localhost:8000

## Docker 部署（群晖 NAS）

### 方式一：docker-compose（推荐）

```bash
cd stock-monitor-backend
docker compose up -d
```

### 方式二：群晖 Container Manager

1. 将 `stock-monitor-backend` 文件夹上传到 NAS
2. 打开 Container Manager → 项目 → 新增
3. 选择 `stock-monitor-backend` 文件夹
4. 使用现有的 `docker-compose.yml`
5. 启动

访问 `http://<NAS-IP>:8000`

## 数据持久化

SQLite 数据库保存在 `data/stock_monitor.db`，通过 Docker volume 挂载，重启容器数据不丢失。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 仪表盘页面 |
| GET | `/api/status` | 最新检查结果 |
| GET | `/api/history` | 历史记录 |
| POST | `/api/scrape` | 手动触发检查 |
| GET | `/api/health` | 健康检查 |
