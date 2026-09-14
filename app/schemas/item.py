"""商品：纯 Pydantic 模型（不落库，内存存储用）"""
from typing import Optional

from pydantic import BaseModel, Field


class Item(BaseModel):
    name: str = Field(..., example="手机", description="商品名称")
    description: Optional[str] = Field(None, example="一部新手机")
    price: float = Field(..., gt=0, example=5999.0, description="价格，必须大于 0")
    tax: Optional[float] = Field(None, example=100.0)


class ItemResponse(BaseModel):
    name: str
    price_with_tax: float
