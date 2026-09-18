from __future__ import annotations

import base64
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from backend.auth import create_token, hash_password, verify_password
from backend.database import Base, engine, get_db
from backend.models import Buyer, Category, Farmer, Order, Product
from backend.schemas import (
    BuyerCreate,
    BuyerRegistration,
    BuyerUpdate,
    CategoryCreate,
    CategoryUpdate,
    FarmerCreate,
    FarmerUpdate,
    OrderCreate,
    OrderStatusUpdate,
    LoginRequest,
    ProductCreate,
    ImageUpload,
    SellerRegistration,
    ProductStockAdjust,
    ProductUpdate,
)
from backend.services import (
    adjust_stock,
    as_success,
    create_buyer,
    create_category,
    create_farmer,
    create_order,
    create_product,
    delete_buyer,
    delete_category,
    delete_farmer,
    delete_product,
    get_buyer,
    get_category,
    get_farmer,
    get_order,
    get_product,
    get_stock,
    list_buyer_orders,
    list_buyers,
    list_categories,
    list_farmer_orders,
    list_farmer_products,
    list_farmers,
    list_orders,
    list_products,
    update_buyer,
    update_category,
    update_farmer,
    update_order_status,
    update_product,
)

Base.metadata.create_all(bind=engine)


def ensure_auth_columns():
    """Add auth columns to databases created before authentication existed."""
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table in ("buyers", "farmers"):
            columns = {column["name"] for column in inspector.get_columns(table)}
            if "passwordHash" not in columns:
                connection.execute(text(f'ALTER TABLE {table} ADD COLUMN passwordHash VARCHAR(255)'))


ensure_auth_columns()

app = FastAPI(title="Farm Produce Marketplace API", version="1.0.0")
upload_dir = Path(os.getenv("UPLOAD_DIR", Path(__file__).resolve().parent / "uploads"))
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"success": False, "message": str(exc.detail), "error": "HTTP_ERROR"}
    return JSONResponse(status_code=exc.status_code, content=detail)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "message": "Validation error",
            "error": "VALIDATION_ERROR",
            "details": exc.errors(),
        },
    )


@app.get("/")
def root():
    return as_success("Farm Produce Marketplace API is running", {"name": "Farm Produce Marketplace"})


@app.post("/uploads/image")
def upload_image(request: Request, payload: ImageUpload):
    try:
        header, encoded = payload.dataUrl.split(",", 1)
        mime_type = header.split(";", 1)[0].removeprefix("data:")
        if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise ValueError
        image_bytes = base64.b64decode(encoded, validate=True)
    except (ValueError, UnicodeError, base64.binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="Upload a valid JPG, PNG, or WebP image") from exc
    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Images must be 5 MB or smaller")
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[mime_type]
    filename = f"{uuid.uuid4().hex}.{extension}"
    (upload_dir / filename).write_bytes(image_bytes)
    image_url = f"{str(request.base_url).rstrip('/')}/uploads/{filename}"
    return as_success("Image uploaded successfully", {"imageUrl": image_url})


def auth_user(user, role: str):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "location": user.location,
        "role": role,
        **({"farmName": user.farmName, "description": user.description} if role == "seller" else {}),
    }


@app.post("/auth/register/buyer", status_code=status.HTTP_201_CREATED)
def register_buyer(payload: BuyerRegistration, db: Session = Depends(get_db)):
    existing = db.query(Buyer).filter(Buyer.email.ilike(payload.email)).first()
    if existing and existing.passwordHash:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"success": False, "message": "An account with this email already exists", "error": "EMAIL_ALREADY_EXISTS"})
    buyer = existing or Buyer(id=__import__("uuid").uuid4().hex)
    buyer.name = payload.name
    buyer.phone = payload.phone
    buyer.email = payload.email
    buyer.location = payload.location
    buyer.passwordHash = hash_password(payload.password)
    if not existing:
        db.add(buyer)
    db.commit()
    db.refresh(buyer)
    user = auth_user(buyer, "buyer")
    return as_success("Buyer account created successfully", {"accessToken": create_token(buyer.id, "buyer"), "user": user})


