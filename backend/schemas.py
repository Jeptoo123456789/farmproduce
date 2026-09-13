from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class FarmerBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(..., min_length=7, max_length=30)
    email: EmailStr
    location: str = Field(..., min_length=2, max_length=150)
    farmName: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None


class FarmerCreate(FarmerBase):
    pass


class FarmerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    phone: Optional[str] = Field(default=None, min_length=7, max_length=30)
    email: Optional[EmailStr] = None
    location: Optional[str] = Field(default=None, min_length=2, max_length=150)
    farmName: Optional[str] = Field(default=None, min_length=2, max_length=150)
    description: Optional[str] = None


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = None


class ProductBase(BaseModel):
    farmerId: str
    categoryId: str
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    unit: str = Field(..., min_length=1, max_length=50)
    quantityAvailable: int = Field(..., ge=0)
    location: str = Field(..., min_length=2, max_length=150)
    imageUrl: Optional[str] = None
    status: Literal["AVAILABLE", "OUT_OF_STOCK", "INACTIVE"] = "AVAILABLE"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"AVAILABLE", "OUT_OF_STOCK", "INACTIVE"}
        if v not in allowed:
            raise ValueError("status must be one of AVAILABLE, OUT_OF_STOCK, INACTIVE")
        return v


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    farmerId: Optional[str] = None
    categoryId: Optional[str] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    unit: Optional[str] = Field(default=None, min_length=1, max_length=50)
    quantityAvailable: Optional[int] = Field(default=None, ge=0)
    location: Optional[str] = Field(default=None, min_length=2, max_length=150)
    imageUrl: Optional[str] = None
    status: Optional[Literal["AVAILABLE", "OUT_OF_STOCK", "INACTIVE"]] = None


class ProductStockAdjust(BaseModel):
    amount: int = Field(..., gt=0)


class BuyerBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(..., min_length=7, max_length=30)
    email: EmailStr
    location: str = Field(..., min_length=2, max_length=150)


class BuyerCreate(BuyerBase):
    pass


class BuyerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    phone: Optional[str] = Field(default=None, min_length=7, max_length=30)
    email: Optional[EmailStr] = None
    location: Optional[str] = Field(default=None, min_length=2, max_length=150)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Literal["buyer", "seller"]


class BuyerRegistration(BuyerBase):
    password: str = Field(..., min_length=8)


class SellerRegistration(FarmerBase):
    password: str = Field(..., min_length=8)


class OrderItemCreate(BaseModel):
    productId: str
    quantity: int = Field(..., gt=0)


class OrderCreate(BaseModel):
    buyerId: str
    deliveryLocation: str = Field(..., min_length=2, max_length=150)
    items: List[OrderItemCreate]


class OrderStatusUpdate(BaseModel):
    status: Literal["PENDING", "CONFIRMED", "PROCESSING", "READY", "COMPLETED", "CANCELLED"]


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    totalPages: int


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Any = None
    error: Optional[str] = None
