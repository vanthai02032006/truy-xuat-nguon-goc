from __future__ import annotations

import pytest

from app.core.security import create_access_token, get_password_hash
from app.models.land_plot import LandPlot
from app.models.user import User, UserRole


def get_auth_headers(user_email: str, role: str, org_id: int | None) -> dict[str, str]:
    token = create_access_token(subject=user_email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


class TestRBACMatrixAndWorkflows:
    """
    Bộ kiểm thử ma trận phân quyền (RBAC) 3 vai trò:
    1. Admin (Quản trị viên)
    2. Farm Owner (Chủ nông trại)
    3. Supervisor (Giám sát nông trại)
    Và quy trình phê duyệt (Approval Workflows): Đề xuất vật tư, Chấm công, Phân bổ nhiệm vụ.
    """

    @pytest.fixture
    def rbac_users(self, db_session, seed_data):
        org = seed_data["org1"]

        admin = User(
            id=100,
            email="admin@system.local",
            hashed_password=get_password_hash("password123"),
            full_name="Quản Trị Viên Hệ Thống",
            role=UserRole.ADMIN.value,
            organization_id=org.id,
            is_active=True,
        )
        owner = User(
            id=101,
            email="owner@thangloi.vn",
            hashed_password=get_password_hash("password123"),
            full_name="Chủ Nông Trại Thắng Lợi",
            role=UserRole.FARM_OWNER.value,
            organization_id=org.id,
            is_active=True,
        )
        supervisor = User(
            id=102,
            email="supervisor@thangloi.vn",
            hashed_password=get_password_hash("password123"),
            full_name="Trần Văn Giám Sát Hiện Trường",
            role=UserRole.SUPERVISOR.value,
            organization_id=org.id,
            is_active=True,
        )
        db_session.add_all([admin, owner, supervisor])
        db_session.commit()

        # Tạo sẵn 1 thửa đất phục vụ test
        plot = LandPlot(
            id=10,
            name="Thửa Đất Thử Nghiệm",
            area=5000.0,
            unit="m2",
            latitude=11.94,
            longitude=108.45,
            organization_id=org.id,
        )
        db_session.add(plot)
        db_session.commit()

        return {
            "org": org,
            "admin": admin,
            "owner": owner,
            "supervisor": supervisor,
            "plot": plot,
        }

    # =========================================================================
    # 1. KIỂM THỬ BẢO MẬT & RANH GIỚI TÀI CHÍNH (FINANCE & PAYROLL RESTRICTIONS)
    # =========================================================================

    def test_owner_can_record_transactions_and_view_finance_summary(
        self, client, rbac_users
    ):
        """Chủ nông trại có toàn quyền ghi nhận thu/chi và xem tổng kết tài chính (P&L)."""
        owner = rbac_users["owner"]
        headers = get_auth_headers(owner.email, owner.role, owner.organization_id)

        # 1. Ghi nhận doanh thu bán nông sản
        res_rev = client.post(
            "/api/v1/finance/transactions",
            headers=headers,
            json={
                "transaction_type": "revenue",
                "category": "sales",
                "amount": 50000000.0,
                "description": "Bán 5 tấn cà chua cho siêu thị",
                "transaction_date": "2026-10-20",
            },
        )
        assert res_rev.status_code == 201
        assert res_rev.json()["amount"] == 50000000.0

        # 2. Ghi nhận chi phí phân bón & vật tư
        res_exp = client.post(
            "/api/v1/finance/transactions",
            headers=headers,
            json={
                "transaction_type": "expense",
                "category": "material",
                "amount": 15000000.0,
                "description": "Chi phí phân hữu cơ NPK",
                "transaction_date": "2026-10-20",
            },
        )
        assert res_exp.status_code == 201

        # 3. Xem báo cáo tổng kết P&L
        res_sum = client.get("/api/v1/finance/summary", headers=headers)
        assert res_sum.status_code == 200
        data = res_sum.json()
        assert data["total_revenue"] == 50000000.0
        assert data["total_expense"] == 15000000.0
        assert data["net_profit"] == 35000000.0
        assert data["transaction_count"] == 2

    def test_supervisor_is_forbidden_from_financial_data(self, client, rbac_users):
        """Giám sát nông trại bị chặn hoàn toàn (403 Forbidden) khi gọi các API tài chính."""
        supervisor = rbac_users["supervisor"]
        headers = get_auth_headers(
            supervisor.email, supervisor.role, supervisor.organization_id
        )

        # 1. Gọi xem tổng kết tài chính -> 403 Forbidden
        res_sum = client.get("/api/v1/finance/summary", headers=headers)
        assert res_sum.status_code == 403
        assert "Quyền truy cập bị từ chối" in res_sum.json()["detail"]

        # 2. Gọi xem danh sách giao dịch -> 403 Forbidden
        res_list = client.get("/api/v1/finance/transactions", headers=headers)
        assert res_list.status_code == 403

        # 3. Cố gắng ghi nhận giao dịch -> 403 Forbidden
        res_post = client.post(
            "/api/v1/finance/transactions",
            headers=headers,
            json={
                "transaction_type": "expense",
                "category": "material",
                "amount": 1000000.0,
                "transaction_date": "2026-10-20",
            },
        )
        assert res_post.status_code == 403

    def test_supervisor_is_forbidden_from_payroll_summary(self, client, rbac_users):
        """Giám sát nông trại bị chặn (403 Forbidden) khi cố xem bảng tổng kết tiền lương."""
        supervisor = rbac_users["supervisor"]
        headers = get_auth_headers(
            supervisor.email, supervisor.role, supervisor.organization_id
        )

        res = client.get("/api/v1/hr/payroll", headers=headers)
        assert res.status_code == 403
        assert "Chỉ Chủ nông trại hoặc Quản trị viên" in res.json()["detail"]

    # =========================================================================
    # 2. KIỂM THỬ CHE DẤU MỨC LƯƠNG NHÂN CÔNG VỚI GIÁM SÁT (DATA MASKING)
    # =========================================================================

    def test_worker_daily_rate_visibility_between_owner_and_supervisor(
        self, client, rbac_users
    ):
        """
        Chủ nông trại tạo công nhân với mức thù lao/ngày.
        - Chủ nông trại xem danh sách: Thấy daily_rate = 300,000.
        - Giám sát xem danh sách: daily_rate = None (bị ẩn).
        """
        owner = rbac_users["owner"]
        supervisor = rbac_users["supervisor"]
        owner_headers = get_auth_headers(owner.email, owner.role, owner.organization_id)
        sup_headers = get_auth_headers(
            supervisor.email, supervisor.role, supervisor.organization_id
        )

        # 1. Chủ nông trại tạo công nhân
        create_res = client.post(
            "/api/v1/hr/workers",
            headers=owner_headers,
            json={
                "full_name": "Nguyễn Văn Làm Vườn",
                "worker_type": "seasonal",
                "phone": "0987654321",
                "daily_rate": 300000.0,
            },
        )
        assert create_res.status_code == 201
        worker_id = create_res.json()["id"]

        # 2. Chủ nông trại xem danh sách: nhìn thấy rõ mức lương daily_rate
        owner_view = client.get("/api/v1/hr/workers", headers=owner_headers)
        assert owner_view.status_code == 200
        owner_worker = next(w for w in owner_view.json() if w["id"] == worker_id)
        assert owner_worker["daily_rate"] == 300000.0

        # 3. Giám sát nông trại xem danh sách: daily_rate bị ẩn (None)
        sup_view = client.get("/api/v1/hr/workers", headers=sup_headers)
        assert sup_view.status_code == 200
        sup_worker = next(w for w in sup_view.json() if w["id"] == worker_id)
        assert sup_worker["daily_rate"] is None

    # =========================================================================
    # 3. QUY TRÌNH DUYỆT ĐỀ XUẤT VẬT TƯ (MATERIAL REQUEST WORKFLOW)
    # =========================================================================

    def test_material_request_approval_workflow(self, client, rbac_users):
        """
        Quy trình:
        1. Giám sát nông trại tạo đề xuất cấp phát vật tư (phân bón) -> status: pending.
        2. Giám sát thử tự duyệt -> 403 Forbidden!
        3. Chủ nông trại duyệt đề xuất -> status: approved, approver_id được gán.
        4. Duyệt lại lần nữa -> 400 Bad Request.
        """
        owner = rbac_users["owner"]
        supervisor = rbac_users["supervisor"]
        owner_headers = get_auth_headers(owner.email, owner.role, owner.organization_id)
        sup_headers = get_auth_headers(
            supervisor.email, supervisor.role, supervisor.organization_id
        )

        # 1. Giám sát nông trại gửi đề xuất
        req_res = client.post(
            "/api/v1/materials/requests",
            headers=sup_headers,
            json={
                "material_name": "Phân bón Kali Clorua",
                "quantity": 200.0,
                "unit": "kg",
                "purpose": "Bón thúc đợt 2 cho thửa A1",
                "urgency": "high",
            },
        )
        assert req_res.status_code == 201
        data = req_res.json()
        assert data["status"] == "pending"
        req_id = data["id"]

        # 2. Giám sát cố tình tự duyệt đề xuất của mình -> 403 Forbidden
        sup_approve_res = client.post(
            f"/api/v1/materials/requests/{req_id}/approve",
            headers=sup_headers,
        )
        assert sup_approve_res.status_code == 403

        # 3. Chủ nông trại duyệt đề xuất
        owner_approve_res = client.post(
            f"/api/v1/materials/requests/{req_id}/approve",
            headers=owner_headers,
        )
        assert owner_approve_res.status_code == 200
        approved_data = owner_approve_res.json()
        assert approved_data["status"] == "approved"
        assert approved_data["approver_id"] == owner.id

        # 4. Thử duyệt lại -> 400 Bad Request
        re_approve = client.post(
            f"/api/v1/materials/requests/{req_id}/approve",
            headers=owner_headers,
        )
        assert re_approve.status_code == 400

    def test_material_request_rejection_workflow(self, client, rbac_users):
        """Chủ nông trại từ chối đề xuất vật tư kèm lý do cụ thể."""
        owner = rbac_users["owner"]
        supervisor = rbac_users["supervisor"]
        owner_headers = get_auth_headers(owner.email, owner.role, owner.organization_id)
        sup_headers = get_auth_headers(
            supervisor.email, supervisor.role, supervisor.organization_id
        )

        # 1. Giám sát nông trại gửi đề xuất
        req_res = client.post(
            "/api/v1/materials/requests",
            headers=sup_headers,
            json={
                "material_name": "Thuốc trừ sâu sinh học thảo mộc",
                "quantity": 50.0,
                "unit": "lít",
                "purpose": "Xịt phòng ngừa sâu tơ",
                "urgency": "normal",
            },
        )
        req_id = req_res.json()["id"]

        # 2. Chủ nông trại từ chối kèm lý do
        reject_res = client.post(
            f"/api/v1/materials/requests/{req_id}/reject",
            headers=owner_headers,
            json={"reason": "Trong kho vẫn còn 30 lít chế phẩm sinh học tương đương."},
        )
        assert reject_res.status_code == 200
        rejected_data = reject_res.json()
        assert rejected_data["status"] == "rejected"
        assert (
            rejected_data["rejection_reason"]
            == "Trong kho vẫn còn 30 lít chế phẩm sinh học tương đương."
        )

    # =========================================================================
    # 4. QUY TRÌNH CHẤM CÔNG & PHÊ DUYỆT (TIMESHEET WORKFLOW)
    # =========================================================================

    def test_timesheet_and_payroll_workflow(self, client, rbac_users):
        """
        Quy trình chấm công và tính lương:
        1. Giám sát chấm công ngày cho công nhân -> status: submitted.
        2. Giám sát cố duyệt chấm công -> 403 Forbidden.
        3. Chủ nông trại duyệt chấm công -> status: approved.
        4. Chủ nông trại xem tổng kết chi phí lương tại /hr/payroll.
        """
        owner = rbac_users["owner"]
        supervisor = rbac_users["supervisor"]
        owner_headers = get_auth_headers(owner.email, owner.role, owner.organization_id)
        sup_headers = get_auth_headers(
            supervisor.email, supervisor.role, supervisor.organization_id
        )

        # Tạo công nhân với mức lương 240,000 / ngày (30,000/giờ)
        w_res = client.post(
            "/api/v1/hr/workers",
            headers=owner_headers,
            json={
                "full_name": "Lê Văn Cần Cù",
                "worker_type": "seasonal",
                "daily_rate": 240000.0,
            },
        )
        worker_id = w_res.json()["id"]

        # 1. Giám sát gửi chấm công 8 giờ
        ts_res = client.post(
            "/api/v1/hr/timesheets",
            headers=sup_headers,
            json={
                "worker_id": worker_id,
                "date": "2026-10-20",
                "hours_worked": 8.0,
                "output_quantity": 150.0,
                "output_unit": "kg",
            },
        )
        assert ts_res.status_code == 201
        ts_data = ts_res.json()
        assert ts_data["status"] == "submitted"
        ts_id = ts_data["id"]

        # 2. Giám sát cố duyệt chấm công -> 403 Forbidden
        sup_ts_approve = client.post(
            f"/api/v1/hr/timesheets/{ts_id}/approve",
            headers=sup_headers,
        )
        assert sup_ts_approve.status_code == 403

        # 3. Chủ nông trại duyệt bảng chấm công
        owner_ts_approve = client.post(
            f"/api/v1/hr/timesheets/{ts_id}/approve",
            headers=owner_headers,
        )
        assert owner_ts_approve.status_code == 200
        assert owner_ts_approve.json()["status"] == "approved"

        # 4. Chủ nông trại xem báo cáo chi phí lương
        payroll_res = client.get("/api/v1/hr/payroll", headers=owner_headers)
        assert payroll_res.status_code == 200
        payroll_data = payroll_res.json()
        assert payroll_data["total_hours_worked"] >= 8.0
        assert payroll_data["total_estimated_wage"] >= 240000.0

    # =========================================================================
    # 5. QUYỀN XÓA THỬA ĐẤT (LAND PLOT DELETION RESTRICTION)
    # =========================================================================

    def test_only_owner_and_admin_can_delete_land_plot(self, client, rbac_users):
        """
        Ràng buộc:
        - Giám sát nông trại không được phép xóa thửa đất (403 Forbidden).
        - Chủ nông trại có quyền xóa thửa đất (204 No Content).
        """
        owner = rbac_users["owner"]
        supervisor = rbac_users["supervisor"]
        plot = rbac_users["plot"]
        owner_headers = get_auth_headers(owner.email, owner.role, owner.organization_id)
        sup_headers = get_auth_headers(
            supervisor.email, supervisor.role, supervisor.organization_id
        )

        # 1. Giám sát cố xóa thửa đất -> 403 Forbidden
        sup_del = client.delete(f"/api/v1/land-plots/{plot.id}", headers=sup_headers)
        assert sup_del.status_code == 403
        assert "Chỉ Chủ nông trại hoặc Quản trị viên" in sup_del.json()["detail"]

        # 2. Chủ nông trại xóa thửa đất -> 204 No Content
        owner_del = client.delete(
            f"/api/v1/land-plots/{plot.id}", headers=owner_headers
        )
        assert owner_del.status_code == 204

    # =========================================================================
    # 6. HOẠT ĐỘNG HIỆN TRƯỜNG CỦA GIÁM SÁT (FARMING LOGS & FIELD INCIDENTS)
    # =========================================================================

    def test_supervisor_farming_logs_and_incidents(self, client, rbac_users):
        """Giám sát ghi nhật ký canh tác và báo cáo sự cố đồng ruộng."""
        supervisor = rbac_users["supervisor"]
        sup_headers = get_auth_headers(
            supervisor.email, supervisor.role, supervisor.organization_id
        )

        # Tạo thêm 1 thửa đất mới để test canh tác
        plot_res = client.post(
            "/api/v1/land-plots",
            headers=get_auth_headers(
                rbac_users["owner"].email,
                rbac_users["owner"].role,
                rbac_users["owner"].organization_id,
            ),
            json={
                "name": "Thửa Canh Tác 01",
                "area": 2000.0,
                "unit": "m2",
                "latitude": 11.95,
                "longitude": 108.46,
            },
        )
        plot_id = plot_res.json()["id"]

        # 1. Ghi nhật ký tưới tiêu & bón phân
        log_res = client.post(
            "/api/v1/farming/logs",
            headers=sup_headers,
            json={
                "plot_id": plot_id,
                "activity_type": "fertilizing",
                "description": "Bón lót phân chuồng ủ hoai mục",
                "materials_used": "Phân chuồng 500kg",
                "activity_date": "2026-10-20",
            },
        )
        assert log_res.status_code == 201
        assert log_res.json()["activity_type"] == "fertilizing"

        # 2. Báo cáo sự cố rầy mềm
        inc_res = client.post(
            "/api/v1/farming/incidents",
            headers=sup_headers,
            json={
                "plot_id": plot_id,
                "incident_type": "pest",
                "severity": "medium",
                "description": "Phát hiện rầy mềm xuất hiện mật độ nhẹ ở góc luống số 3",
            },
        )
        assert inc_res.status_code == 201
        inc_id = inc_res.json()["id"]

        # 3. Giám sát xử lý và đóng sự cố
        resolve_res = client.put(
            f"/api/v1/farming/incidents/{inc_id}/resolve",
            headers=sup_headers,
            json={"action_taken": "Đã phun dầu khoáng sinh học và tỉa bỏ lá nhiễm."},
        )
        assert resolve_res.status_code == 200
        assert resolve_res.json()["status"] == "resolved"