@app.post("/auth/register/seller", status_code=status.HTTP_201_CREATED)
def register_seller(payload: SellerRegistration, db: Session = Depends(get_db)):
    existing = db.query(Farmer).filter(Farmer.email.ilike(payload.email)).first()
    if existing and existing.passwordHash:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"success": False, "message": "An account with this email already exists", "error": "EMAIL_ALREADY_EXISTS"})
    farmer = existing or Farmer(id=__import__("uuid").uuid4().hex)
    farmer.name = payload.name
    farmer.phone = payload.phone
    farmer.email = payload.email
    farmer.location = payload.location
    farmer.farmName = payload.farmName
    farmer.description = payload.description
    farmer.passwordHash = hash_password(payload.password)
    if not existing:
        db.add(farmer)
    db.commit()
    db.refresh(farmer)
    user = auth_user(farmer, "seller")
    return as_success("Seller account created successfully", {"accessToken": create_token(farmer.id, "seller"), "user": user})


@app.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    role = "seller" if payload.role == "seller" else "buyer"
    model = Farmer if role == "seller" else Buyer
    user = db.query(model).filter(model.email.ilike(payload.email)).first()
    if not user or not verify_password(payload.password, user.passwordHash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"success": False, "message": "Incorrect email, password, or account type", "error": "INVALID_CREDENTIALS"})
    return as_success("Login successful", {"accessToken": create_token(user.id, role), "user": auth_user(user, role)})


@app.post("/farmers", status_code=status.HTTP_201_CREATED)
def create_farmer_route(payload: FarmerCreate, db: Session = Depends(get_db)):
    farmer = create_farmer(db, payload.model_dump())
    return as_success("Farmer created successfully", serialize_farmer(farmer))


@app.get("/farmers")
def list_farmers_route(db: Session = Depends(get_db)):
    farmers = list_farmers(db)
    return as_success("Farmers retrieved successfully", [serialize_farmer(f) for f in farmers])


@app.get("/farmers/{farmer_id}")
def get_farmer_route(farmer_id: str, db: Session = Depends(get_db)):
    farmer = get_farmer(db, farmer_id)
    return as_success("Farmer retrieved successfully", serialize_farmer(farmer))


@app.put("/farmers/{farmer_id}")
def update_farmer_route(farmer_id: str, payload: FarmerUpdate, db: Session = Depends(get_db)):
    farmer = update_farmer(db, farmer_id, payload.model_dump(exclude_unset=True))
    return as_success("Farmer updated successfully", serialize_farmer(farmer))


@app.patch("/farmers/{farmer_id}")
def patch_farmer_route(farmer_id: str, payload: FarmerUpdate, db: Session = Depends(get_db)):
    farmer = update_farmer(db, farmer_id, payload.model_dump(exclude_unset=True))
    return as_success("Farmer updated successfully", serialize_farmer(farmer))


