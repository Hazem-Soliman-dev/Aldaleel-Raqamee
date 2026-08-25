# Product Inventory & Stock Reservation System

A complete, production-ready Django backend for managing product inventory, reserving stock on order creation, and safely releasing reserved stock upon cancellation under high concurrency.

Built with ACID transactional guarantees, row-level locking (`select_for_update`), role-based permissions, and conflict management (HTTP `409`) to prevent negative stock and double releases.

---

## 👥 Demo Accounts (Roles)

The system includes pre-configured accounts for testing both **Admin** and **Customer** roles:

| Role | Username | Password | Permissions & Capabilities |
|---|---|---|---|
| **Admin** | `admin` | `admin123` | **Full access**: Create, edit, delete products, set stock quantities, manage orders, and access the Django Admin site (`/admin/`). |
| **Customer** | `customer` | `customer123` (local) & `hi2000pass` (live) | **Customer access**: Browse/search products, create orders, reserve stock, and cancel their own pending orders. Cannot modify products. |
| **Guest / Anonymous** | *(none)* | *(none)* | **Public access**: Browse the product catalog only. Must log in to place orders. |

---

## 🌐 Quick Start

1. Start the server:
   ```bash
   python manage.py runserver
   ```
2. Open your browser to the storefront: **`http://127.0.0.1:8000/`** → auto-redirects to **`http://127.0.0.1:8000/shop/`**
3. Use the **Log in** button in the top-right navbar to sign in with a demo account.

---

## 🖥️ Two Primary Interfaces

### 1. Visual Storefront — `/shop/`

The main customer-facing interface served at `/shop/` (also reachable from the root `/`).

| Screen | URL | What You Can Do |
|---|---|---|
| **Root Redirect** | `http://127.0.0.1:8000/` | Automatically redirects to `/shop/` |
| **Storefront** | `http://127.0.0.1:8000/shop/` | Browse products, build a multi-item order cart, place orders, view & cancel your orders |

### 2. Admin Dashboard — `/admin/`

The Django Admin panel for staff management of products, orders, and users.

| Screen | URL | What You Can Do |
|---|---|---|
| **Admin Dashboard** | `http://127.0.0.1:8000/admin/` | Full product CRUD, order list with inline items, approve/reject orders via bulk actions (Login: `admin` / `admin123`) |

---

## 🔄 Step-by-Step Testing Guide

### Scenario A: Browse the Storefront as a Guest

1. Open `http://127.0.0.1:8000/shop/` (no login required).
2. Browse the **Available Products** table on the left — each item shows name, SKU, price, and a real-time stock badge (✅ In Stock / ⚠️ Low Stock / ❌ Out of Stock).
3. Click **"+ Add"** on any product → The page prompts you to **Log in** since guests cannot place orders.

---

### Scenario B: Customer Places an Order & Reserves Stock

1. Click **Log in** (top-right navbar) and sign in with:
   - **Username:** `customer` | **Password:** `customer123`
2. On the **Available Products** table, click **"+ Add"** on one or more products to add them to the **Order Builder** panel on the right.
3. Adjust quantities using the `+` / `−` buttons or type directly. The running total updates in real time.
4. Click **"Reserve Stock & Place Order"** → a spinner appears while the order is processed atomically.
5. On success: a green alert confirms the new **Order #ID**. The page reloads and the order appears in the **Reservations & Orders** list below the cart.
6. Notice the stock badges on the product table have decreased by the reserved quantities.

---

### Scenario C: Insufficient Stock Rejection

1. While logged in as `customer`, click **"+ Add"** on a product repeatedly until the **Order Builder** shows the maximum available stock.
2. Try to increase the quantity beyond the stock limit using the `+` button → The storefront shows an inline warning: *"Cannot reserve more than N units."*
3. If the item goes out of stock between your cart build and submit (e.g., concurrent order), clicking **"Reserve Stock & Place Order"** returns a red alert: *"Reservation Failed: Insufficient stock for product '...' Requested: X, Available: Y."* — zero stock was deducted (atomic rollback).

---

### Scenario D: Cancel an Order & Release Stock

1. In the **Reservations & Orders** list (right panel), find a **PENDING** order belonging to the logged-in customer.
2. Click **"↩ Cancel & Release Stock"** → a confirmation dialog appears.
3. Confirm → the order status badge updates to **CANCELLED** after page reload, and the reserved stock is restored to the product catalog.
4. **Double-Release Protection**: The cancel button disappears for already-cancelled orders. Attempting a programmatic repeat cancel returns a `409 Conflict`.

---

### Scenario E: Admin Approve & Reject Orders (`/admin/`)

#### Via the Storefront (Quick Actions)

1. Log in as `admin` / `admin123` and open `http://127.0.0.1:8000/shop/`.
2. The **Reservations & Orders** panel shows **all customer orders** (admin view).
3. For any **PENDING** order, two action buttons appear:
   - **"✓ Approve Order"** → confirms the reservation; stock remains reserved. Status → `APPROVED`.
   - **"✗ Reject & Release"** → rejects the order and restores reserved stock to catalog. Status → `REJECTED`.

#### Via the Django Admin Panel (Bulk Actions)

1. Open `http://127.0.0.1:8000/admin/orders/order/`.
2. Select one or more PENDING orders using the checkboxes.
3. From the **Action** dropdown, choose:
   - **"Approve selected PENDING orders"**
   - **"Reject selected PENDING orders (releases stock)"**
4. Click **Go** → success/failure messages are shown in the admin toolbar.

---

### Scenario F: Admin Manages Products (`/admin/`)

