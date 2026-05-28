"""
数据库层 — SQLAlchemy 模型和数据库操作
"""
from datetime import datetime, timedelta

from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    DateTime, ForeignKey, UniqueConstraint, Index, func,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship
from sqlalchemy.sql import text

from app.config import DATABASE_URL, PRODUCTS

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    series = Column(String)
    url = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())

    stock_records = relationship("StockRecord", back_populates="product")


class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    checked_at = Column(DateTime, nullable=False, default=func.now())
    status = Column(String, nullable=False, default="success")  # success | partial | error
    error_msg = Column(String, nullable=True)

    stock_records = relationship("StockRecord", back_populates="snapshot")


class StockRecord(Base):
    __tablename__ = "stock_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant = Column(String, nullable=False)
    in_stock = Column(Boolean, nullable=False)

    snapshot = relationship("Snapshot", back_populates="stock_records")
    product = relationship("Product", back_populates="stock_records")

    __table_args__ = (
        UniqueConstraint("snapshot_id", "product_id", "variant", name="uq_stock_record"),
        Index("idx_stock_snapshot", "snapshot_id"),
        Index("idx_stock_product", "product_id"),
    )


class SnapshotIndex(Base):
    """快照时间索引，加速查询"""
    __tablename__ = "snapshot_index"

    snapshot_id = Column(Integer, primary_key=True)
    checked_at = Column(DateTime, nullable=False, index=True)


def init_db():
    """初始化数据库：创建表和种子数据"""
    import os
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(engine)
    _seed_products()


def _seed_products():
    """插入商品目录（如果为空）"""
    with Session(engine) as session:
        existing = session.query(Product).count()
        if existing == 0:
            for p in PRODUCTS:
                session.add(Product(
                    item_code=p["item_code"],
                    name=p["name"],
                    series=p["series"],
                    url=p["url"],
                ))
            session.commit()


def get_session() -> Session:
    """获取一个新的数据库会话"""
    return Session(engine)


def save_snapshot(results: list[dict]) -> dict:
    """
    保存一次抓取的所有结果。
    results: [{item_code, name, stocks: [{variant, in_stock}], error}]
    """
    with Session(engine) as session:
        # 确定状态
        errors = [r for r in results if r["error"]]
        if len(errors) == len(results):
            status = "error"
        elif errors:
            status = "partial"
        else:
            status = "success"

        error_msg = "; ".join(
            f"{r['item_code']}: {r['error']}" for r in errors
        ) or None

        # 创建快照
        snapshot = Snapshot(
            checked_at=datetime.now(),
            status=status,
            error_msg=error_msg,
        )
        session.add(snapshot)
        session.flush()  # 获取 snapshot.id

        # 查询商品 ID 映射
        product_map = {
            p.item_code: p.id
            for p in session.query(Product).all()
        }

        # 保存每条库存记录
        record_count = 0
        for r in results:
            product_id = product_map.get(r["item_code"])
            if not product_id:
                continue

            for s in r.get("stocks", []):
                session.add(StockRecord(
                    snapshot_id=snapshot.id,
                    product_id=product_id,
                    variant=s["variant"],
                    in_stock=s["in_stock"],
                ))
                record_count += 1

        session.commit()
        return {
            "snapshot_id": snapshot.id,
            "status": status,
            "record_count": record_count,
            "error_count": len(errors),
        }


def get_latest_snapshot() -> dict | None:
    """获取最新一次检查的完整结果"""
    with Session(engine) as session:
        snapshot = (
            session.query(Snapshot)
            .order_by(Snapshot.checked_at.desc())
            .first()
        )
        if not snapshot:
            return None

        return _format_snapshot(session, snapshot)


def get_snapshot_history(limit: int = 30) -> list[dict]:
    """获取最近的快照摘要列表"""
    with Session(engine) as session:
        snapshots = (
            session.query(Snapshot)
            .order_by(Snapshot.checked_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": s.id,
                "checked_at": s.checked_at.isoformat(),
                "status": s.status,
                "record_count": len(s.stock_records),
            }
            for s in snapshots
        ]


