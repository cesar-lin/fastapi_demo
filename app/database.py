"""数据库连接配置：全局唯一的 engine"""
from sqlmodel import SQLModel, create_engine

sqlite_url = "sqlite:///app.db"   # 换 PostgreSQL 只需改这一行
engine = create_engine(sqlite_url, echo=True)  # echo=True 打印 SQL，便于学习

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
