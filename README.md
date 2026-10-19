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

## 2. Hướng dẫn Khởi chạy

### Cách 1: Khởi chạy bằng Docker Compose (Khuyên dùng)
```bash
# Sao chép file cấu hình môi trường
cp backend/.env.example backend/.env

# Khởi động toàn bộ dịch vụ (PostgreSQL, Backend, Frontend)
docker compose up -d --build
```
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Frontend App**: [http://localhost:3000](http://localhost:3000)

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