from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable
import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.models import Buyer, Category, Farmer, Order, OrderItem, Product

ALLOWED_ORDER_STATUSES = {"PENDING", "CONFIRMED", "PROCESSING", "READY", "COMPLETED", "CANCELLED"}
PRODUCT_STATUSES = {"AVAILABLE", "OUT_OF_STOCK", "INACTIVE"}


def as_success(message: str, data: Any = None):
    return {"success": True, "message": message, "data": data if data is not None else {}}


def as_error(message: str, error_code: str = "ERROR"):
    return {"success": False, "message": message, "error": error_code}


def ensure_product_status(product: Product):
    if product.quantityAvailable <= 0:
        product.status = "OUT_OF_STOCK"
    elif product.status != "INACTIVE":
        product.status = "AVAILABLE"
    product.updatedAt = datetime.utcnow()
    return product


def generate_id() -> str:
    return str(uuid.uuid4())


def get_farmer(db: Session, farmer_id: str):
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=as_error("Farmer not found", "FARMER_NOT_FOUND"))
    return farmer


def list_farmers(db: Session):
    return db.query(Farmer).order_by(Farmer.createdAt.desc()).all()


def create_farmer(db: Session, payload: dict):
    farmer = Farmer(**payload, id=generate_id())
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return farmer


def update_farmer(db: Session, farmer_id: str, payload: dict):
    farmer = get_farmer(db, farmer_id)
    for field, value in payload.items():
        if value is not None:
            setattr(farmer, field, value)
    farmer.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(farmer)
    return farmer


def delete_farmer(db: Session, farmer_id: str):
    farmer = get_farmer(db, farmer_id)
    db.delete(farmer)
    db.commit()
    return None


def get_category(db: Session, category_id: str):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=as_error("Category not found", "CATEGORY_NOT_FOUND"))
    return category


def list_categories(db: Session):
    return db.query(Category).order_by(Category.createdAt.desc()).all()


def create_category(db: Session, payload: dict):
    if db.query(Category).filter(Category.name.ilike(payload["name"])).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=as_error("Category name already exists", "CATEGORY_ALREADY_EXISTS"))
    category = Category(**payload, id=generate_id())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: str, payload: dict):
    category = get_category(db, category_id)
    if "name" in payload and payload["name"] is not None:
        existing = db.query(Category).filter(Category.name.ilike(payload["name"]), Category.id != category_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=as_error("Category name already exists", "CATEGORY_ALREADY_EXISTS"))
    for field, value in payload.items():
        if value is not None:
            setattr(category, field, value)
    category.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: str):
    category = get_category(db, category_id)
    db.delete(category)
    db.commit()
    return None


def get_product(db: Session, product_id: str):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=as_error("Product not found", "PRODUCT_NOT_FOUND"))
    return product


def list_products(db: Session, *, category: str | None, farmer: str | None, location: str | None, min_price: float | None, max_price: float | None, status: str | None, search: str | None, page: int, limit: int, sort_by: str, order: str):
    query = db.query(Product)

    if category:
        query = query.join(Product.category).filter(Category.name.ilike(category.strip()))
    if farmer:
        query = query.join(Product.farmer).filter(
            Farmer.id == farmer.strip() |
            Farmer.name.ilike(farmer.strip()) |
            Farmer.farmName.ilike(farmer.strip())
        )
    if location:
        query = query.filter(Product.location.ilike(f"%{location.strip()}%"))
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if status:
        query = query.filter(Product.status == status.upper())
    if search:
        term = f"%{search.strip()}%"
        query = query.outerjoin(Product.category).outerjoin(Product.farmer)
        query = query.filter(
            or_(
                Product.name.ilike(term),
                Product.description.ilike(term),
                Product.location.ilike(term),
                Product.unit.ilike(term),
                Category.name.ilike(term),
                Farmer.name.ilike(term),
                Farmer.farmName.ilike(term),
                Farmer.location.ilike(term),
            )
        )

    valid_sort_fields = {"name": Product.name, "price": Product.price, "createdAt": Product.createdAt, "location": Product.location}
    sort_column = valid_sort_fields.get(sort_by, Product.createdAt)
    if order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    total = query.count()
    products = query.offset((page - 1) * limit).limit(limit).all()
    total_pages = max((total + limit - 1) // limit, 1) if total else 1
    return products, {"page": page, "limit": limit, "total": total, "totalPages": total_pages}


def create_product(db: Session, payload: dict):
    farmer = get_farmer(db, payload["farmerId"])
    category = get_category(db, payload["categoryId"])
    if payload["price"] < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=as_error("Product price cannot be negative", "INVALID_PRODUCT_PRICE"))
    if payload["quantityAvailable"] < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=as_error("Product quantity cannot be negative", "INVALID_PRODUCT_QUANTITY"))
    if payload["status"] not in PRODUCT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=as_error("Invalid product status", "INVALID_PRODUCT_STATUS"))
    product = Product(**payload, id=generate_id())
    if product.quantityAvailable <= 0:
        product.status = "OUT_OF_STOCK"
    elif product.status == "OUT_OF_STOCK":
        product.status = "AVAILABLE"

    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: str, payload: dict):
    product = get_product(db, product_id)
    if "farmerId" in payload and payload["farmerId"] is not None:
        get_farmer(db, payload["farmerId"])
    if "categoryId" in payload and payload["categoryId"] is not None:
        get_category(db, payload["categoryId"])
    if "price" in payload and payload["price"] is not None and payload["price"] < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=as_error("Product price cannot be negative", "INVALID_PRODUCT_PRICE"))
    if "quantityAvailable" in payload and payload["quantityAvailable"] is not None and payload["quantityAvailable"] < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=as_error("Product quantity cannot be negative", "INVALID_PRODUCT_QUANTITY"))
    for field, value in payload.items():
        if value is not None:
            setattr(product, field, value)
    if product.quantityAvailable <= 0:
        product.status = "OUT_OF_STOCK"
    elif product.status != "INACTIVE":
        product.status = "AVAILABLE"
    product.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: str):
    product = get_product(db, product_id)
    db.delete(product)
    db.commit()
    return None