@app.delete("/farmers/{farmer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farmer_route(farmer_id: str, db: Session = Depends(get_db)):
    delete_farmer(db, farmer_id)
    return None


@app.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category_route(payload: CategoryCreate, db: Session = Depends(get_db)):
    category = create_category(db, payload.model_dump())
    return as_success("Category created successfully", serialize_category(category))


@app.get("/categories")
def list_categories_route(db: Session = Depends(get_db)):
    categories = list_categories(db)
    return as_success("Categories retrieved successfully", [serialize_category(c) for c in categories])


@app.get("/categories/{category_id}")
def get_category_route(category_id: str, db: Session = Depends(get_db)):
    category = get_category(db, category_id)
    return as_success("Category retrieved successfully", serialize_category(category))


@app.put("/categories/{category_id}")
def update_category_route(category_id: str, payload: CategoryUpdate, db: Session = Depends(get_db)):
    category = update_category(db, category_id, payload.model_dump(exclude_unset=True))
    return as_success("Category updated successfully", serialize_category(category))


@app.patch("/categories/{category_id}")
def patch_category_route(category_id: str, payload: CategoryUpdate, db: Session = Depends(get_db)):
    category = update_category(db, category_id, payload.model_dump(exclude_unset=True))
    return as_success("Category updated successfully", serialize_category(category))


@app.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category_route(category_id: str, db: Session = Depends(get_db)):
    delete_category(db, category_id)
    return None


@app.post("/products", status_code=status.HTTP_201_CREATED)
def create_product_route(payload: ProductCreate, db: Session = Depends(get_db)):
    product = create_product(db, payload.model_dump())
    return as_success("Product created successfully", serialize_product(product))


@app.get("/products")
def list_products_route(
    db: Session = Depends(get_db),
    category: str | None = Query(default=None),
    farmer: str | None = Query(default=None),
    location: str | None = Query(default=None),
    minPrice: float | None = Query(default=None),
    maxPrice: float | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    sortBy: str = Query(default="createdAt"),
    order: str = Query(default="desc"),
):
    products, pagination = list_products(
        db,
        category=category,
        farmer=farmer,
        location=location,
        min_price=minPrice,
        max_price=maxPrice,
        status=status,
        search=search,
        page=page,
        limit=limit,
        sort_by=sortBy,
        order=order,
    )
    response = as_success("Products retrieved successfully", [serialize_product(p) for p in products])
    response["pagination"] = pagination
    return response


@app.get("/products/{product_id}")
def get_product_route(product_id: str, db: Session = Depends(get_db)):
    product = get_product(db, product_id)
    return as_success("Product retrieved successfully", serialize_product(product))


@app.put("/products/{product_id}")
def update_product_route(product_id: str, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = update_product(db, product_id, payload.model_dump(exclude_unset=True))
    return as_success("Product updated successfully", serialize_product(product))


@app.patch("/products/{product_id}")
def patch_product_route(product_id: str, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = update_product(db, product_id, payload.model_dump(exclude_unset=True))
    return as_success("Product updated successfully", serialize_product(product))


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_route(product_id: str, db: Session = Depends(get_db)):
    delete_product(db, product_id)
    return None


@app.get("/farmers/{farmer_id}/products")
def farmers_products_route(farmer_id: str, db: Session = Depends(get_db)):
    products = list_farmer_products(db, farmer_id)
    return as_success("Farmer products retrieved successfully", [serialize_product(p) for p in products])


@app.post("/products/{product_id}/stock/increase")
def increase_stock_route(product_id: str, payload: ProductStockAdjust, db: Session = Depends(get_db)):
    product = adjust_stock(db, product_id, payload.amount, "increase")
    return as_success("Stock increased successfully", serialize_product(product))


@app.post("/products/{product_id}/stock/decrease")
def decrease_stock_route(product_id: str, payload: ProductStockAdjust, db: Session = Depends(get_db)):
    product = adjust_stock(db, product_id, payload.amount, "decrease")
    return as_success("Stock decreased successfully", serialize_product(product))


@app.get("/products/{product_id}/stock")
def product_stock_route(product_id: str, db: Session = Depends(get_db)):
    product = get_stock(db, product_id)
    return as_success("Stock retrieved successfully", {"productId": product.id, "quantityAvailable": product.quantityAvailable, "status": product.status})


@app.post("/buyers", status_code=status.HTTP_201_CREATED)
def create_buyer_route(payload: BuyerCreate, db: Session = Depends(get_db)):
    buyer = create_buyer(db, payload.model_dump())
    return as_success("Buyer created successfully", serialize_buyer(buyer))


@app.get("/buyers")
def list_buyers_route(db: Session = Depends(get_db)):
    buyers = list_buyers(db)
    return as_success("Buyers retrieved successfully", [serialize_buyer(b) for b in buyers])


@app.get("/buyers/{buyer_id}")
def get_buyer_route(buyer_id: str, db: Session = Depends(get_db)):
    buyer = get_buyer(db, buyer_id)
    return as_success("Buyer retrieved successfully", serialize_buyer(buyer))


@app.put("/buyers/{buyer_id}")
def update_buyer_route(buyer_id: str, payload: BuyerUpdate, db: Session = Depends(get_db)):
    buyer = update_buyer(db, buyer_id, payload.model_dump(exclude_unset=True))
    return as_success("Buyer updated successfully", serialize_buyer(buyer))


@app.patch("/buyers/{buyer_id}")
def patch_buyer_route(buyer_id: str, payload: BuyerUpdate, db: Session = Depends(get_db)):
    buyer = update_buyer(db, buyer_id, payload.model_dump(exclude_unset=True))
    return as_success("Buyer updated successfully", serialize_buyer(buyer))


@app.delete("/buyers/{buyer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_buyer_route(buyer_id: str, db: Session = Depends(get_db)):
    delete_buyer(db, buyer_id)
    return None


@app.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order_route(payload: OrderCreate, db: Session = Depends(get_db)):
    order = create_order(db, payload.model_dump())
    return as_success("Order created successfully", serialize_order(order))


@app.get("/orders")
def list_orders_route(db: Session = Depends(get_db)):
    orders = list_orders(db)
    return as_success("Orders retrieved successfully", [serialize_order(o) for o in orders])


@app.get("/orders/{order_id}")
def get_order_route(order_id: str, db: Session = Depends(get_db)):
    order = get_order(db, order_id)
    return as_success("Order retrieved successfully", serialize_order(order))


@app.get("/buyers/{buyer_id}/orders")
def buyer_orders_route(buyer_id: str, db: Session = Depends(get_db)):
    orders = list_buyer_orders(db, buyer_id)
    return as_success("Buyer orders retrieved successfully", [serialize_order(order) for order in orders])


@app.get("/farmers/{farmer_id}/orders")
def farmer_orders_route(farmer_id: str, db: Session = Depends(get_db)):
    orders = list_farmer_orders(db, farmer_id)
    return as_success("Farmer orders retrieved successfully", [serialize_order(order) for order in orders])


@app.patch("/orders/{order_id}/status")
def update_order_status_route(order_id: str, payload: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = update_order_status(db, order_id, payload.status)
    return as_success("Order status updated successfully", serialize_order(order))


def serialize_farmer(farmer: Farmer):
    return {
        "id": farmer.id,
        "name": farmer.name,
        "phone": farmer.phone,
        "email": farmer.email,
        "location": farmer.location,
        "farmName": farmer.farmName,
        "description": farmer.description,
        "createdAt": farmer.createdAt.isoformat(),
        "updatedAt": farmer.updatedAt.isoformat(),
    }


def serialize_category(category: Category):
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "createdAt": category.createdAt.isoformat(),
        "updatedAt": category.updatedAt.isoformat(),
    }


def serialize_product(product: Product):
    return {
        "id": product.id,
        "farmerId": product.farmerId,
        "categoryId": product.categoryId,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "unit": product.unit,
        "quantityAvailable": product.quantityAvailable,
        "location": product.location,
        "imageUrl": product.imageUrl,
        "farmerName": product.farmer.name if product.farmer else None,
        "farmName": product.farmer.farmName if product.farmer else None,
        "categoryName": product.category.name if product.category else None,
        "status": product.status,
        "createdAt": product.createdAt.isoformat(),
        "updatedAt": product.updatedAt.isoformat(),
    }


def serialize_buyer(buyer: Buyer):
    return {
        "id": buyer.id,
        "name": buyer.name,
        "phone": buyer.phone,
        "email": buyer.email,
        "location": buyer.location,
        "createdAt": buyer.createdAt.isoformat(),
        "updatedAt": buyer.updatedAt.isoformat(),
    }


def serialize_order_item(item):
    return {
        "id": item.id,
        "orderId": item.orderId,
        "productId": item.productId,
        "quantity": item.quantity,
        "unitPrice": item.unitPrice,
        "subtotal": item.subtotal,
        "productName": item.product.name if item.product else None,
        "productImageUrl": item.product.imageUrl if item.product else None,
        "unit": item.product.unit if item.product else None,
    }


def serialize_order(order: Order):
    return {
        "id": order.id,
        "buyerId": order.buyerId,
        "totalAmount": order.totalAmount,
        "status": order.status,
        "deliveryLocation": order.deliveryLocation,
        "createdAt": order.createdAt.isoformat(),
        "updatedAt": order.updatedAt.isoformat(),
        "items": [serialize_order_item(item) for item in order.items],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