def get_snapshot_detail(snapshot_id: int) -> dict | None:
    """获取单个快照的详细信息"""
    with Session(engine) as session:
        snapshot = session.query(Snapshot).filter_by(id=snapshot_id).first()
        if not snapshot:
            return None
        return _format_snapshot(session, snapshot)


def get_snapshot_detail(snapshot_id: int) -> dict | None:
    """获取单个快照的详细信息"""
    with Session(engine) as session:
        snapshot = session.query(Snapshot).filter_by(id=snapshot_id).first()
        if not snapshot:
            return None
        return _format_snapshot(session, snapshot)


def get_stock_changes() -> list[dict]:
    """对比最近两次快照，找出库存变化的商品"""
    with Session(engine) as session:
        snapshots = (
            session.query(Snapshot)
            .order_by(Snapshot.checked_at.desc())
            .limit(2)
            .all()
        )

        if len(snapshots) < 2:
            return []

        current = snapshots[0]
        previous = snapshots[1]

        changes = []
        current_records = {
            (r.product_id, r.variant): r.in_stock
            for r in current.stock_records
        }
        previous_records = {
            (r.product_id, r.variant): r.in_stock
            for r in previous.stock_records
        }

        # 获取商品名称映射
        product_names = {
            p.id: p.name
            for p in session.query(Product).all()
        }

        # 检查所有当前记录中与之前不同的
        for (pid, variant), in_stock in current_records.items():
            prev_stock = previous_records.get((pid, variant))
            if prev_stock is not None and prev_stock != in_stock:
                changes.append({
                    "product_name": product_names.get(pid, "未知"),
                    "variant": variant,
                    "from_stock": prev_stock,
                    "to_stock": in_stock,
                })

        return changes


def get_product_trend(item_code: str, days: int = 7) -> list[dict]:
    """获取单个商品最近 N 天的库存趋势"""
    with Session(engine) as session:
        product = session.query(Product).filter_by(item_code=item_code).first()
        if not product:
            return []

        cutoff = datetime.now() - timedelta(days=days)
        records = (
            session.query(StockRecord, Snapshot.checked_at)
            .join(Snapshot)
            .filter(
                StockRecord.product_id == product.id,
                Snapshot.checked_at >= cutoff,
            )
            .order_by(Snapshot.checked_at.desc())
            .all()
        )

        # 按快照时间分组
        result = []
        for record, checked_at in records:
            result.append({
                "checked_at": checked_at.isoformat(),
                "variant": record.variant,
                "in_stock": record.in_stock,
            })
        return result


def _format_snapshot(session: Session, snapshot: Snapshot) -> dict:
    """将快照格式化为 API 响应结构"""
    products = session.query(Product).all()
    product_map = {p.id: p for p in products}

    # 按商品分组
    grouped = {}
    for record in snapshot.stock_records:
        pid = record.product_id
        if pid not in grouped:
            product = product_map.get(pid)
            grouped[pid] = {
                "item_code": product.item_code if product else "未知",
                "name": product.name if product else "未知",
                "series": product.series if product else "",
                "url": product.url if product else "",
                "stocks": [],
            }
        grouped[pid]["stocks"].append({
            "variant": record.variant,
            "in_stock": record.in_stock,
        })

    # 计算摘要
    for pid, data in grouped.items():
        in_stock_count = sum(1 for s in data["stocks"] if s["in_stock"])
        total_count = len(data["stocks"])
        data["summary"] = f"{in_stock_count}/{total_count}"
        data["has_stock"] = in_stock_count > 0

    return {
        "id": snapshot.id,
        "checked_at": snapshot.checked_at.isoformat(),
        "status": snapshot.status,
        "error_msg": snapshot.error_msg,
        "products": list(grouped.values()),
    }
