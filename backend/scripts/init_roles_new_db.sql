-- ============================================================================
-- SCRIPT KHỞI TẠO ROLES VÀ PHÂN QUYỀN CHO DATABASE POSTGRESQL MỚI (S-10, S-11)
-- ============================================================================
-- Nguyên tắc bảo mật đặc tả:
-- 1. Tài khoản Migration (farm_migrator): Là Schema Owner, có toàn quyền DDL để chạy Alembic.
-- 2. Tài khoản Runtime (farm_app_user): Chỉ có quyền DML tối thiểu cần thiết cho ứng dụng.
--    Tuyệt đối KHÔNG PHẢI superuser, KHÔNG PHẢI owner.
--    Tuyệt đối KHÔNG CÓ QUYỀN UPDATE hoặc DELETE trên bảng chain_events (Append-only).
-- ============================================================================

-- BƯỚC 1: Tạo Database (nếu chưa có)
-- Chạy dưới quyền postgres (Superuser):
-- CREATE DATABASE farm_db;

\connect farm_db;

-- BƯỚC 2: Tạo các tài khoản (Thay đổi mật khẩu trước khi chạy trong môi trường thực tế)
DO $$
BEGIN
    -- 1. Tạo role cho Migration (Chủ sở hữu bảng/schema)
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'farm_migrator') THEN
        CREATE ROLE farm_migrator WITH LOGIN PASSWORD 'CHANGE_THIS_MIGRATOR_STRONG_PASSWORD';
    END IF;

    -- 2. Tạo role cho Ứng dụng chạy thực tế (Runtime App User)
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'farm_app_user') THEN
        CREATE ROLE farm_app_user WITH LOGIN PASSWORD 'CHANGE_THIS_APP_STRONG_PASSWORD';
    END IF;
END $$;

-- BƯỚC 3: Phân quyền Schema cho farm_migrator
ALTER SCHEMA public OWNER TO farm_migrator;
GRANT ALL PRIVILEGES ON SCHEMA public TO farm_migrator;

-- BƯỚC 4: Cấp quyền kết nối cho Runtime App
GRANT CONNECT ON DATABASE farm_db TO farm_app_user;
GRANT USAGE ON SCHEMA public TO farm_app_user;

-- BƯỚC 5: Thiết lập quyền mặc định cho các bảng do farm_migrator tạo ra sau này
ALTER DEFAULT PRIVILEGES FOR ROLE farm_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO farm_app_user;

ALTER DEFAULT PRIVILEGES FOR ROLE farm_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO farm_app_user;

-- BƯỚC 6: Sau khi chạy Alembic Migration lần đầu (alembic upgrade head):
-- Thu hồi toàn bộ quyền UPDATE, DELETE, TRUNCATE trên bảng chain_events đối với farm_app_user:
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'chain_events') THEN
        REVOKE UPDATE, DELETE, TRUNCATE ON TABLE chain_events FROM farm_app_user;
        GRANT SELECT, INSERT ON TABLE chain_events TO farm_app_user;
    END IF;
END $$;
