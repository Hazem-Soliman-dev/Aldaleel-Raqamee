# Product Inventory & Stock Reservation REST API

A complete, production-ready Django REST Framework backend project for managing product inventory, reserving stock on order creation, and safely releasing reserved stock upon cancellation under high concurrency.

Built with ACID transactional guarantees, row-level locking (`select_for_update`), and conflict management (HTTP `409`) to prevent negative stock and double releases.

---

## 🌐 Interactive Browser Testing Guide (For Reviewers)

To make reviewing as human-friendly and intuitive as possible, every endpoint in this project can be tested directly inside your web browser via **Django REST Framework's Interactive Browsable API** and the **Django Admin Dashboard**.

### Quick Start
1. Start the local server:
   ```bash
   python manage.py runserver
   ```
2. Open your browser to: **`http://127.0.0.1:8000/api/`**

---

### 1. Visual Review URLs Directory

| Screen | Browser URL | What to Test in Browser |
|---|---|---|
| **API Root** | `http://127.0.0.1:8000/api/` | Clickable directory linking to Products & Orders |
| **Products List & Create** | `http://127.0.0.1:8000/api/products/` | Browse catalog, search (`?search=`), filter (`?is_active=`), or create items via bottom form |
| **Product Detail & Actions** | `http://127.0.0.1:8000/api/products/1/` | Edit prices/stock via bottom form, or click red **DELETE** button to test soft-deletion |
| **Orders List & Reserve** | `http://127.0.0.1:8000/api/orders/` | View orders, or paste JSON in the **Raw data** tab to reserve stock atomically |
| **Order Cancellation** | `http://127.0.0.1:8000/api/orders/1/cancel/` | Click **POST** button to cancel order and restore stock |
| **Django Admin Dashboard** | `http://127.0.0.1:8000/admin/` | Visual GUI table with inline order items (Login: `admin` / `admin123`) |

---

### 2. Step-by-Step Browser Testing Scenarios

#### Scenario A: Create a Product via HTML Form
1. Open `http://127.0.0.1:8000/api/products/`
2. Scroll to the HTML form at the bottom of the page.
3. Enter:
   - **Name:** `Gaming Mousepad XXL`
   - **SKU:** `PAD-XXL-001`
   - **Price:** `29.99`
   - **Stock quantity:** `15`
4. Click **POST** $	o$ You will see `HTTP 201 Created` with the new product rendered.

#### Scenario B: Reserve Stock by Creating an Order
1. Open `http://127.0.0.1:8000/api/orders/`
2. Scroll down and click the **Raw data** tab.
3. Paste the following JSON:
   ```json
   {
     "customer_name": "Reviewer Alice",
     "items": [
       { "product_id": 1, "quantity": 2 }
     ]
   }
   ```
4. Click **POST** $	o$ You will receive `HTTP 201 Created`.
5. Open `http://127.0.0.1:8000/api/products/1/` in another tab $	o$ Notice `stock_quantity` decreased by 2!

#### Scenario C: Test Insufficient Stock Rejection (HTTP 409 Conflict)
1. On `http://127.0.0.1:8000/api/orders/`, in the **Raw data** tab, enter quantity `9999`:
   ```json
   {
     "customer_name": "Over-limit Buyer",
     "items": [
       { "product_id": 1, "quantity": 9999 }
     ]
   }
   ```
2. Click **POST** $	o$ The browser displays `HTTP 409 Conflict` with a clear explanation:
   ```json
   { "detail": "Insufficient stock for product 'MBP-M3-16' (ID: 1). Requested: 9999, Available: 12." }
   ```
3. Zero partial stock was deducted (atomic rollback).

#### Scenario D: Cancel an Order & Release Stock
1. Open `http://127.0.0.1:8000/api/orders/1/cancel/`
2. Click the **POST** button $	o$ Status changes to `HTTP 200 OK`, `status` becomes `"CANCELLED"`, and `cancelled_at` timestamp is set.
3. Check `http://127.0.0.1:8000/api/products/1/` $	o$ The stock is restored back to the product!
4. **Test Double-Release Protection**: Click the **POST** button again on the cancel page $	o$ Browser returns `HTTP 409 Conflict` ("Only orders in 'PENDING' status can be cancelled.").

#### Scenario E: Django Admin Site
1. Open `http://127.0.0.1:8000/admin/`
2. Log in with:
   - **Username:** `admin`
   - **Password:** `admin123`