1. Open `http://127.0.0.1:8000/admin/products/product/`.
2. **Create a product**: Click **"+ Add Product"**, fill in Name, SKU, Price, Stock Quantity, and save.
3. **Edit inline**: The list view allows directly editing `price`, `stock_quantity`, and `is_active` without opening the detail page.
4. **Soft-delete**: Set `is_active = False` to hide a product from the `/shop/` storefront without permanently deleting it.
5. **Search & filter**: Use the search bar (name, SKU, description) or sidebar filters (Active/Inactive, date created).

---

## 🔄 System & Order Lifecycle Flow

```
                     ┌────────────────────────┐
                     │  Customer on /shop/    │
                     │  Builds cart & submits │
                     └───────────┬────────────┘
                                 │  POST /api/orders/ (internal fetch)
                                 ▼
                     ┌────────────────────────┐
                     │  Atomic Stock Check    │
                     │  & Lock (DB layer)     │
                     └───────────┬────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 │                               │
        Insufficient Stock              Sufficient Stock
                 │                               │
                 ▼                               ▼
       [ HTTP 409 Conflict ]           Deduct stock quantity
         (Atomic Rollback)             Set Order Status = PENDING
         Red alert on /shop/           Green alert + order in list
                                                 │
                   ┌─────────────────────────────┼──────────────────────────┐
                   │                             │                          │
                   ▼                             ▼                          ▼
       Customer Cancel Button          Admin Approve Button        Admin Reject Button
       (on /shop/ order list)         (on /shop/ or /admin/)      (on /shop/ or /admin/)
                   │                             │                          │
                   ▼                             ▼                          ▼
        Restore Stock Quantity          Stock Remains Reserved      Restore Stock Quantity
        Status = CANCELLED              Status = APPROVED           Status = REJECTED
        Set `cancelled_at`              Set `approved_at`           Set `rejected_at`
```

---

## 🌟 Key Features

- **Interactive Visual Storefront (`/shop/`)**: Front-end shopping UI with interactive cart building, real-time stock indicators, and session-isolated order history per customer.
- **Role-Based Access Control**:
  - **Admins (`is_staff=True`)**: Full product management in `/admin/`, view all customer orders, approve/reject orders from both `/shop/` and `/admin/`.
  - **Customers (`is_staff=False`)**: Browse active catalog, build cart, create orders, reserve stock, and cancel their own pending orders.
  - **Guests**: Browse catalog only; must log in to place orders.
- **Atomic Stock Reservation**: Multi-item order creation with row locking (`select_for_update()`) inside an atomic transaction. If any item has insufficient stock, the transaction rolls back cleanly with **zero partial reservation**.
- **Order Lifecycle Management**:
  - `PENDING`: Initial state upon order creation with reserved stock.
  - `APPROVED`: Admin approves order, finalizing stock reservation.
  - `REJECTED`: Admin rejects order, restoring reserved stock to catalog.
  - `CANCELLED`: Customer/Admin cancels order, restoring reserved stock.
- **Safe Stock Release**: Idempotent cancellation and rejection that restore reserved quantities. Rejects invalid state transitions or double releases with `409 Conflict`.
- **Concurrency & Deadlock Safety**: Deterministic sorted lock acquisition on products prevents database deadlocks under high concurrency.
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
   - **Visual Storefront UI**: `http://127.0.0.1:8000/` → redirects to `http://127.0.0.1:8000/shop/`
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

## 📌 Assumptions & Decisions

1. **Role-Based Access Control (RBAC)**:
   - **Admin role (`is_staff=True`)**: Full product management via `/admin/`. Approve/reject orders from both `/shop/` and `/admin/`.
   - **Customer role (`is_staff=False`)**: Can browse catalog and create/cancel their own orders via `/shop/`.
   - Demo accounts provided out of the box: `admin` / `admin123` and `customer` / `customer123`.

2. **Stock Reservation Model**:
   - Stock reservation directly decrements `Product.stock_quantity` upon order creation (`PENDING`).
   - Order cancellation restores `Product.stock_quantity` by adding back the reserved quantity.
   - No secondary "reserved" counter column is used, keeping stock calculations clean and deterministic.

3. **Concurrency & Locking Strategy**:
   - `select_for_update()` row locking is used within `transaction.atomic()`.
   - Product IDs are sorted before locking (`sorted_product_ids = sorted(keys)`) to guarantee a deterministic lock acquisition order and prevent deadlocks across multi-item orders.

4. **HTTP Status Code Standardization**:
   - `201 Created` for product and order creation.
   - `200 OK` for reads, updates, and order cancellation.
   - `400 Bad Request` for schema/field validation errors (e.g. price ≤ 0, empty items list, zero quantity).
   - `403 Forbidden` for role permission rejections.
   - `404 Not Found` for missing product or order IDs.
   - `409 Conflict` for business rule rejections: insufficient stock or invalid order state transitions (e.g. cancelling an already-cancelled order).
   - `204 No Content` for soft-deleting products.

5. **Bonus Items Completed**:
   - PostgreSQL via Docker Compose: Fully wired with healthcheck and automatic migrations on startup.
   - Database Backup Fixture: Committed `backup.json` with sample products and orders.
   - Automated Concurrency Tests: Multi-threaded test suite verifying zero oversell and idempotency.

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
├── common/                # Shared utilities, custom exceptions (409 Conflict), pagination, permissions
├── products/              # Product model, serializers, views, admin, tests
├── orders/                # Order, OrderItem, atomic reservation/cancellation service, tests
├── templates/
│   └── shop.html          # Visual storefront UI (rendered at /shop/)
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
