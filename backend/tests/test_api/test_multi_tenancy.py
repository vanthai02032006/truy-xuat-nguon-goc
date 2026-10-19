from __future__ import annotations

from app.core.security import create_access_token
from app.models.security_log import SecurityLog
from app.repositories.batch_repository import BatchRepository


def get_auth_headers(user_email: str, role: str, org_id: int | None) -> dict[str, str]:
    """Tạo header Authorization Bearer token phục vụ test."""
    token = create_access_token(subject=user_email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


class TestStoryS05MultiTenancyIsolation:
    """
    Bộ test kiểm thử tích hợp (Integration Tests) cho Story S-05:
    'Mỗi tổ chức chỉ thấy dữ liệu của chính mình' (Sprint 1 / E-02).
    """

    def test_ac1_member_only_sees_own_organization_batches(self, client, seed_data):
        """
        AC 1: Giả sử tôi đã đăng nhập, Khi xem bất kỳ danh sách nào,
              Thì chỉ thấy bản ghi thuộc tổ chức tôi.
        """
        # 1. Người dùng thuộc Tổ chức 1 (HTX Thắng Lợi)
        headers_org1 = get_auth_headers(
            user_email=seed_data["user_org1"].email,
            role=seed_data["user_org1"].role,
            org_id=seed_data["user_org1"].organization_id,
        )
        res_org1 = client.get("/api/v1/batches", headers=headers_org1)
        assert res_org1.status_code == 200
        data_org1 = res_org1.json()

        # Tổ chức 1 có 2 lô: BATCH-TL-001 và BATCH-TL-002
        assert len(data_org1) == 2
        batch_codes_org1 = {b["batch_code"] for b in data_org1}
        assert "BATCH-TL-001" in batch_codes_org1
        assert "BATCH-TL-002" in batch_codes_org1
        # Tuyệt đối không thấy lô của Tổ chức 2
        assert "BATCH-DL-001" not in batch_codes_org1

        # 2. Người dùng thuộc Tổ chức 2 (HTX Đà Lạt)
        headers_org2 = get_auth_headers(
            user_email=seed_data["user_org2"].email,
            role=seed_data["user_org2"].role,
            org_id=seed_data["user_org2"].organization_id,
        )
        res_org2 = client.get("/api/v1/batches", headers=headers_org2)
        assert res_org2.status_code == 200
        data_org2 = res_org2.json()

        # Tổ chức 2 chỉ có 1 lô: BATCH-DL-001
        assert len(data_org2) == 1
        assert data_org2[0]["batch_code"] == "BATCH-DL-001"
        assert data_org2[0]["organization_id"] == 2

    def test_ac2_calling_other_org_batch_returns_403_and_logs_security_event(
        self, client, db_session, seed_data
    ):
        """
        AC 2: Giả sử tôi gọi thẳng API với mã bản ghi của tổ chức khác bằng công cụ dòng lệnh,
              Khi máy chủ nhận yêu cầu, Thì trả về 403 và ghi nhật ký lần thử.
        """
        headers_org1 = get_auth_headers(
            user_email=seed_data["user_org1"].email,
            role=seed_data["user_org1"].role,
            org_id=seed_data["user_org1"].organization_id,
        )

        # Lô #3 (BATCH-DL-001) thuộc về Tổ chức 2 (HTX Đà Lạt)
        target_batch_id = seed_data["batch3_org2"].id

        # Thành viên Tổ chức 1 cố tình gọi thẳng API lấy thông tin lô của Tổ chức 2
        response = client.get(
            f"/api/v1/batches/{target_batch_id}", headers=headers_org1
        )

        # Máy chủ phải trả về HTTP 403 Forbidden
        assert response.status_code == 403
        assert (
            "Không có quyền truy cập dữ liệu của tổ chức khác"
            in response.json()["detail"]
        )

        # Kiểm tra nhật ký an ninh (security_logs) đã ghi nhận lần thử này
        log_entry = (
            db_session.query(SecurityLog)
            .filter(
                SecurityLog.user_id == seed_data["user_org1"].id,
                SecurityLog.target_resource == "batch",
                SecurityLog.target_id == str(target_batch_id),
            )
            .first()
        )
        assert log_entry is not None
        assert log_entry.attempt_type == "cross_tenant_access_denied"
        assert log_entry.user_email == seed_data["user_org1"].email
        assert log_entry.target_org_id == 2
        assert f"/api/v1/batches/{target_batch_id}" in log_entry.endpoint

    def test_ac3_default_deny_when_route_lacks_permission_declaration(
        self, client, seed_data
    ):
        """
        AC 3: Giả sử một route mới được thêm mà quên khai báo quyền,
              Khi gọi route đó, Thì bị từ chối — mặc định là chặn.
        """
        headers = get_auth_headers(
            user_email=seed_data["user_org1"].email,
            role=seed_data["user_org1"].role,
            org_id=seed_data["user_org1"].organization_id,
        )

        # Route mới thêm quên khai báo quyền (_declared_permissions is None)
        res_unconfigured = client.get(
            "/api/v1/protected/unconfigured-route", headers=headers
        )
        assert res_unconfigured.status_code == 403
        assert (
            "Route chưa được khai báo quyền truy cập — mặc định là chặn"
            in res_unconfigured.json()["detail"]
        )

        # Route có khai báo quyền hợp lệ -> Truy cập thành công HTTP 200
        res_configured = client.get("/api/v1/protected/declared-perm", headers=headers)
        assert res_configured.status_code == 200
        assert res_configured.json()["status"] == "ok"

    def test_ac4_inspector_sees_all_batches_in_read_only_mode(self, client, seed_data):
        """
        AC 4: Giả sử tôi là cán bộ kiểm tra, Khi xem,
              Thì thấy được lô của mọi tổ chức nhưng chỉ ở chế độ đọc.
        """
        headers_inspector = get_auth_headers(
            user_email=seed_data["inspector"].email,
            role=seed_data["inspector"].role,
            org_id=seed_data["inspector"].organization_id,
        )

        # 1. Cán bộ kiểm tra xem danh sách: Thấy được lô của MỌI tổ chức (cả 3 lô)
        res_list = client.get("/api/v1/batches", headers=headers_inspector)
        assert res_list.status_code == 200
        all_batches = res_list.json()
        assert len(all_batches) == 3

        # 2. Cán bộ kiểm tra đọc chi tiết lô của bất kỳ tổ chức nào: Đều xem được (HTTP 200)
        res_batch1 = client.get(
            f"/api/v1/batches/{seed_data['batch1_org1'].id}", headers=headers_inspector
        )
        assert res_batch1.status_code == 200
        assert res_batch1.json()["batch_code"] == "BATCH-TL-001"

        res_batch3 = client.get(
            f"/api/v1/batches/{seed_data['batch3_org2'].id}", headers=headers_inspector
        )
        assert res_batch3.status_code == 200
        assert res_batch3.json()["batch_code"] == "BATCH-DL-001"

        # 3. Nhưng CHỈ Ở CHẾ ĐỘ ĐỌC: Cố tình tạo mới (POST) bị từ chối 403
        res_create = client.post(
            "/api/v1/batches",
            headers=headers_inspector,
            json={"batch_code": "BATCH-NEW-999", "product_name": "Rau thử nghiệm"},
        )
        assert res_create.status_code == 403
        assert "chế độ chỉ đọc" in res_create.json()["detail"]

        # 4. Cố tình xóa (DELETE) bị từ chối 403
        res_delete = client.delete(
            f"/api/v1/batches/{seed_data['batch1_org1'].id}",
            headers=headers_inspector,
        )
        assert res_delete.status_code == 403
        assert "chế độ chỉ đọc" in res_delete.json()["detail"]

    def test_nfr_query_level_filtering_database_sql(self, db_session, seed_data):
        """
        NFR: Lọc theo tổ chức ở tầng truy vấn, không lọc ở giao diện.
        Xác nhận BatchRepository thực thi câu truy vấn SQL có điều kiện WHERE organization_id.
        """
        # Truy vấn trực tiếp qua Repository
        batches_org1 = BatchRepository.list_batches(db_session, organization_id=1)
        assert len(batches_org1) == 2
        for b in batches_org1:
            assert b.organization_id == 1

        batches_org2 = BatchRepository.list_batches(db_session, organization_id=2)
        assert len(batches_org2) == 1
        assert batches_org2[0].organization_id == 2