3. Click **Products** to see all items with inline editable stock and price columns.
4. Click **Orders** to see all customer orders and their line items inline.

---

## 🌟 Key Architecture & Features

- **Product Management (US-001)**: Full CRUD API with validation (`price > 0`, `stock_quantity >= 0`, unique `sku`), soft deletion (`is_active=False`), search, and filtering.
- **Atomic Stock Reservation (US-002)**: Multi-item order creation with row locking (`select_for_update()`) inside an atomic transaction. If any item has insufficient stock, the transaction rolls back cleanly with **zero partial reservation**.
- **Safe Stock Release (US-003)**: Idempotent cancellation endpoint (`POST /api/orders/{id}/cancel/`) that restores reserved product quantities and locks the order status. Rejects invalid transitions or double cancellations with `409 Conflict`.
- **Concurrency & Deadlock Safety**: Deterministic sorted lock acquisition on products prevents database deadlocks. Tested under concurrent load.
- **Dual Database Architecture**: Defaults to **SQLite** for zero-friction local development, and switches automatically to **PostgreSQL 16** via Docker Compose or `DATABASE_URL`.
- **Database Backup & Seed Fixture**: Pre-populated sample data fixture (`backup.json`) with sample products and orders.

---

## 🏗️ Tech Stack

- **Framework**: Django 5.2 + Django REST Framework 3.18
- **Language**: Python 3.11+ / 3.12 / 3.14
- **Database**: SQLite (local fallback) / PostgreSQL 16 (production & Docker)
- **Filtering & Search**: `django-filter` + DRF Search & Ordering filters
- **Testing**: Django Test Framework + `pytest-django` + multi-threaded concurrency test suite
- **Containerization**: Docker + Docker Compose

---

## 🚀 Setup & Execution Guide

### Option 1: Local Development (SQLite - Zero External Dependencies)

1. **Navigate to the project directory:**
   ```bash
   cd Aldaleel-Raqamee
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv

   # On Windows (PowerShell):
   .venv\Scripts\Activate.ps1

   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment variables:**
   ```bash
   cp .env.example .env
   ```

5. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

6. **(Optional) Load sample seed data:**
   ```bash
   python manage.py loaddata backup.json
   ```

7. **Start the development server:**
   ```bash
   python manage.py runserver
   ```
   - **Interactive API Browser**: `http://127.0.0.1:8000/api/`
   - **Django Admin UI**: `http://127.0.0.1:8000/admin/` (Login: `admin` / `admin123`)

---

### Option 2: Docker Compose (PostgreSQL 16 - One-Command Setup)

1. **Build and start services:**
   ```bash
   docker-compose up --build
   ```
   This automatically starts PostgreSQL 16, runs database migrations, and exposes the Django app on port 8000.

2. **(Optional) Load fixture inside Docker container:**
   ```bash
   docker-compose exec web python manage.py loaddata backup.json
   ```

3. **Stop containers:**
   ```bash
   docker-compose down
   ```

---

## 🧪 Running Automated Tests

### Run with Django test runner:
```bash
python manage.py test --no-input
```

### Run with pytest:
```bash
python -m pytest -v
```

### Run concurrency tests:
```bash
python manage.py test orders.tests.test_concurrency
```

---

## 💾 Database Fixture & Backup

A cross-database JSON fixture is committed at `backup.json` containing sample products and orders.

- **Load backup data:**
  ```bash
  python manage.py loaddata backup.json
  ```
- **Export latest database data:**
  ```bash
  python manage.py dumpdata products orders --indent 2 > backup.json
  ```

---

## 📋 API Endpoints Reference

| Method | Path | Purpose | Status Codes |
|---|---|---|---|
| `GET` | `/api/products/` | List products (paginated, search & filter) | `200 OK` |
| `POST` | `/api/products/` | Create product | `201 Created`, `400 Bad Request` |
| `GET` | `/api/products/{id}/` | Retrieve product | `200 OK`, `404 Not Found` |
| `PUT/PATCH` | `/api/products/{id}/` | Update product | `200 OK`, `400 Bad Request`, `404 Not Found` |
| `DELETE` | `/api/products/{id}/` | Soft-delete product (`is_active=False`) | `204 No Content`, `404 Not Found` |
| `POST` | `/api/orders/` | Create order & reserve stock atomically | `201 Created`, `400 Bad Request`, `409 Conflict` |
| `GET` | `/api/orders/` | List orders (paginated, filter by status) | `200 OK` |
| `GET` | `/api/orders/{id}/` | Retrieve order + items + total | `200 OK`, `404 Not Found` |
| `POST` | `/api/orders/{id}/cancel/` | Cancel order & restore stock | `200 OK`, `404 Not Found`, `409 Conflict` |

