from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.organization import Organization
from app.models.user import User, UserRole


def get_auth_headers(email: str, role: str, org_id: int) -> dict:
    token = create_access_token(subject=email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


class TestSeedLineageDagDataset:
    def test_seed_dag_sample_data_endpoint(self, client: TestClient, db_session: Session):
        """
        Kiểm thử API nạp bộ dữ liệu mẫu phả hệ 3-4 tầng (Seed S-22 / S-39):
        - Tạo sẵn đồ thị ít nhất 12 lô qua 3+ tổ chức có cả tách lẫn gộp.
        - Có đáp án đếm tay để đối chiếu.
        - Kiểm tra đồ thị DAG không có chu trình.
        """
        # Tạo user Admin hoặc Inspector để gọi API
        org = Organization(name="Hệ Thống Quản Trị", code="ORG_SYS_ADMIN")
        db_session.add(org)
        db_session.commit()

        admin_user = User(
            email="admin_seed@example.com",
            hashed_password="fakehash",
            full_name="Quản Trị Viên Seed",
            role=UserRole.SYSTEM_ADMIN.value,
            organization_id=org.id,
            is_active=True,
        )
        db_session.add(admin_user)
        db_session.commit()

        headers = get_auth_headers(admin_user.email, admin_user.role, org.id)

        # 1. Gọi POST /api/v1/batches/seed-lineage-dag
        res = client.post("/api/v1/batches/seed-lineage-dag", headers=headers)
        assert res.status_code == status.HTTP_201_CREATED, res.text
        data = res.json()

        assert data["total_batches"] >= 12
        assert data["total_organizations"] >= 3
        assert data["total_relations"] >= 10
        assert "answer_key" in data

        answer_key = data["answer_key"]
        assert "focus_merge_m1" in answer_key
        assert "focus_root_tom_01" in answer_key
        assert "recall_scenario_m1" in answer_key

        m1_id = answer_key["focus_merge_m1"]["batch_id"]
        root1_id = answer_key["focus_root_tom_01"]["batch_id"]

        # 2. Kiểm tra truy vấn DAG Graph của lô gộp MERGE-TOM-M1
        dag_res = client.get(f"/api/v1/batches/{m1_id}/dag-graph", headers=headers)
        assert dag_res.status_code == status.HTTP_200_OK, dag_res.text
        dag_data = dag_res.json()

        assert dag_data["focus_batch"]["batch_code"] == "MERGE-TOM-M1"
        assert len(dag_data["roots"]) == 2  # ROOT-TOM-01 và ROOT-CHERRY-02
        assert len(dag_data["descendants"]) == 3  # RETAIL-01, RETAIL-02, STOCK-BACKUP

        # 3. Kiểm tra đối chiếu số kg trên kệ vs đã bán
        shelf_kg = sum(d["remaining_quantity"] for d in dag_data["descendants"])
        # RETAIL-02 còn 150 kg, STOCK-BACKUP còn 200 kg => 350 kg
        assert round(shelf_kg, 1) == 350.0

        # 4. Kiểm tra truy xuôi từ Lô gốc ROOT-TOM-01
        desc_res = client.get(f"/api/v1/batches/{root1_id}/descendants", headers=headers)
        assert desc_res.status_code == status.HTTP_200_OK
        desc_data = desc_res.json()
        assert desc_data["descendant_count"] == 8

        # 5. Kiểm tra tính idempotency: Gọi seed lần 2 không bị lỗi trùng lặp
        res2 = client.post("/api/v1/batches/seed-lineage-dag", headers=headers)
        assert res2.status_code == status.HTTP_201_CREATED
