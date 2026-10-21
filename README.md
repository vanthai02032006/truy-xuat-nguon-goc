# Hệ Thống Truy Xuất Nguồn Gốc và Giám Sát Chuỗi Lạnh Nông Sản

> **Product Goal**: Chuỗi cung ứng nông sản truy được nguồn gốc từng lô từ vườn tới tay người mua, phát hiện được vi phạm chuỗi lạnh, và khi có sự cố thì chỉ ra đúng và đủ mọi lô hàng liên quan trong vòng vài phút thay vì vài ngày. Hệ thống được tổ chức theo mô hình **Monorepo** đa tổ chức (Multi-Tenant), bảo vệ toàn vẹn lịch sử bằng **Cryptographic Hash Chain SHA-256** (chốt cứng không sử dụng Blockchain theo Spike K-01).

---

## 1. Thông Tin Dự Án & Thông Số Vận Hành Scrum

| Trường thông tin | Giá trị cấu hình |
| :--- | :--- |
| **Tên dự án** | Truy xuất nguồn gốc và giám sát chuỗi lạnh nông sản |
| **Quy mô đội ngũ** | 5 Developer (cả 5 thành viên đều lập trình; không có QA, DevOps, Designer riêng) |
| **Độ dài Sprint / Ngày làm việc** | 1 tuần / 5 ngày làm việc mỗi Sprint |
| **Focus Factor / Đơn vị ước lượng** | 0.5 / Story Point (dãy số Fibonacci) |
| **Kinh nghiệm team / Phương pháp** | Thực tập / Mới ra trường — mới áp dụng Scrum |
| **Loại dự án** | Mới tinh (Greenfield) |
| **Ràng buộc tuân thủ** | An toàn thực phẩm, thời gian cách ly PHI và truy xuất nguồn gốc; bảo vệ dữ liệu định danh nông hộ và cơ sở sơ chế (Nghị định 13/2023/NĐ-CP) |

---

## 2. Điểm Truy Cập Dịch Vụ (Endpoints)