---

## 📌 Assumptions & Decisions

1. **Assumption A (Authentication & Authorization Scope)**:
   - No authentication or permission system is enforced on API endpoints. The user stories reference "admin" (managing products) and "customer" (creating orders) as functional roles for narrative clarity rather than an enforced authentication layer. Endpoints are open for transparent evaluation and automated testing.
   - The built-in Django Admin (`/admin/`) is fully registered and available for administrative inspection with pre-configured credentials (`admin` / `admin123`).

2. **Assumption B (Stock Reservation Model)**:
   - Stock reservation directly decrements `Product.stock_quantity` upon order creation (`PENDING`).
   - Order cancellation restores `Product.stock_quantity` by adding back the reserved quantity.
   - No secondary "reserved" counter column is used (matching TASK-003), keeping stock calculations clean and deterministic.

3. **Concurrency & Locking Strategy**:
   - `select_for_update()` row locking is used within `transaction.atomic()`.
   - Product IDs are sorted before locking (`sorted_product_ids = sorted(keys)`) to guarantee a deterministic lock acquisition order and prevent deadlocks across multi-item orders.

4. **HTTP Status Code Standardization**:
   - `201 Created` for product and order creation.
   - `200 OK` for reads, updates, and order cancellation.
   - `400 Bad Request` for schema/field validation errors (e.g. price <= 0, empty items list, zero quantity).
   - `404 Not Found` for missing product or order IDs.
   - `409 Conflict` for business rule rejections: insufficient stock (TASK-009, TASK-011) or invalid order state transitions such as cancelling an already-cancelled order (TASK-014, TASK-015).
   - `204 No Content` for soft-deleting products.

5. **Bonus Items Completed**:
   - PostgreSQL via Docker Compose: Fully wired with healthcheck and automatic migrations on startup.
   - Database Backup Fixture: Committed `backup.json` containing sample products and orders across multiple categories.
   - Automated Concurrency Tests: Multi-threaded concurrency test suite verifying zero oversell and idempotency.

---

## 📑 Task Traceability Checklist

- [x] **TASK-001**: Product model (`products/models.py`)
- [x] **TASK-002**: CRUD endpoints (`products/views.py`)
- [x] **TASK-003**: Stock quantity field (`products/models.py`)
- [x] **TASK-004**: Validation (`products/models.py` & `products/serializers.py`)
- [x] **TASK-005**: Pagination & filtering (`common/pagination.py` & `products/views.py`)
- [x] **TASK-005/006**: Create order + order items (`orders/services.py` & `orders/models.py`)
- [x] **TASK-007**: Validate stock (`orders/services.py`)
- [x] **TASK-008**: Reserve stock (`orders/services.py`)
- [x] **TASK-009**: Prevent negative stock (`orders/services.py`)
- [x] **TASK-010**: Handle concurrent requests (`orders/services.py` with select_for_update & atomic transaction)
- [x] **TASK-011**: Rollback failed operations (`orders/services.py` atomic rollback on insufficient stock)
- [x] **TASK-012**: Implement cancellation (`orders/views.py` & `orders/services.py`)
- [x] **TASK-013**: Restore stock (`orders/services.py`)
- [x] **TASK-014**: Prevent double release (`orders/services.py` status check and row locking)
- [x] **TASK-015**: Handle invalid state transitions (`orders/services.py` returning 409 Conflict)

---

## 📁 Project Structure

```
Aldaleel-Raqamee/
├── config/                # Django project configuration (settings, urls, wsgi, asgi)
├── common/                # Shared utilities, custom exceptions (409 Conflict), pagination
├── products/              # Product model, serializers, views, admin, tests
├── orders/                # Order, OrderItem, atomic reservation/cancellation service, tests
├── backup.json            # Seed database fixture
├── Dockerfile             # Production Python 3.12 Dockerfile
├── docker-compose.yml     # Multi-container Postgres 16 + Web orchestration
├── docker-entrypoint.sh   # Container bootstrap with auto-migration
├── requirements.txt       # Python dependencies
├── pytest.ini             # Pytest configuration
├── .env.example           # Environment template
├── .env                   # Local configuration
├── .gitignore
└── README.md
```
