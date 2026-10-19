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
- **Trang chủ Backend API**: [http://localhost:8000](http://localhost:8000) (Trả về HTTP 200: `{"message": "Hệ thống truy xuất nguồn gốc..."}`)
- **Kiểm tra sức khỏe (Health Check)**: [http://localhost:8000/health](http://localhost:8000/health) (Trả về HTTP 200: `{"status": "ok"}`)
- **Tài liệu API tương tác (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Frontend App**: [http://localhost:3000](http://localhost:3000)
- **Giao diện Nông Sản Lành (Single-File SPA)**: Mở trực tiếp [index.html](index.html) bằng trình duyệt hoặc qua cổng web server.

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

# Chạy kiểm thử tự động
pytest

# Kiểm tra chất lượng mã nguồn với Ruff
ruff check app tests
```