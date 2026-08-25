# Product Inventory & Stock Reservation REST API

A complete, production-ready Django REST Framework backend project for managing product inventory, reserving stock on order creation, and safely releasing reserved stock upon cancellation under high concurrency.

Built with ACID transactional guarantees, row-level locking (`select_for_update`), and conflict management (HTTP `409`) to prevent negative stock and double releases.

---

## Key Features

- **Product Management (US-001)**: Full CRUD API with validation (`price > 0`, `stock_quantity >= 0`, unique `sku`), soft deletion (`is_active=False`), search, and filtering.
- **Atomic Stock Reservation (US-002)**: Multi-item order creation with row locking (`select_for_update()`) inside an atomic transaction. If any item has insufficient stock, the transaction rolls back cleanly with **zero partial reservation**.
- **Safe Stock Release (US-003)**: Idempotent cancellation endpoint (`POST /api/orders/{id}/cancel/`) that restores reserved product quantities and locks the order status. Rejects invalid transitions or double cancellations with `409 Conflict`.
- **Concurrency & Deadlock Safety**: Deterministic sorted lock acquisition on products prevents database deadlocks. Tested under concurrent load.
- **Dual Database Architecture**: Defaults to **SQLite** for zero-friction local development, and switches automatically to **PostgreSQL 16** via Docker Compose or `DATABASE_URL`.
- **Django Admin UI**: Integrated administrative interface at `/admin/` with inline order items, search, and status filters.
- **Interactive Browsable API**: DRF interactive web UI for testing every endpoint directly in the browser with HTML forms.
- **Database Backup & Seed Fixture**: Pre-populated sample data fixture (`backup.json`) with sample products and orders.

---

## Tech Stack

- **Framework**: Django 5.2 + Django REST Framework 3.18
- **Language**: Python 3.11+ / 3.12 / 3.14
- **Database**: SQLite (local fallback) / PostgreSQL 16 (production & Docker)
- **Filtering & Search**: `django-filter` + DRF Search & Ordering filters
- **Testing**: Django Test Framework + `pytest-django` + multi-threaded concurrency test suite
- **Containerization**: Docker + Docker Compose

---

## Quick Start Guide

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

## Running Automated Tests

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

## Database Fixture & Backup

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

## API Endpoints Reference

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

### Example Requests & Responses

#### 1. Create a Product
**Request (`POST /api/products/`):**
```json
{
  "name": "Wireless Mechanical Keyboard",
  "sku": "KB-WL-001",
  "description": "75% layout RGB mechanical keyboard",
  "price": "129.99",
  "stock_quantity": 20,
  "is_active": true
}
```
**Response (`201 Created`):**
```json
{
  "id": 1,
  "name": "Wireless Mechanical Keyboard",
  "sku": "KB-WL-001",
  "description": "75% layout RGB mechanical keyboard",
  "price": "129.99",
  "stock_quantity": 20,
  "is_active": true,
  "created_at": "2026-08-25T11:30:00Z",
  "updated_at": "2026-08-25T11:30:00Z"
}
```

#### 2. Create Order & Reserve Stock
**Request (`POST /api/orders/`):**
```json
{
  "customer_name": "Alice Johnson",
  "items": [
    { "product_id": 1, "quantity": 2 }
  ]
}
```
**Response (`201 Created`):**
```json
{
  "id": 1,
  "customer_name": "Alice Johnson",
  "status": "PENDING",
  "total_amount": "259.98",
  "items": [
    {
      "id": 1,
      "product_id": 1,
      "product_name": "Wireless Mechanical Keyboard",
      "product_sku": "KB-WL-001",
      "quantity": 2,
      "unit_price": "129.99",
      "line_total": "259.98"
    }
  ],
  "created_at": "2026-08-25T11:35:00Z",
  "updated_at": "2026-08-25T11:35:00Z",
  "cancelled_at": null
}
```

#### 3. Cancel Order & Restore Stock
**Request (`POST /api/orders/1/cancel/`)**
**Response (`200 OK`):**
```json
{
  "id": 1,
  "customer_name": "Alice Johnson",
  "status": "CANCELLED",
  "total_amount": "259.98",
  "items": [
    {
      "id": 1,
      "product_id": 1,
      "product_name": "Wireless Mechanical Keyboard",
      "product_sku": "KB-WL-001",
      "quantity": 2,
      "unit_price": "129.99",
      "line_total": "259.98"
    }
  ],
  "created_at": "2026-08-25T11:35:00Z",
  "updated_at": "2026-08-25T11:40:00Z",
  "cancelled_at": "2026-08-25T11:40:00Z"
}
```

---

## Assumptions & Decisions

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

## Task Traceability Checklist

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

## Project Structure

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
