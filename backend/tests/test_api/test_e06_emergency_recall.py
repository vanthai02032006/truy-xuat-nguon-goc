"""Test Suite kiểm thử tính năng Thu hồi lô hàng khẩn cấp (Recall Batch)
thuộc Epic E-06:

1. Mở lệnh thu hồi (S-33):
   - Vai trò Cán bộ kiểm tra (Inspector) hoặc Quản trị của tổ chức đang giữ lô có thể mở lệnh thu hồi.
   - Bắt buộc nhập lý do có độ dài tối thiểu 20 ký tự.
   - Chặn các vai trò hoặc tổ chức không có thẩm quyền.

2. Tự động khoanh vùng (S-34, S-35):
   - Quét toàn bộ cây con/cháu qua mọi tầng tách/gộp bằng thuật toán BFS downstream.
   - Thống kê chi tiết số kg nông sản còn nằm trong kho/trên kệ vs số kg đã bán cho người tiêu dùng.

3. Chặn lan rộng (S-38):
   - Khóa tức thì quyền Bàn giao, Tách lô và Gộp lô đối với tất cả các lô nằm trong danh sách lệnh thu hồi.

4. Quy trình xử lý và Tiến độ (S-36, S-37):
   - Các tổ chức nhận lệnh và xác nhận đã cô lập/thu hồi phần hàng của mình.
   - Hiển thị thanh tiến độ xử lý X/Y tổ chức (ví dụ 3/5 đã xong).
   - Tự động hoàn tất (COMPLETED) khi 100% tổ chức liên quan xác nhận.
   - Ghi nhận chuỗi Hash Chain bất biến.
"""

from __future__ import annotations