def list_farmer_products(db: Session, farmer_id: str):
    get_farmer(db, farmer_id)
    return db.query(Product).filter(Product.farmerId == farmer_id).order_by(Product.createdAt.desc()).all()


def get_stock(db: Session, product_id: str):
    product = get_product(db, product_id)
    return product


def adjust_stock(db: Session, product_id: str, amount: int, direction: str):
    product = get_product(db, product_id)
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=as_error("Stock adjustment amount must be greater than zero", "INVALID_STOCK_AMOUNT"))
    if direction == "increase":
        product.quantityAvailable += amount
    elif direction == "decrease":
        if product.quantityAvailable == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=as_error("Stock cannot go below zero", "NEGATIVE_STOCK"))
        product.quantityAvailable = max(0, product.quantityAvailable - amount)
    ensure_product_status(product)
    db.commit()
    db.refresh(product)
    return product


def get_buyer(db: Session, buyer_id: str):
    buyer = db.query(Buyer).filter(Buyer.id == buyer_id).first()
    if not buyer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=as_error("Buyer not found", "BUYER_NOT_FOUND"))
    return buyer


def list_buyers(db: Session):
    return db.query(Buyer).order_by(Buyer.createdAt.desc()).all()


def create_buyer(db: Session, payload: dict):
    buyer = Buyer(**payload, id=generate_id())
    db.add(buyer)
    db.commit()
    db.refresh(buyer)
    return buyer


def update_buyer(db: Session, buyer_id: str, payload: dict):
    buyer = get_buyer(db, buyer_id)
    for field, value in payload.items():
        if value is not None:
            setattr(buyer, field, value)
    buyer.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(buyer)
    return buyer


def delete_buyer(db: Session, buyer_id: str):
    buyer = get_buyer(db, buyer_id)
    db.delete(buyer)
    db.commit()
    return None


def get_order(db: Session, order_id: str):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=as_error("Order not found", "ORDER_NOT_FOUND"))
    return order


def list_orders(db: Session):
    return db.query(Order).order_by(Order.createdAt.desc()).all()


def list_buyer_orders(db: Session, buyer_id: str):
    get_buyer(db, buyer_id)
    return db.query(Order).filter(Order.buyerId == buyer_id).order_by(Order.createdAt.desc()).all()


def list_farmer_orders(db: Session, farmer_id: str):
    get_farmer(db, farmer_id)
    query = (
        db.query(Order)
        .join(Order.items)
        .join(OrderItem.product)
        .filter(Product.farmerId == farmer_id)
        .distinct()
        .order_by(Order.createdAt.desc())
    )
    return query.all()


def update_order_status(db: Session, order_id: str, status_value: str):
    order = get_order(db, order_id)
    if status_value not in ALLOWED_ORDER_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=as_error("Invalid order status", "INVALID_ORDER_STATUS"))
    order.status = status_value
    order.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order


def create_order(db: Session, payload: dict):
    buyer = get_buyer(db, payload["buyerId"])
    if not payload.get("items"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=as_error("Order must contain at least one item", "EMPTY_ORDER"))

    order = Order(
        id=generate_id(),
        buyerId=buyer.id,
        deliveryLocation=payload["deliveryLocation"],
        totalAmount=0,
        status="PENDING",
    )
    db.add(order)
    db.flush()

    order_items = []
    total_amount = 0.0

    for item in payload["items"]:
        product = get_product(db, item["productId"])
        if product.status == "INACTIVE":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=as_error(f"Product {product.name} is inactive", "INACTIVE_PRODUCT"))
        if product.quantityAvailable <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=as_error(f"Product {product.name} is out of stock", "OUT_OF_STOCK"))
        if item["quantity"] <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=as_error(f"Quantity for {product.name} must be greater than zero", "INVALID_ORDER_QUANTITY"))
        if item["quantity"] > product.quantityAvailable:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=as_error(f"Insufficient stock for {product.name}", "INSUFFICIENT_STOCK"))

        unit_price = float(product.price)
        subtotal = unit_price * item["quantity"]
        order_item = OrderItem(
            id=generate_id(),
            orderId=order.id,
            productId=product.id,
            quantity=item["quantity"],
            unitPrice=unit_price,
            subtotal=subtotal,
        )
        order_items.append(order_item)
        total_amount += subtotal

    order.totalAmount = round(total_amount, 2)
    db.add_all(order_items)

    for item in order_items:
        product = db.query(Product).filter(Product.id == item.productId).first()
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=as_error("Product not found", "PRODUCT_NOT_FOUND"))
        product.quantityAvailable -= item.quantity
        ensure_product_status(product)

    db.commit()
    db.refresh(order)
    for item in order_items:
        db.refresh(item)
    order.items = order_items
    return order
