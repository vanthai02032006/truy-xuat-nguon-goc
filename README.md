# Hệ Thống Truy Xuất Nguồn Gốc và Giám Sát Chuỗi Lạnh Nông Sản

Dự án được tổ chức theo mô hình **Monorepo** gồm Backend (FastAPI, SQLAlchemy, Alembic) và Frontend (React, Vite, TailwindCSS).

---

## 1. Cấu trúc Thư mục Monorepo

```text
truyxuatnguongoc/
├── backend/
│   ├── app/
│   │   ├── main.py                # Entry point khởi tạo FastAPI
│   │   ├── core/                  # config.py, database.py, security.py
│   │   ├── api/
│   │   │   ├── deps.py            # Dependencies (get_db, ...)
│   │   │   └── v1/                # API routers
│   │   ├── models/                # SQLAlchemy ORM models
│   │   ├── schemas/               # Pydantic schemas
│   │   ├── services/              # Business logic
│   │   ├── repositories/          # Tầng truy vấn database
│   │   ├── middlewares/           # Custom middlewares
│   │   └── utils/                 # Helper functions, custom exceptions
│   ├── alembic/                   # Database migrations
│   ├── tests/                     # Test suite (test_api, test_services...)
│   ├── alembic.ini                # Cấu hình Alembic
│   ├── pytest.ini                 # Cấu hình Pytest
│   ├── requirements.txt           # Thư viện runtime
│   ├── requirements-dev.txt       # Thư viện kiểm thử và phát triển
│   ├── Dockerfile                 # Dockerfile backend
│   ├── docker-entrypoint.sh       # Script khởi chạy container
│   └── .env.example               # Mẫu cấu hình môi trường backend
├── frontend/                      # Khung ứng dụng React + Vite
│   ├── src/
│   │   ├── components/            # UI components tái sử dụng
│   │   ├── pages/                 # Màn hình ứng dụng
│   │   ├── hooks/                 # Custom React hooks
│   │   ├── context/               # React Context state
│   │   ├── services/              # Client gọi API backend
│   │   ├── utils/                 # Helper functions
│   │   ├── assets/                # Ảnh, icons, fonts
│   │   ├── styles/                # CSS tùy chỉnh
│   │   ├── App.jsx                # Component gốc
│   │   └── main.jsx               # Entry point React
│   ├── public/                    # Static assets
│   ├── .env.example               # Mẫu cấu hình môi trường frontend
│   ├── package.json               # Cấu hình npm & dependencies
│   ├── vite.config.js             # Cấu hình Vite
│   ├── tailwind.config.js         # Cấu hình TailwindCSS
│   └── Dockerfile                 # Dockerfile frontend
├── docs/                          # Tài liệu kỹ thuật, báo cáo spike
│   └── bao-cao-spike.md
├── .github/workflows/             # CI/CD workflows (CI & Deploy)
├── docker-compose.yml             # Cấu hình Docker Compose toàn hệ thống
├── .gitignore
├── .dockerignore
└── README.md
```

---

## 2. Hướng dẫn Khởi chạy (Chạy bằng 1 lệnh - Story S-01)

Theo tiêu chí nghiệm thu của **Story S-01** (*Khung ứng dụng chạy được trên máy cá nhân bằng một lệnh*), máy chỉ cần cài sẵn **Docker** và **Git**, khởi động toàn bộ hệ thống bằng một lệnh duy nhất:

```bash
docker compose up --build
```

Hệ thống sẽ tự động:
1. Khởi động PostgreSQL 16 và kiểm tra healthcheck.
2. Tự động chạy toàn bộ Database Migrations (`alembic upgrade head`) khi database còn trống.
3. Kiểm tra biến môi trường bắt buộc (dừng ngay và báo lỗi rõ ràng nếu thiếu).
4. Khởi động Backend FastAPI và Frontend.

