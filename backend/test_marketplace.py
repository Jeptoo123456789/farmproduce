from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def reset_db():
    from backend.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_create_farmer():
    reset_db()
    payload = {
        "name": "Alice Mwangi",
        "phone": "+254700000001",
        "email": "alice@example.com",
        "location": "Eldoret",
        "farmName": "Green Valley Farm",
        "description": "Vegetable producer"
    }
    response = client.post("/farmers", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["name"] == "Alice Mwangi"
    assert body["data"]["farmName"] == "Green Valley Farm"


def test_create_category_and_product_and_filter():
    reset_db()
    category = client.post("/categories", json={"name": "Vegetables", "description": "Fresh vegetables"})
    assert category.status_code == 201

    farmer = client.post("/farmers", json={
        "name": "John Njoroge",
        "phone": "+254700000002",
        "email": "john@example.com",
        "location": "Nakuru",
        "farmName": "Sunrise Farm",
        "description": "Fruit and veg"
    })
    farmer_id = farmer.json()["data"]["id"]
    category_id = category.json()["data"]["id"]

    product = client.post("/products", json={
        "farmerId": farmer_id,
        "categoryId": category_id,
        "name": "Tomatoes",
        "description": "Fresh tomatoes",
        "price": 120,
        "unit": "kg",
        "quantityAvailable": 50,
        "location": "Nakuru",
        "status": "AVAILABLE"
    })
    assert product.status_code == 201
    product_id = product.json()["data"]["id"]

    filtered = client.get("/products?search=tomato&category=vegetables&location=Nakuru&status=AVAILABLE&page=1&limit=10")
    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["success"] is True
    assert payload["pagination"]["total"] >= 1
    assert any(item["id"] == product_id for item in payload["data"])
    item = next(item for item in payload["data"] if item["id"] == product_id)
    assert item["categoryName"] == "Vegetables"
    assert item["farmerName"] == "John Njoroge"
    assert item["quantityAvailable"] == 50
    assert item["price"] == 120


def test_stock_updates_and_cannot_go_negative():
    reset_db()
    category = client.post("/categories", json={"name": "Cereals", "description": "Cereals"})
    farmer = client.post("/farmers", json={
        "name": "Farmer Two",
        "phone": "+254700000003",
        "email": "farmer2@example.com",
        "location": "Eldoret",
        "farmName": "Golden Acres",
        "description": "" 
    })
    product = client.post("/products", json={
        "farmerId": farmer.json()["data"]["id"],
        "categoryId": category.json()["data"]["id"],
        "name": "Maize",
        "description": "Dry maize",
        "price": 75,
        "unit": "kg",
        "quantityAvailable": 10,
        "location": "Eldoret",
        "status": "AVAILABLE"
    })
    product_id = product.json()["data"]["id"]

    inc = client.post(f"/products/{product_id}/stock/increase", json={"amount": 5})
    assert inc.status_code == 200
    assert inc.json()["data"]["quantityAvailable"] == 15

    dec = client.post(f"/products/{product_id}/stock/decrease", json={"amount": 20})
    assert dec.status_code == 200
    assert dec.json()["data"]["quantityAvailable"] == 0
    assert dec.json()["data"]["status"] == "OUT_OF_STOCK"

    negative = client.post(f"/products/{product_id}/stock/decrease", json={"amount": 1})
    assert negative.status_code == 400
    assert negative.json()["success"] is False


def test_order_creation_with_stock_reduction_and_history():
    reset_db()
    category = client.post("/categories", json={"name": "Fruits", "description": "Fresh fruits"})
    farmer = client.post("/farmers", json={
        "name": "Farmer Three",
        "phone": "+254700000004",
        "email": "farmer3@example.com",
        "location": "Kisumu",
        "farmName": "Riverbank Farm",
        "description": "Fruit farm"
    })
    buyer = client.post("/buyers", json={
        "name": "Buyer One",
        "phone": "+254700000005",
        "email": "buyer@example.com",
        "location": "Kisumu"
    })
    farmer_id = farmer.json()["data"]["id"]
    category_id = category.json()["data"]["id"]
    buyer_id = buyer.json()["data"]["id"]

    product = client.post("/products", json={
        "farmerId": farmer_id,
        "categoryId": category_id,
        "name": "Bananas",
        "description": "Sweet bananas",
        "price": 90,
        "unit": "bunch",
        "quantityAvailable": 12,
        "location": "Kisumu",
        "status": "AVAILABLE"
    })
    product_id = product.json()["data"]["id"]

    order = client.post("/orders", json={
        "buyerId": buyer_id,
        "deliveryLocation": "Kisumu",
        "items": [{"productId": product_id, "quantity": 3}]
    })
    assert order.status_code == 201
    body = order.json()
    assert body["success"] is True
    assert body["data"]["totalAmount"] == 270
    assert body["data"]["items"][0]["unitPrice"] == 90
    assert body["data"]["items"][0]["subtotal"] == 270

    stock = client.get(f"/products/{product_id}/stock")
    assert stock.status_code == 200
    assert stock.json()["data"]["quantityAvailable"] == 9


def test_order_insufficient_stock_and_status_update():
    reset_db()
    category = client.post("/categories", json={"name": "Legumes", "description": "Legumes"})
    farmer = client.post("/farmers", json={
        "name": "Farmer Four",
        "phone": "+254700000006",
        "email": "farmer4@example.com",
        "location": "Kitale",
        "farmName": "Hilltop Farm",
        "description": "Legume farm"
    })
    buyer = client.post("/buyers", json={
        "name": "Buyer Two",
        "phone": "+254700000007",
        "email": "buyer2@example.com",
        "location": "Kitale"
    })
    product = client.post("/products", json={
        "farmerId": farmer.json()["data"]["id"],
        "categoryId": category.json()["data"]["id"],
        "name": "Beans",
        "description": "Dried beans",
        "price": 50,
        "unit": "kg",
        "quantityAvailable": 2,
        "location": "Kitale",
        "status": "AVAILABLE"
    })
    order = client.post("/orders", json={
        "buyerId": buyer.json()["data"]["id"],
        "deliveryLocation": "Kitale",
        "items": [{"productId": product.json()["data"]["id"], "quantity": 3}]
    })
    assert order.status_code == 400
    assert order.json()["success"] is False

    created = client.post("/orders", json={
        "buyerId": buyer.json()["data"]["id"],
        "deliveryLocation": "Kitale",
        "items": [{"productId": product.json()["data"]["id"], "quantity": 2}]
    })
    assert created.status_code == 201
    order_id = created.json()["data"]["id"]

    update = client.patch(f"/orders/{order_id}/status", json={"status": "READY"})
    assert update.status_code == 200
    assert update.json()["data"]["status"] == "READY"


def test_farmer_and_buyer_order_lists():
    reset_db()
    category = client.post("/categories", json={"name": "Dairy", "description": "Dairy"})
    farmer = client.post("/farmers", json={
        "name": "Farm Owner",
        "phone": "+254700000008",
        "email": "owner@example.com",
        "location": "Mombasa",
        "farmName": "Coastal Farm",
        "description": "Milk and dairy"
    })
    buyer = client.post("/buyers", json={
        "name": "Buyer Three",
        "phone": "+254700000009",
        "email": "buyer3@example.com",
        "location": "Mombasa"
    })
    product = client.post("/products", json={
        "farmerId": farmer.json()["data"]["id"],
        "categoryId": category.json()["data"]["id"],
        "name": "Milk",
        "description": "Fresh milk",
        "price": 60,
        "unit": "litre",
        "quantityAvailable": 30,
        "location": "Mombasa",
        "status": "AVAILABLE"
    })
    order = client.post("/orders", json={
        "buyerId": buyer.json()["data"]["id"],
        "deliveryLocation": "Mombasa",
        "items": [{"productId": product.json()["data"]["id"], "quantity": 5}]
    })
    assert order.status_code == 201

    buyer_orders = client.get(f"/buyers/{buyer.json()['data']['id']}/orders")
    farmer_orders = client.get(f"/farmers/{farmer.json()['data']['id']}/orders")
    assert buyer_orders.status_code == 200
    assert farmer_orders.status_code == 200
    assert buyer_orders.json()["data"][0]["buyerId"] == buyer.json()["data"]["id"]
    assert farmer_orders.json()["data"][0]["buyerId"] == buyer.json()["data"]["id"]
    assert buyer_orders.json()["data"][0]["items"][0]["productName"] == "Milk"


def test_missing_resources_and_validation():
    reset_db()
    response = client.get("/farmers/non-existent-id")
    assert response.status_code == 404
    assert response.json()["success"] is False

    bad_product = client.post("/products", json={
        "farmerId": "bad-id",
        "categoryId": "bad-id",
        "name": "Bad item",
        "description": "bad",
        "price": -1,
        "unit": "kg",
        "quantityAvailable": -2,
        "location": "Nairobi",
        "status": "AVAILABLE"
    })
    assert bad_product.status_code == 400
    assert bad_product.json()["success"] is False


def test_buyer_registration_and_login():
    reset_db()
    registered = client.post("/auth/register/buyer", json={
        "name": "Buyer Auth",
        "phone": "+254700000010",
        "email": "authbuyer@example.com",
        "location": "Nairobi",
        "password": "buyer-password",
    })
    assert registered.status_code == 201
    assert registered.json()["data"]["user"]["role"] == "buyer"
    assert registered.json()["data"]["accessToken"]

    logged_in = client.post("/auth/login", json={
        "email": "authbuyer@example.com",
        "password": "buyer-password",
        "role": "buyer",
    })
    assert logged_in.status_code == 200
    assert logged_in.json()["data"]["user"]["email"] == "authbuyer@example.com"


def test_seller_registration_and_role_is_required_for_login():
    reset_db()
    registered = client.post("/auth/register/seller", json={
        "name": "Seller Auth",
        "phone": "+254700000011",
        "email": "authseller@example.com",
        "location": "Eldoret",
        "farmName": "Auth Farm",
        "description": "Fresh produce",
        "password": "seller-password",
    })
    assert registered.status_code == 201
    assert registered.json()["data"]["user"]["role"] == "seller"

    wrong_role = client.post("/auth/login", json={
        "email": "authseller@example.com",
        "password": "seller-password",
        "role": "buyer",
    })
    assert wrong_role.status_code == 401

    logged_in = client.post("/auth/login", json={
        "email": "authseller@example.com",
        "password": "seller-password",
        "role": "seller",
    })
    assert logged_in.status_code == 200
    assert logged_in.json()["data"]["user"]["farmName"] == "Auth Farm"


def test_existing_profile_can_claim_login_account():
    reset_db()
    existing = client.post("/buyers", json={
        "name": "Legacy Buyer",
        "phone": "+254700000012",
        "email": "legacy@example.com",
        "location": "Nakuru",
    })
    assert existing.status_code == 201

    claimed = client.post("/auth/register/buyer", json={
        "name": "Legacy Buyer",
        "phone": "+254700000012",
        "email": "LEGACY@example.com",
        "location": "Nakuru",
        "password": "legacy-password",
    })
    assert claimed.status_code == 201

    logged_in = client.post("/auth/login", json={
        "email": "legacy@example.com",
        "password": "legacy-password",
        "role": "buyer",
    })
    assert logged_in.status_code == 200
