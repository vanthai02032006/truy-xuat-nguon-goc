-- ============================================================================
-- SCRIPT HƯỚNG DẪN NÂNG CẤP PHÂN QUYỀN AN TOÀN CHO DATABASE POSTGRESQL HIỆN CÓ
-- (Đáp ứng User Story S-10, S-11: Phân tách vai trò Runtime vs Migration)
-- ============================================================================
--
-- QUY TẮC AN TOÀN TRƯỚC KHI THỰC HIỆN:
-- 1. SAO LƯU DỮ LIỆU: Luôn chạy pg_dump trước khi nâng cấp:
--    pg_dump -U postgres -h localhost -d farm_db -F c -b -v -f farm_db_pre_upgrade.dump
-- 2. KHÔNG THỰC HIỆN TỰ ĐỘNG TRONG QUÁ TRÌNH VIẾT CODE:
--    File này chỉ là tài liệu hướng dẫn và script chuyển đổi được kiểm soát bởi DBA/DevOps.
-- 3. CHUẨN BỊ MẬT KHẨU MẠNH CHO 2 ROLE MỚI:
--    - farm_migrator: Dùng cho CI/CD và lệnh `alembic upgrade head`
--    - farm_app_user: Dùng cho chuỗi kết nối runtime DATABASE_URL của FastAPI backend.
--
-- ============================================================================

\connect farm_db;

-- ----------------------------------------------------------------------------
-- BƯỚC 1: Tạo các Roles nếu chưa tồn tại
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    -- Role chuyên trách Migration (Schema Owner)
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'farm_migrator') THEN
        CREATE ROLE farm_migrator WITH LOGIN PASSWORD 'DAT_MAT_KHAU_MIGRATOR_O_DAY';
    END IF;

    -- Role chuyên trách Runtime Backend (Quyền DML tối thiểu)
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'farm_app_user') THEN
        CREATE ROLE farm_app_user WITH LOGIN PASSWORD 'DAT_MAT_KHAU_APP_USER_O_DAY';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- BƯỚC 2: Chuyển giao quyền sở hữu (Ownership) các bảng hiện có sang farm_migrator
-- ----------------------------------------------------------------------------
-- Lưu ý: Thực thi dưới quyền postgres (superuser) hoặc owner hiện tại của các bảng.

DO $$
DECLARE
    tbl RECORD;
    seq RECORD;
BEGIN
    -- Đổi owner cho tất cả các bảng trong schema public
    FOR tbl IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO farm_migrator;', tbl.tablename);
    END LOOP;

    -- Đổi owner cho tất cả sequence
    FOR seq IN
        SELECT sequence_name
        FROM information_schema.sequences
        WHERE sequence_schema = 'public'
    LOOP
        EXECUTE format('ALTER SEQUENCE public.%I OWNER TO farm_migrator;', seq.sequence_name);
    END LOOP;
END $$;

-- Đổi owner của schema public sang farm_migrator
ALTER SCHEMA public OWNER TO farm_migrator;
GRANT ALL PRIVILEGES ON SCHEMA public TO farm_migrator;

-- ----------------------------------------------------------------------------
-- BƯỚC 3: Cấp quyền runtime DML tối thiểu cho farm_app_user
-- ----------------------------------------------------------------------------
GRANT CONNECT ON DATABASE farm_db TO farm_app_user;
GRANT USAGE ON SCHEMA public TO farm_app_user;

-- Cấp quyền thao tác nghiệp vụ thông thường trên tất cả các bảng
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO farm_app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO farm_app_user;

-- ----------------------------------------------------------------------------
-- BƯỚC 4: THIẾT LẬP BẢO VỆ APPEND-ONLY CHO BẢNG chain_events (S-11)
-- ----------------------------------------------------------------------------
-- Thu hồi dứt điểm quyền UPDATE, DELETE, TRUNCATE trên chain_events đối với farm_app_user:
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'chain_events') THEN
        REVOKE UPDATE, DELETE, TRUNCATE ON TABLE chain_events FROM farm_app_user;
        GRANT SELECT, INSERT ON TABLE chain_events TO farm_app_user;
        RAISE NOTICE 'Da thu hoi quyen UPDATE/DELETE tren chain_events tu farm_app_user thanh cong.';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- BƯỚC 5: Thiết lập Default Privileges cho các bảng do farm_migrator tạo trong tương lai
-- ----------------------------------------------------------------------------
ALTER DEFAULT PRIVILEGES FOR ROLE farm_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO farm_app_user;

ALTER DEFAULT PRIVILEGES FOR ROLE farm_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO farm_app_user;

-- ----------------------------------------------------------------------------
-- BƯỚC 6: Kiểm tra và xác nhận quyền sau nâng cấp (Verification Queries)
-- ----------------------------------------------------------------------------
-- Kết quả mong đợi:
-- can_insert = true
-- can_select = true
-- can_update = false
-- can_delete = false
SELECT 
    has_table_privilege('farm_app_user', 'chain_events', 'INSERT') AS can_insert,
    has_table_privilege('farm_app_user', 'chain_events', 'SELECT') AS can_select,
    has_table_privilege('farm_app_user', 'chain_events', 'UPDATE') AS can_update,
    has_table_privilege('farm_app_user', 'chain_events', 'DELETE') AS can_delete;
