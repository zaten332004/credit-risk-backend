"""
Admin service: business logic for admin & system management
"""
from typing import List, Optional

from app.schemas.schemas import AuditLogRead, ExportRequestBody, ExportResponse, UserCreate, UserRead

# In-memory "repository" cho demo
_audit_logs: List[AuditLogRead] = []


def list_users() -> List[UserRead]:
    # Thực tế sẽ dùng DB; ở đây demo trống để bạn tự nối
    return []


def create_user(user: UserCreate) -> UserRead:
    # Demo trả giả; thực tế hash password và lưu DB
    return UserRead(id=1, email=user.email, full_name=user.full_name, is_active=True, is_admin=user.is_admin)


def list_audit_logs(from_date: Optional[str], to_date: Optional[str], user_id: Optional[int]) -> List[AuditLogRead]:
    return _audit_logs


def export_data(body: ExportRequestBody) -> ExportResponse:
    # Demo presigned URL giả
    return ExportResponse(file_url="https://example-bucket.s3.amazonaws.com/export/demo.csv")