- **Tên miền Staging (DuckDNS - HTTPS/SSL)**: [https://nong-san-lanh-k18-n4.duckdns.org](https://nong-san-lanh-k18-n4.duckdns.org) *(Tự động chuyển hướng sang `/app/`)*
- **Giao diện Web Nông Sản Lành (SPA)**: [https://nong-san-lanh-k18-n4.duckdns.org/app/](https://nong-san-lanh-k18-n4.duckdns.org/app/)
- **Tài liệu API tương tác (Swagger UI)**: [https://nong-san-lanh-k18-n4.duckdns.org/docs](https://nong-san-lanh-k18-n4.duckdns.org/docs)
- **Kiểm tra sức khỏe (Health Check)**: [https://nong-san-lanh-k18-n4.duckdns.org/health](https://nong-san-lanh-k18-n4.duckdns.org/health)
- **Truy cập cục bộ (Localhost)**: [http://localhost](http://localhost) *(Mặc định cổng 80, hoặc cổng chỉ định qua biến `APP_PORT`)*

---

## 3. Cấu Trúc Thư Mục Monorepo

```text
truyxuatnguongoc/
├── backend/
│   ├── app/
│   │   ├── main.py                # Entry point khởi tạo FastAPI
│   │   ├── core/                  # config.py, database.py, security.py (Argon2id)
│   │   ├── api/
│   │   │   ├── deps.py            # Dependencies (get_db, get_current_user...)
│   │   │   └── v1/                # API routers (batches, events, trips, audit...)
│   │   ├── models/                # SQLAlchemy ORM models
│   │   ├── schemas/               # Pydantic schemas
│   │   ├── services/              # Business logic (hash chain, lineage, seeder...)
│   │   ├── repositories/          # Tầng truy vấn database
│   │   ├── middlewares/           # Custom middlewares (RBAC, Tenant Isolation)
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
├── frontend/                      # Khung ứng dụng React + Vite + TailwindCSS
│   ├── src/
│   │   ├── components/            # UI components tái sử dụng
│   │   ├── pages/                 # Màn hình ứng dụng theo từng Story
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
├── docs/                          # Tài liệu kỹ thuật, báo cáo spike (K-01)
│   └── bao-cao-spike.md
├── .github/workflows/             # CI/CD workflows (CI & Deploy)
├── docker-compose.yml             # Cấu hình Docker Compose toàn hệ thống
├── .gitignore
├── .dockerignore
└── README.md
```

---

## 4. Lộ Trình 8 Sprint & Danh Mục Epics (Product Backlog)

### 4.1. Kế hoạch 8 Sprint

| Sprint | Capacity | Đã Xếp | Sprint Goal |
| :--- | :--- | :--- | :--- |
| **Sprint 1** | 12 SP | 12 SP | Vùng trồng khai báo được thửa đất của mình trên môi trường staging chạy thật, và mọi thay đổi mã đều đi qua CI. |
| **Sprint 2** | 20 SP | 20 SP | Lô thu hoạch được ghi nhận, bàn giao được, và lịch sử của nó không ai sửa lén được mà không bị phát hiện. |
| **Sprint 3** | 20 SP | 20 SP | Lô tách và gộp được ở hợp tác xã, và từ lô bất kỳ truy ngược ra đúng vùng trồng gốc. |
| **Sprint 4** | 20 SP | 20 SP | Từ một lô gốc chỉ ra được mọi lô con đã phát sinh và nơi chúng đang nằm. |
| **Sprint 5** | 20 SP | 20 SP | Thu hồi một lô chỉ ra đúng và đủ mọi lô liên quan, và từng bên xác nhận được đã xử lý. |
| **Sprint 6** | 20 SP | 20 SP | Vi phạm chuỗi lạnh trên đường vận chuyển được phát hiện đúng và gắn vào từng lô liên quan. |
| **Sprint 7** | 20 SP | 20 SP | Người tiêu dùng quét QR xem được hành trình lô hàng mà không lộ dữ liệu nội bộ. |
| **Sprint 8** | 20 SP | 20 SP | Cán bộ kiểm tra tự tra cứu và xuất được hồ sơ truy xuất đầy đủ mà không cần lập trình viên hỗ trợ. |

### 4.2. Ánh xạ Epics & User Stories

- **E-01 (Hạ tầng, CI/CD và môi trường):** S-01 (Chạy 1 lệnh Docker), S-02 (CI chặn merge lỗi), S-03 (Tự động deploy staging).
- **E-02 (Tài khoản, tổ chức và phân quyền):** S-04 (Đăng nhập Argon2id, khóa sau 5 lần sai), S-05 (Cách ly dữ liệu theo organization_id ở tầng SQL), S-23 (Xem lịch sử tổ tiên), S-31 (Audit log thao tác), S-63 (Mời thành viên).
- **E-03 (Vùng trồng, sản phẩm và lô hàng):** S-06 (Khai báo thửa đất GPS), S-07 (Danh mục sản phẩm), S-08 (Sinh mã lô 8 ký tự ngẫu nhiên), S-09 (Kiểm tra hợp lệ máy chủ), S-14 (Danh sách lô đang giữ), S-25 (Chi tiết lô), S-30 (Chia lô về cửa hàng), S-32 (Nhập CSV), S-62 (Nhật ký vật tư & Kiểm tra thời gian cách ly PHI).
- **E-04 (Sự kiện chuỗi cung ứng và chuỗi bản ghi bất biến):** K-01 (Spike chọn Hash Chain thay vì Blockchain), S-10 (Sự kiện nối tiếp SHA-256), S-11 (Chặn sửa xóa sự kiện ở DB), S-12 (Kiểm tra toàn vẹn phát hiện đứt mạch), S-13 (Dòng thời gian sự kiện), S-15 & S-16 (Bàn giao và xác nhận/từ chối), S-24 (Đánh dấu bàn giao quá hạn 48h), S-61 (Ghi nhận công đoạn sơ chế).
- **E-05 (Phả hệ lô hàng: tách và gộp):** S-17 (Tách lô), S-18 (Khóa dòng SELECT ... FOR UPDATE chống tách vượt khối lượng), S-19 (Gộp lô cùng sản phẩm), S-20 (Ghi sự kiện tách/gộp), S-21 (BFS truy ngược nguồn gốc chống chu trình), S-22 (Dữ liệu mẫu 3 tầng có đáp án đếm tay), S-26 & S-27 (BFS truy xuôi hậu duệ kèm vị trí/số dư), S-28 (Sơ đồ cây phả hệ), S-29 (Ghi nhận lô đã tiêu thụ hết).
- **E-06 (Thu hồi lô hàng):** S-33 (Mở lệnh thu hồi khẩn cấp), S-34 & S-35 (Liệt kê toàn bộ lô hậu duệ, nơi giữ và lượng tồn), S-37 (Theo dõi tiến độ xác nhận), S-38 (Khóa thao tác lô bị thu hồi), S-39 (Dữ liệu thu hồi mẫu 4 tầng).
- **E-07 (Giám sát chuỗi lạnh & IoT):** S-40 (Quản lý chuyến xe lạnh), S-41 (Ghi nhận nhiệt độ thời gian thực), S-42 (Script giả lập 5 kịch bản cảm biến), S-43 (Phát hiện vi phạm ngưỡng có độ trễ 30 phút, gộp dưới 5 phút), S-44 (Cấu hình ngưỡng theo sản phẩm), S-45 (Ghi sự kiện vi phạm vào chuỗi lô hàng), S-51 (Nén dữ liệu nhiệt độ cũ theo giờ).
- **E-08 (Trang truy xuất công khai quét QR):** S-46 (Sinh mã QR PNG/SVG), S-47 (Tra cứu hành trình không cần đăng nhập), S-48 (Ẩn trường nhạy cảm nội bộ), S-49 (Cảnh báo đỏ nếu lô bị thu hồi), S-50 (Cache 60s & Rate-limit 30 mã/phút chống cào dữ liệu), S-60 (Bản đồ vị trí hành trình).
- **E-09 (Báo cáo và hồ sơ kiểm tra):** S-52 (Cán bộ kiểm tra tra cứu toàn hệ thống), S-53 (Xuất PDF kèm kết quả toàn vẹn và hash cuối chuỗi), S-54 (Thống kê vi phạm theo nhà xe).
- **E-10 (Vận hành và bảo vệ dữ liệu):** S-55 (Job đêm kiểm tra toàn vẹn định kỳ), S-56 (Xóa dữ liệu định danh nông hộ theo Nghị định 13/2023/NĐ-CP mà không làm vỡ chuỗi hash), S-57 (Sao lưu hàng đêm & diễn tập khôi phục).
- **E-11 (Thông báo và cảnh báo):** S-36 (Cảnh báo và xác nhận thu hồi), S-58 (Trung tâm thông báo ứng dụng), S-59 (Gửi email thu hồi tự động).

---

## 5. Hướng Dẫn Khởi Chạy (Chạy bằng 1 lệnh - Story S-01)

### Cách 1: Khởi chạy bằng Docker Compose (Khuyên dùng)

Theo tiêu chí nghiệm thu của Story S-01, máy chỉ cần cài sẵn Docker và Git, khởi động toàn bộ hệ thống bằng một lệnh duy nhất:

```bash
docker compose up --build
```

Hệ thống sẽ tự động:
1. Khởi động PostgreSQL 16 và kiểm tra healthcheck.
2. Tự động chạy toàn bộ Database Migrations (`alembic upgrade head`) khi database còn trống.
3. Kiểm tra biến môi trường bắt buộc (dừng ngay và báo lỗi rõ ràng nếu thiếu).
4. Khởi động Backend FastAPI và Frontend.

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

## 6. Chuỗi Hash Bất Biến & Kiểm Tra Toàn Vẹn (User Stories S-10, S-11, S-12)

Hệ thống triển khai cơ chế chuỗi băm mật mã học (Cryptographic Hash Chain) theo chuẩn SHA-256 để bảo vệ tính toàn vẹn và chống chối bỏ cho toàn bộ sự kiện chuỗi cung ứng nông sản.

### 6.1. Cơ chế Tạo Hash & Chuẩn hóa Canonical JSON (S-10)

- **Chuẩn hóa dữ liệu:** Hàm `canonicalize_event_data` chuẩn hóa JSON tất định (sắp xếp khóa theo bảng chữ cái, chuẩn hóa định dạng số thực và ngày giờ ISO-8601 UTC, loại bỏ khoảng trắng thừa). Nhờ đó, hai sự kiện có cùng nội dung nhưng thứ tự khóa khác nhau luôn tạo ra cùng một mã băm.
- **Định dạng nối chuỗi:**
```text
raw = f"{batch_id}|{event_type}|{canonical_data}|{org_id or ''}|{prev_hash}|{ts_str}"
current_hash = SHA256(raw)
```
- **Tính kế thừa:**
  - Sự kiện đầu tiên của mỗi lô hàng luôn mang `previous_hash = "GENESIS"`.
  - Các sự kiện tiếp theo kế thừa `current_hash` của sự kiện liền trước làm `previous_hash`.
- **Lưu ý tương thích:** Định dạng băm này được bảo toàn tuyệt đối để đảm bảo tương thích ngược với toàn bộ dữ liệu sự kiện đã lưu trước đây.

### 6.2. Cơ chế Bảo vệ Append-Only Đa Tầng (S-11)

Bảng `chain_events` là bảng chỉ-thêm (Append-Only) và được bảo vệ ở 4 tầng:
1. **Tầng API Router:** Không cung cấp bất kỳ endpoint PUT, PATCH, hoặc DELETE nào trên `/api/v1/chain-events/`.
2. **Tầng ORM SQLAlchemy:** Trình lắng nghe sự kiện `@event.listens_for(ChainEvent, "before_update")` và `"before_delete"` chủ động chặn đứng mọi thao tác cập nhật hoặc xóa từ code ứng dụng với ngoại lệ `ReadOnlyChainEventError`.
3. **Tầng Khóa Ngoại Ràng Buộc:** Khóa ngoại `chain_events.batch_id` liên kết với `batches.id` với hành vi `ON DELETE RESTRICT` (migration 0012). Khi gọi API xóa lô hàng, hệ thống từ chối xóa lô (HTTP 400) nếu lô đã có lịch sử sự kiện, ngăn chặn hoàn toàn việc xóa lô kéo theo cascade xóa chuỗi sự kiện.
4. **Tầng Trigger CSDL PostgreSQL:**
   Hàm trigger `prevent_chain_events_tamper()` trong PL/pgSQL:
   ```sql
   CREATE OR REPLACE FUNCTION prevent_chain_events_tamper()
   RETURNS TRIGGER AS $$
   BEGIN
       RAISE EXCEPTION 'Bảng chain_events là chỉ-thêm (append-only - S-11). Nghiêm cấm mọi thao tác UPDATE hoặc DELETE.';
   END;
   $$ LANGUAGE plpgsql;
   ```
   Hai trigger `BEFORE UPDATE` và `BEFORE DELETE` trên bảng `chain_events` chặn đứng mọi câu lệnh SQL sửa hoặc xóa trực tiếp trong cơ sở dữ liệu.

---

## 7. Phân Tách Quyền Cơ Sở Dữ Liệu: Runtime vs Migration (S-11)

Để đảm bảo nguyên tắc đặc quyền tối thiểu (Principle of Least Privilege):

| Tiêu chí | Tài khoản Quản trị / Migration (`farm_migrator`) | Tài khoản Chạy Ứng dụng (`farm_app_user`) |
| :--- | :--- | :--- |
| **Vai trò** | Schema Owner / DDL Administrator | Runtime App User (FastAPI Backend) |
| **Quyền hạn DDL** | `CREATE`, `ALTER`, `DROP` bảng, trigger, index | **KHÔNG** có quyền DDL |
| **Quyền trên `chain_events`** | Toàn quyền quản trị lược đồ | Chỉ có `SELECT`, `INSERT`. Bị thu hồi triệt để `UPDATE`, `DELETE`, `TRUNCATE` |
| **Biến môi trường kết nối** | `MIGRATION_DATABASE_URL` (dùng cho Alembic) | `DATABASE_URL` (dùng cho ứng dụng chạy runtime) |

---

## 8. Tính Toàn Vẹn Chuỗi & Tính Nguyên Tử Giao Dịch (S-10, S-12)

### 8.1. Giao Dịch Nguyên Tử (Atomic Transactions)
Khi tạo mới một lô hàng tại `POST /api/v1/batches`:
- Việc tạo bản ghi `Batch` và ghi sự kiện khởi tạo `BATCH_INITIALIZED` vào `chain_events` được thực hiện trong cùng một transaction duy nhất.
- Nếu việc ghi sự kiện băm thất bại hoặc xảy ra bất kỳ ngoại lệ nào, hệ thống sẽ thực hiện `db.rollback()` toàn bộ. Không bao giờ để lại lô hàng thiếu sự kiện hoặc sự kiện mồ côi không có lô tương ứng.

### 8.2. Thuật toán Kiểm tra Toàn vẹn (Integrity Verification - S-12)
Hàm `verify_chain_integrity`:
- Chuỗi có 1 sự kiện duy nhất được kiểm tra là hợp lệ nếu `previous_hash` thuộc tập mã khởi đầu (`GENESIS`).
- Với chuỗi nhiều sự kiện:
  - Nếu bất kỳ sự kiện nào bị sửa lén dữ liệu trong database mà không tính lại hash: thuật toán tính lại SHA-256 từ Canonical JSON và chỉ đích danh `broken_event_index` cùng mã lỗi `tampered`.
  - Nếu một sự kiện bị xóa làm đứt mạch: thuật toán phát hiện `previous_hash` của sự kiện sau không khớp với `current_hash` của sự kiện trước (`broken_link`).
  - Toàn bộ các sự kiện đứng sau vị trí đứt mạch/bị sửa được tự động đánh dấu trạng thái nghi vấn (`compromised`).

---

## 9. Hướng Dẫn Chạy Kiểm Thử & Kiểm Tra Mã Nguồn (Testing & Linting)

```bash
cd backend

# Chạy bộ kiểm thử tự động (in-memory SQLite)
pytest -v

# Kiểm tra chất lượng mã nguồn với Ruff
ruff check app tests alembic

# Chạy bộ test tích hợp PostgreSQL thật (Kiểm chứng trigger & phân quyền)
export TEST_POSTGRESQL_URL="postgresql+psycopg://postgres:postgres@localhost:5432/farm_test_db"
pytest tests/test_postgres_append_only_integration.py -v
```

---

## 10. Tiêu Chuẩn Hoàn Thành & Sẵn Sàng (DoD / DoR)

### Definition of Done (DoD):
- Code review đã duyệt bởi ít nhất một thành viên khác.
- Unit test cho nhánh logic mới; độ phủ trên phần thay đổi không giảm.
- CI xanh: build, lint, typecheck, test.
- Không có secret trong mã nguồn; quét phụ thuộc sạch.
- AC pass trên môi trường staging, không chỉ trên máy cá nhân.
- Story chạm sự kiện của lô: kiểm tra toàn vẹn chuỗi vẫn báo hợp lệ sau khi chạy.
- Story chạm đồ thị phả hệ: có ca kiểm thử với bộ dữ liệu mẫu có đáp án đếm tay và ca chu trình.
- Story chạm khối lượng: có test hai giao dịch đồng thời.
- Không log dữ liệu định danh nông hộ.
- README.md cập nhật nếu đổi hành vi công khai hoặc thêm biến môi trường.

### Definition of Ready (DoR):
- Đủ nhỏ để Done trong 1 sprint (story đã chẻ task con $\le$ nửa ngày).
- Dependency ngoài đã có cam kết.
- Có AC viết dạng Giả sử / Khi / Thì.
- Đã ước lượng Story Point bởi chính team, không dùng SP thô của backlog.