### Điểm truy cập dịch vụ:
- **Tên miền Staging (DuckDNS)**: [http://nong-san-lanh-k18-n4.duckdns.org](http://nong-san-lanh-k18-n4.duckdns.org) (Tự động chuyển hướng sang `/app/`)
- **Giao diện Web Nông Sản Lành (SPA)**: [http://nong-san-lanh-k18-n4.duckdns.org/app/](http://nong-san-lanh-k18-n4.duckdns.org/app/)
- **Tài liệu API tương tác (Swagger UI)**: [http://nong-san-lanh-k18-n4.duckdns.org/docs](http://nong-san-lanh-k18-n4.duckdns.org/docs)
- **Kiểm tra sức khỏe (Health Check)**: [http://nong-san-lanh-k18-n4.duckdns.org/health](http://nong-san-lanh-k18-n4.duckdns.org/health)
- **Truy cập cục bộ (Localhost)**: [http://localhost](http://localhost) (mặc định cổng 80, hoặc cổng chỉ định qua biến `APP_PORT`)

---

### Cách 2: Chạy trực tiếp trên máy cục bộ (Local Development)

#### Backend
```bash
cd backend
python -m venv .venv
# Trên Windows:
.venv\Scripts\activate
# Trên Linux/macOS:
# source .venv/bin/activate

pip install -r requirements-dev.txt

# Chạy migrations
alembic upgrade head

# Chạy server development
uvicorn app.main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 3. Kiểm thử & Kiểm tra chất lượng mã nguồn (Testing & Linting)

```bash
cd backend

# Chạy kiểm thử tự động (In-memory SQLite cho CI/CD và Unit Tests)
pytest

# Kiểm tra chất lượng mã nguồn với Ruff
ruff check app tests alembic
```

---

## 4. Chuỗi Hash Bất Biến & Kiểm Tra Toàn Vẹn (User Stories S-10, S-11, S-12)

Hệ thống triển khai cơ chế chuỗi băm mật mã học (Cryptographic Hash Chain) theo chuẩn SHA-256 để bảo vệ tính toàn vẹn và chống chối bỏ cho toàn bộ sự kiện chuỗi cung ứng nông sản.

### 4.1. Cơ chế Tạo Hash & Chuẩn hóa Canonical JSON (S-10)
- **Chuẩn hóa dữ liệu**: Hàm `canonicalize_event_data` chuẩn hóa JSON tất định (sắp xếp khóa theo bảng chữ cái, chuẩn hóa định dạng số thực và ngày giờ ISO-8601 UTC, loại bỏ khoảng trắng thừa). Nhờ đó, hai sự kiện có cùng nội dung nhưng thứ tự khóa khác nhau luôn tạo ra cùng một mã băm.
- **Định dạng nối chuỗi**:
  ```text
  raw = f"{batch_id}|{event_type}|{canonical_data}|{org_id or ''}|{prev_hash}|{ts_str}"
  current_hash = SHA256(raw)
  ```
- **Tính kế thừa**:
  - Sự kiện đầu tiên của mỗi lô hàng luôn mang `previous_hash = "GENESIS"`.
  - Các sự kiện tiếp theo kế thừa `current_hash` của sự kiện liền trước làm `previous_hash`.
  - **Lưu ý tương thích**: Định dạng băm này được bảo toàn tuyệt đối để đảm bảo tương thích ngược với toàn bộ dữ liệu sự kiện đã lưu trước đây.

### 4.2. Cơ chế Bảo vệ Append-Only Đa Tầng (S-11)
Bảng `chain_events` là bảng chỉ-thêm (Append-Only) và được bảo vệ ở 4 tầng:
1. **Tầng API Router**: Không cung cấp bất kỳ endpoint `PUT`, `PATCH`, hoặc `DELETE` nào trên `/api/v1/chain-events/`.
2. **Tầng ORM SQLAlchemy**: Trình lắng nghe sự kiện `@event.listens_for(ChainEvent, "before_update")` và `"before_delete"` chủ động chặn đứng mọi thao tác cập nhật hoặc xóa từ code ứng dụng với ngoại lệ `ReadOnlyChainEventError`.
3. **Tầng Khóa Ngoại Ràng Buộc**: Khóa ngoại `chain_events.batch_id` liên kết với `batches.id` với hành vi `ON DELETE RESTRICT` (migration `0012`). Khi gọi API xóa lô hàng, hệ thống từ chối xóa lô (HTTP 400) nếu lô đã có lịch sử sự kiện, ngăn chặn hoàn toàn việc xóa lô kéo theo cascade xóa chuỗi sự kiện.
4. **Tầng Trigger CSDL PostgreSQL**:
   - Hàm trigger `prevent_chain_events_tamper()` trong PL/pgSQL:
     ```sql
     CREATE OR REPLACE FUNCTION prevent_chain_events_tamper()
     RETURNS TRIGGER AS $$
     BEGIN
         RAISE EXCEPTION 'Bảng chain_events là chỉ-thêm (append-only - S-11). Nghiêm cấm mọi thao tác UPDATE hoặc DELETE.';
     END;
     $$ LANGUAGE plpgsql;
     ```
   - Hai trigger `BEFORE UPDATE` và `BEFORE DELETE` trên bảng `chain_events` chặn đứng mọi câu lệnh SQL sửa hoặc xóa trực tiếp trong cơ sở dữ liệu.

> [!WARNING]
> **Giới hạn Bảo mật của Trigger PostgreSQL**:
> Trigger CSDL không thể ngăn cản một superuser (hoặc tài khoản có quyền owner bảng) cố tình can thiệp bằng cách chạy lệnh `ALTER TABLE chain_events DISABLE TRIGGER ...`. Do đó, giải pháp phòng thủ chuyên sâu bắt buộc phải kết hợp **Phân tách Tài khoản (Role Separation)** ở tầng cơ sở dữ liệu.

---

## 5. Phân Tách Quyền Cơ Sở Dữ Liệu: Runtime vs Migration (S-11)

Để đảm bảo nguyên tắc đặc quyền tối thiểu (Principle of Least Privilege):

| Tiêu chí | Tài khoản Quản trị / Migration (`farm_migrator`) | Tài khoản Chạy Ứng dụng (`farm_app_user`) |
| :--- | :--- | :--- |
| **Vai trò** | Schema Owner / DDL Administrator | Runtime App User (FastAPI Backend) |
| **Quyền hạn DDL** | `CREATE`, `ALTER`, `DROP` bảng, trigger, index | **KHÔNG** có quyền DDL |
| **Quyền trên `chain_events`**| Toàn quyền quản trị lược đồ | **Chỉ có `SELECT`, `INSERT`**. Bị thu hồi triệt để `UPDATE`, `DELETE`, `TRUNCATE` |
| **Biến môi trường kết nối** | `MIGRATION_DATABASE_URL` (dùng cho Alembic) | `DATABASE_URL` (dùng cho ứng dụng chạy runtime) |

### 5.1. Khởi tạo Role cho Database Mới
Chạy script dưới quyền `postgres` (Superuser) khi tạo cơ sở dữ liệu mới:
```bash
psql -U postgres -d farm_db -f backend/scripts/init_roles_new_db.sql
```

### 5.2. Nâng cấp An toàn cho Database Hiện có
Khi nâng cấp cơ sở dữ liệu đang chạy:
1. **Sao lưu trước khi thực hiện**:
   ```bash
   pg_dump -U postgres -h localhost -d farm_db -F c -b -v -f farm_db_pre_upgrade.dump
   ```
2. **Thực thi script phân quyền**:
   ```bash
   psql -U postgres -d farm_db -f backend/scripts/upgrade_existing_db_roles.sql
   ```
3. **Chạy migration Alembic dưới quyền migrator**:
   ```bash
   MIGRATION_DATABASE_URL="postgresql+psycopg://farm_migrator:PASSWORD@localhost:5432/farm_db" alembic upgrade head
   ```

> [!IMPORTANT]
> Tuyệt đối không tự ý chạy thay đổi quyền hoặc migration trực tiếp trên môi trường staging/production trong quá trình sửa mã nguồn. Mọi thay đổi quyền phải được DBA/DevOps kiểm soát theo lịch bảo trì.

---

## 6. Tính Toàn Vẹn Chuỗi & Tính Nguyên Tử Giao Dịch (S-10, S-12)

### 6.1. Giao Dịch Nguyên Tử (Atomic Transactions)
Khi tạo mới một lô hàng tại `POST /api/v1/batches`:
- Việc tạo bản ghi `Batch` và ghi sự kiện khởi tạo `BATCH_INITIALIZED` vào `chain_events` được thực hiện trong **cùng một transaction duy nhất**.
- Nếu việc ghi sự kiện băm thất bại hoặc xảy ra bất kỳ ngoại lệ nào, hệ thống sẽ thực hiện `db.rollback()` toàn bộ. Không bao giờ để lại lô hàng thiếu sự kiện hoặc sự kiện mồ côi không có lô tương ứng.

### 6.2. Thuật toán Kiểm tra Toàn vẹn (Integrity Verification - S-12)
Hàm `verify_chain_integrity`:
- Chuỗi có 1 sự kiện duy nhất được kiểm tra là hợp lệ nếu `previous_hash` thuộc tập mã khởi đầu (`GENESIS`).
- Với chuỗi nhiều sự kiện:
  - Nếu bất kỳ sự kiện nào bị sửa lén dữ liệu trong database mà không tính lại hash: thuật toán tính lại SHA-256 từ Canonical JSON và chỉ đích danh `broken_event_index` cùng mã lỗi `tampered`.
  - Nếu một sự kiện bị xóa làm đứt mạch: thuật toán phát hiện `previous_hash` của sự kiện sau không khớp với `current_hash` của sự kiện trước (`broken_link`).
  - Toàn bộ các sự kiện đứng sau vị trí đứt mạch/bị sửa được tự động đánh dấu trạng thái nghi vấn (`compromised`).

---

## 7. Hướng Dẫn Chạy Kiểm Thử (Testing Guide)

Hệ thống hỗ trợ 2 nhóm kiểm thử rõ ràng:

### 7.1. Kiểm thử Chức năng Tự động (In-memory SQLite)
Toàn bộ 142 bài kiểm thử chức năng, nghiệp vụ RBAC, chuỗi băm, tính nguyên tử transaction và kiểm tra toàn vẹn có thể chạy ngay mà không cần cài đặt PostgreSQL cục bộ:
```bash
cd backend
pytest -v
```

### 7.2. Kiểm thử Tích hợp PostgreSQL Thật (Kiểm chứng Trigger & Phân quyền)
> [!NOTE]
> Để tránh giả lập sai lệch, hệ thống **không dùng SQLite để tuyên bố đã kiểm chứng quyền PostgreSQL**.
> Bộ kiểm thử `tests/test_postgres_append_only_integration.py` được thiết kế chuyên biệt để chạy trực tiếp trên PostgreSQL thật nhằm kiểm chứng trigger `prevent_chain_events_tamper()` và quyền `farm_app_user`.

Khi có PostgreSQL thật, thiết lập biến môi trường và chạy:
```bash
# Cung cấp URL kết nối PostgreSQL (có quyền tạo bảng và trigger)
export TEST_POSTGRESQL_URL="postgresql+psycopg://postgres:postgres@localhost:5432/farm_test_db"

# (Tùy chọn) Cung cấp URL kết nối dưới quyền runtime farm_app_user để kiểm chứng phân quyền
export TEST_POSTGRESQL_RUNTIME_URL="postgresql+psycopg://farm_app_user:app_password@localhost:5432/farm_test_db"

# Chạy bộ test tích hợp PostgreSQL
pytest tests/test_postgres_append_only_integration.py -v -rs
```
- Nếu không cấu hình `TEST_POSTGRESQL_URL`, bộ test sẽ tự động `SKIPPED` với lý do rõ ràng, không gây lỗi giả cho CI/CD tiêu chuẩn.
- Khi cấu hình `TEST_POSTGRESQL_URL`, 7 ca kiểm thử tích hợp trên PostgreSQL thật sẽ được thực thi và chứng minh trực tiếp trên engine PostgreSQL.