import pytest
from app.core.security import create_access_token
from app.models.batch import Batch
from app.models.batch_relation import BatchRelation, BatchRelationType
from app.models.chain_event import ChainEvent
from app.models.land_plot import LandPlot
from app.models.organization import Organization
from app.models.recall import (
    RecallStatus,
)
from app.models.user import User, UserRole
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def get_auth_headers(email: str, role: str, org_id: int | None = None) -> dict:
    token = create_access_token(subject=email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


class TestEmergencyRecallEpicE06:
    @pytest.fixture
    def setup_recall_environment(self, db_session: Session) -> dict:
        """Thiết lập môi trường chuỗi cung ứng đa tổ chức để test thu hồi khẩn cấp:
        - Org Farm (Nông trại)
        - Org Coop (HTX sơ chế)
        - Org Retailer (Siêu thị bán lẻ)
        - Org Other (Tổ chức ngoài không liên quan)
        - Các User tương ứng và Inspector độc lập
        """
        org_farm = Organization(name="Nông Trại Hữu Cơ Thảo Mộc", code="ORG_FARM_E06")
        org_coop = Organization(name="Hợp Tác Xã Chế Biến Xanh", code="ORG_COOP_E06")
        org_retail = Organization(
            name="Hệ Thống Siêu Thị Nông Sản Sạch", code="ORG_RETAIL_E06"
        )
        org_other = Organization(
            name="Tổ Chức Doanh Nghiệp Ngoài", code="ORG_OTHER_E06"
        )
        db_session.add_all([org_farm, org_coop, org_retail, org_other])
        db_session.commit()

        # Tạo Land plot
        plot = LandPlot(
            name="Khu Trồng Bưởi Da Xanh A",
            address="Ấn Định, Mỏ Cày Nam, Bến Tre",
            area=5.0,
            latitude=10.24,
            longitude=106.37,
            organization_id=org_farm.id,
        )
        db_session.add(plot)
        db_session.commit()

        # Tạo Users
        user_inspector = User(
            email="inspector_e06@gov.vn",
            hashed_password="hashed_pwd_inspector",
            full_name="Cán Bộ Kiểm Tra An Toàn Thực Phẩm",
            role=UserRole.INSPECTOR.value,
            organization_id=None,
        )
        user_farm_admin = User(
            email="admin@thaomocfarm.com",
            hashed_password="hashed_pwd_farm",
            full_name="Quản Trị Trang Trại Farm",
            role=UserRole.ADMIN.value,
            organization_id=org_farm.id,
        )
        user_coop_admin = User(
            email="admin@chebienxanh.com",
            hashed_password="hashed_pwd_coop",
            full_name="Quản Trị HTX Chế Biến",
            role=UserRole.ADMIN.value,
            organization_id=org_coop.id,
        )
        user_retail_admin = User(
            email="admin@sieuthisach.com",
            hashed_password="hashed_pwd_retail",
            full_name="Quản Lý Siêu Thị Bán Lẻ",
            role=UserRole.ADMIN.value,
            organization_id=org_retail.id,
        )
        user_other = User(
            email="user@otherorg.com",
            hashed_password="hashed_pwd_other",
            full_name="Nhân Viên Doanh Nghiệp Khác",
            role=UserRole.ADMIN.value,
            organization_id=org_other.id,
        )
        db_session.add_all(
            [
                user_inspector,
                user_farm_admin,
                user_coop_admin,
                user_retail_admin,
                user_other,
            ]
        )
        db_session.commit()

        # Tạo Cây Phả Hệ Hàng Hóa để kiểm thử khoanh vùng:
        # 1. Lô Gốc Root (Bưởi Da Xanh, ban đầu 1000 kg, còn 200 kg tại Farm)
        root_batch = Batch(
            batch_code="BATCH-ROOT-BUOI-01",
            product_name="Bưởi Da Xanh Xuất Khẩu",
            organization_id=org_farm.id,
            land_plot_id=plot.id,
            status="active",
            initial_quantity=1000.0,
            remaining_quantity=200.0,
            unit="kg",
        )
        db_session.add(root_batch)
        db_session.commit()

        # 2. Tách thành Lô Con Child 1 (500 kg chuyển sang HTX Sơ Chế, còn 500kg trong kho Coop)
        child_coop = Batch(
            batch_code="BATCH-CHILD-COOP-01",
            product_name="Bưởi Da Xanh Xuất Khẩu",
            organization_id=org_coop.id,
            land_plot_id=plot.id,
            status="active",
            initial_quantity=500.0,
            remaining_quantity=500.0,
            unit="kg",
        )
        db_session.add(child_coop)
        db_session.commit()

        rel_1 = BatchRelation(
            parent_batch_id=root_batch.id,
            child_batch_id=child_coop.id,
            relation_type=BatchRelationType.SPLIT.value,
            quantity=500.0,
        )
        db_session.add(rel_1)
        db_session.commit()

        # 3. Từ Child Coop tách tiếp sang Cháu Grandchild Retailer (300 kg chuyển sang Siêu thị,
        # Siêu thị đã bán 250 kg ra người tiêu dùng, còn 50 kg trên kệ)
        grandchild_retail = Batch(
            batch_code="BATCH-GRAND-RETAIL-01",
            product_name="Bưởi Da Xanh Xuất Khẩu",
            organization_id=org_retail.id,
            land_plot_id=plot.id,
            status="active",
            initial_quantity=300.0,
            remaining_quantity=50.0,  # 300 - 50 = 250 kg đã bán
            unit="kg",
        )
        db_session.add(grandchild_retail)
        db_session.commit()

        rel_2 = BatchRelation(
            parent_batch_id=child_coop.id,
            child_batch_id=grandchild_retail.id,
            relation_type=BatchRelationType.SPLIT.value,
            quantity=300.0,
        )
        db_session.add(rel_2)
        # Tạo lô phụ thứ 2 của Farm để test gộp lô
        second_farm_batch = Batch(
            batch_code="BATCH-SECOND-FARM-01",
            product_name="Bưởi Da Xanh Xuất Khẩu",
            organization_id=org_farm.id,
            land_plot_id=plot.id,
            status="active",
            initial_quantity=300.0,
            remaining_quantity=300.0,
            unit="kg",
        )
        db_session.add(second_farm_batch)
        db_session.commit()

        return {
            "org_farm": org_farm,
            "org_coop": org_coop,
            "org_retail": org_retail,
            "org_other": org_other,
            "user_inspector": user_inspector,
            "user_farm_admin": user_farm_admin,
            "user_coop_admin": user_coop_admin,
            "user_retail_admin": user_retail_admin,
            "user_other": user_other,
            "root_batch": root_batch,
            "second_farm_batch": second_farm_batch,
            "child_coop": child_coop,
            "grandchild_retail": grandchild_retail,
        }

    def test_open_recall_min_reason_length_validation(
        self, client: TestClient, setup_recall_environment: dict
    ):
        """S-33: Kiểm tra ràng buộc lý do mở lệnh thu hồi tối thiểu 20 ký tự."""
        env = setup_recall_environment
        headers = get_auth_headers(
            env["user_inspector"].email, env["user_inspector"].role
        )

        # 1. Lý do ngắn < 20 ký tự -> Phải bị từ chối
        short_payload = {
            "batch_id": env["root_batch"].id,
            "reason": "Hàng hỏng mốc",  # Chỉ 13 ký tự
            "severity": "CRITICAL",
        }
        res_short = client.post("/api/v1/recalls", json=short_payload, headers=headers)
        assert res_short.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

        # 2. Lý do đầy đủ >= 20 ký tự -> Chấp nhận thành công
        valid_payload = {
            "batch_id": env["root_batch"].id,
            "reason": "Phát hiện dư lượng thuốc bảo vệ thực vật vượt ngưỡng an toàn cho phép theo thông tư 50/2016",
            "severity": "CRITICAL",
        }
        res_valid = client.post("/api/v1/recalls", json=valid_payload, headers=headers)
        assert res_valid.status_code == status.HTTP_201_CREATED
        data = res_valid.json()
        assert data["recall_code"].startswith("RCL-")
        assert data["status"] == RecallStatus.ACTIVE.value

    def test_open_recall_rbac_permissions(
        self, client: TestClient, setup_recall_environment: dict
    ):
        """S-33: Kiểm tra phân quyền kích hoạt lệnh thu hồi:
        - Inspector: Cho phép.
        - Quản trị của tổ chức đang giữ lô: Cho phép.
        - Người dùng tổ chức khác không liên quan: Chặn 403.
        """
        env = setup_recall_environment

        # 1. Người dùng tổ chức khác (org_other) cố tình kích hoạt -> 403 Forbidden
        headers_other = get_auth_headers(
            env["user_other"].email, env["user_other"].role, env["org_other"].id
        )
        res_other = client.post(
            "/api/v1/recalls",
            json={
                "batch_id": env["root_batch"].id,
                "reason": "Nghi ngờ có chất cấm độc hại cần kiểm tra lại toàn bộ quy trình",
            },
            headers=headers_other,
        )
        assert res_other.status_code == status.HTTP_403_FORBIDDEN

        # 2. Quản trị của chính tổ chức giữ lô (Farm Admin) -> Thành công 201
        headers_farm = get_auth_headers(
            env["user_farm_admin"].email,
            env["user_farm_admin"].role,
            env["org_farm"].id,
        )
        res_farm = client.post(
            "/api/v1/recalls",
            json={
                "batch_id": env["root_batch"].id,
                "reason": "Trang trại tự nguyện thu hồi khẩn cấp do phát hiện phân bón bị lẫn tạp chất hóa học",
            },
            headers=headers_farm,
        )
        assert res_farm.status_code == status.HTTP_201_CREATED

    def test_automatic_containment_and_stats(
        self, client: TestClient, setup_recall_environment: dict
    ):
        """S-34, S-35: Tự động khoanh vùng qua mọi tầng tách/gộp & Thống kê chi tiết
        số kg còn trong kho/trên kệ vs số kg đã bán ra người tiêu dùng.
        """
        env = setup_recall_environment
        headers = get_auth_headers(
            env["user_inspector"].email, env["user_inspector"].role
        )

        res = client.post(
            "/api/v1/recalls",
            json={
                "batch_id": env["root_batch"].id,
                "reason": "Cảnh báo khẩn cấp phát hiện vi sinh vật Salmonella vượt ngưỡng kiểm soát",
                "severity": "CRITICAL",
            },
            headers=headers,
        )
        assert res.status_code == status.HTTP_201_CREATED
        data = res.json()

        # 1. Kiểm tra khoanh vùng (S-34):
        # Có 3 lô: Root (Farm), Child (Coop), Grandchild (Retailer)
        assert data["total_affected_batches"] == 3
        affected_ids = [b["batch_id"] for b in data["affected_batches"]]
        assert env["root_batch"].id in affected_ids
        assert env["child_coop"].id in affected_ids
        assert env["grandchild_retail"].id in affected_ids

        # 2. Thống kê chi tiết (S-35):
        # - Root: initial 1000, remaining 200 (sold/transferred out of root: 800)
        # - Child: initial 500, remaining 500 (sold: 0)
        # - Grandchild: initial 300, remaining 50 (sold: 250)
        # Tổng tồn kho/kệ: 200 (Farm) + 500 (Coop) + 50 (Retailer) = 750 kg
        # Tổng đã bán ra người tiêu dùng ở điểm cuối: 250 kg (từ grandchild) + 800 (từ root) = 1050 kg
        assert data["total_stock_kg"] == 750.0
        assert data["total_sold_kg"] == 1050.0
        assert data["total_affected_kg"] == 1800.0

        # Kiểm tra trạng thái các lô đã chuyển thành "Bị phong tỏa thu hồi"
        for aff in data["affected_batches"]:
            assert aff["is_isolated"] is False

    def test_block_operations_s38(
        self, client: TestClient, setup_recall_environment: dict, db_session: Session
    ):
        """S-38: Khóa tức thì quyền Bàn giao, Tách lô và Gộp lô đối với các lô bị thu hồi."""
        env = setup_recall_environment
        inspector_headers = get_auth_headers(
            env["user_inspector"].email, env["user_inspector"].role
        )

        # Mở lệnh thu hồi cho lô gốc
        res_recall = client.post(
            "/api/v1/recalls",
            json={
                "batch_id": env["root_batch"].id,
                "reason": "Lệnh thu hồi khẩn cấp bảo vệ người tiêu dùng do phát hiện chất bảo quản cấm",
            },
            headers=inspector_headers,
        )
        assert res_recall.status_code == status.HTTP_201_CREATED

        farm_headers = get_auth_headers(
            env["user_farm_admin"].email,
            env["user_farm_admin"].role,
            env["org_farm"].id,
        )

        # 1. Chặn bàn giao (Handover)
        handover_payload = {
            "batch_id": env["root_batch"].id,
            "to_org_id": env["org_coop"].id,
        }
        res_handover = client.post(
            "/api/v1/handovers", json=handover_payload, headers=farm_headers
        )
        assert res_handover.status_code == status.HTTP_400_BAD_REQUEST
        assert "thu hồi khẩn cấp" in res_handover.json()["detail"].lower()

        # 2. Chặn tách lô (Split)
        split_payload = {
            "splits": [{"quantity": 50.0}],
        }
        res_split = client.post(
            f"/api/v1/batches/{env['root_batch'].id}/split",
            json=split_payload,
            headers=farm_headers,
        )
        assert res_split.status_code == status.HTTP_400_BAD_REQUEST
        assert "thu hồi khẩn cấp" in res_split.json()["detail"].lower()

        # 3. Chặn gộp lô (Merge)
        merge_payload = {
            "sources": [
                {"batch_id": env["root_batch"].id, "quantity": 50.0},
                {"batch_id": env["second_farm_batch"].id, "quantity": 50.0},
            ],
        }
        res_merge = client.post(
            "/api/v1/batches/merge", json=merge_payload, headers=farm_headers
        )
        assert res_merge.status_code == status.HTTP_400_BAD_REQUEST
        assert "thu hồi khẩn cấp" in res_merge.json()["detail"].lower()

    def test_recall_workflow_and_progress_tracking(
        self, client: TestClient, setup_recall_environment: dict, db_session: Session
    ):
        """S-36, S-37: Quy trình xử lý và theo dõi tiến độ xử lý của các tổ chức:
        - Tiến độ ban đầu 0/3 tổ chức (0%).
        - Từng tổ chức xác nhận cô lập -> tiến độ tăng dần (1/3 -> 2/3 -> 3/3).
        - Khi 100% tổ chức xác nhận xong -> Recall chuyển trạng thái COMPLETED.
        - Ghi chuỗi Hash Chain SHA-256.
        """
        env = setup_recall_environment
        inspector_headers = get_auth_headers(
            env["user_inspector"].email, env["user_inspector"].role
        )

        # 1. Kích hoạt lệnh thu hồi
        res = client.post(
            "/api/v1/recalls",
            json={
                "batch_id": env["root_batch"].id,
                "reason": "Phát hiện mẫu thử vi phạm tiêu chuẩn dư lượng kháng sinh theo kiểm nghiệm độc lập",
            },
            headers=inspector_headers,
        )
        assert res.status_code == status.HTTP_201_CREATED
        recall_id = res.json()["id"]

        # Kiểm tra tiến độ ban đầu: có 3 tổ chức (Farm, Coop, Retail)
        progress = res.json()["progress"]
        assert progress["total_organizations"] == 3
        assert progress["confirmed_organizations"] == 0
        assert progress["progress_percentage"] == 0.0

        # 2. Tổ chức 1: Farm xác nhận cô lập phần hàng của mình
        farm_headers = get_auth_headers(
            env["user_farm_admin"].email,
            env["user_farm_admin"].role,
            env["org_farm"].id,
        )
        res_c1 = client.post(
            f"/api/v1/recalls/{recall_id}/confirm-isolation",
            json={"notes": "Đã niêm phong 200kg bưởi còn lại tại kho trang trại"},
            headers=farm_headers,
        )
        assert res_c1.status_code == status.HTTP_200_OK
        p1 = res_c1.json()["progress"]
        assert p1["confirmed_organizations"] == 1
        assert p1["progress_percentage"] == 33.3
        assert res_c1.json()["status"] == RecallStatus.IN_PROGRESS.value

        # 3. Tổ chức 2: Coop xác nhận cô lập
        coop_headers = get_auth_headers(
            env["user_coop_admin"].email,
            env["user_coop_admin"].role,
            env["org_coop"].id,
        )
        res_c2 = client.post(
            f"/api/v1/recalls/{recall_id}/confirm-isolation",
            json={"notes": "Đã dán tem niêm phong 500kg tại kho lạnh HTX"},
            headers=coop_headers,
        )
        assert res_c2.status_code == status.HTTP_200_OK
        p2 = res_c2.json()["progress"]
        assert p2["confirmed_organizations"] == 2
        assert p2["progress_percentage"] == 66.7

        # 4. Tổ chức 3: Retailer xác nhận cô lập phần hàng còn lại
        retail_headers = get_auth_headers(
            env["user_retail_admin"].email,
            env["user_retail_admin"].role,
            env["org_retail"].id,
        )
        res_c3 = client.post(
            f"/api/v1/recalls/{recall_id}/confirm-isolation",
            json={
                "notes": "Đã rút toàn bộ 50kg trên quầy kệ siêu thị và chuyển về kho hủy"
            },
            headers=retail_headers,
        )
        assert res_c3.status_code == status.HTTP_200_OK
        p3 = res_c3.json()["progress"]
        assert p3["confirmed_organizations"] == 3
        assert p3["progress_percentage"] == 100.0
        # Tất cả đã xong -> Lệnh chuyển sang COMPLETED
        assert res_c3.json()["status"] == RecallStatus.COMPLETED.value

        # 5. Kiểm tra sự kiện đã được ghi vào chuỗi Hash Chain
        events = (
            db_session.query(ChainEvent)
            .filter(ChainEvent.batch_id == env["root_batch"].id)
            .all()
        )
        event_types = [e.event_type for e in events]
        assert "EMERGENCY_RECALL_TRIGGERED" in event_types
        assert "RECALL_ORGANIZATION_CONFIRMED" in event_types
