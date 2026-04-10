"""
Manager upgrade workflow service.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import ManagerUpgradeRequestDB, ManagerUpgradeVoteDB, RoleDB, UserDB
from app.schemas.schemas import ManagerUpgradeRequestRead


class ManagerUpgradeService:
    @staticmethod
    def ensure_tables(db: Session) -> None:
        bind = db.get_bind()
        ManagerUpgradeRequestDB.__table__.create(bind=bind, checkfirst=True)
        ManagerUpgradeVoteDB.__table__.create(bind=bind, checkfirst=True)

    @staticmethod
    def create_self_request(db: Session, analyst_user_id: int, purpose: str) -> ManagerUpgradeRequestDB:
        ManagerUpgradeService.ensure_tables(db)
        analyst = db.query(UserDB).filter(UserDB.user_id == analyst_user_id).first()
        if not analyst:
            raise ValueError("User not found")
        if not ManagerUpgradeService._is_role(db, analyst.role_id, "risk analyst"):
            raise ValueError("Only risk analyst can create manager upgrade request")
        if ManagerUpgradeService._has_pending_request(db, analyst_user_id):
            raise ValueError("User already has a pending manager upgrade request")

        req = ManagerUpgradeRequestDB(
            target_user_id=analyst_user_id,
            purpose=purpose,
            status="pending",
            requested_by_role="risk analyst",
            nominated_by=None,
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def create_manager_nomination(
        db: Session,
        manager_user_id: int,
        analyst_user_id: int,
        purpose: str,
    ) -> ManagerUpgradeRequestDB:
        ManagerUpgradeService.ensure_tables(db)
        manager = db.query(UserDB).filter(UserDB.user_id == manager_user_id).first()
        analyst = db.query(UserDB).filter(UserDB.user_id == analyst_user_id).first()
        if not manager or not ManagerUpgradeService._is_role(db, manager.role_id, "manager"):
            raise ValueError("Only manager can nominate analyst")
        if not analyst:
            raise ValueError("Risk analyst user not found")
        if not ManagerUpgradeService._is_role(db, analyst.role_id, "risk analyst"):
            raise ValueError("Only risk analyst can be nominated")
        if ManagerUpgradeService._has_pending_request(db, analyst_user_id):
            raise ValueError("Risk analyst already has a pending manager upgrade request")

        req = ManagerUpgradeRequestDB(
            target_user_id=analyst_user_id,
            purpose=purpose,
            status="pending",
            requested_by_role="manager",
            nominated_by=manager_user_id,
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def list_requests(
        db: Session,
        status_filter: Optional[str] = None,
        target_user_id: Optional[int] = None,
    ) -> List[ManagerUpgradeRequestRead]:
        ManagerUpgradeService.ensure_tables(db)
        query = db.query(ManagerUpgradeRequestDB)
        if status_filter:
            query = query.filter(ManagerUpgradeRequestDB.status == status_filter.lower())
        if target_user_id:
            query = query.filter(ManagerUpgradeRequestDB.target_user_id == target_user_id)
        rows = query.order_by(ManagerUpgradeRequestDB.created_at.desc()).all()
        return [ManagerUpgradeService._to_read_model(db, row) for row in rows]

    @staticmethod
    def get_request_by_id(db: Session, request_id: int) -> ManagerUpgradeRequestRead:
        ManagerUpgradeService.ensure_tables(db)
        row = db.query(ManagerUpgradeRequestDB).filter(ManagerUpgradeRequestDB.request_id == request_id).first()
        if not row:
            raise ValueError("Request not found")
        return ManagerUpgradeService._to_read_model(db, row)

    @staticmethod
    def vote_or_decide(
        db: Session,
        request_id: int,
        actor_user_id: int,
        actor_role: str,
        action: str,
        note: Optional[str] = None,
    ) -> ManagerUpgradeRequestRead:
        ManagerUpgradeService.ensure_tables(db)
        req = db.query(ManagerUpgradeRequestDB).filter(ManagerUpgradeRequestDB.request_id == request_id).first()
        if not req:
            raise ValueError("Request not found")
        if req.status != "pending":
            raise ValueError(f"Request already {req.status}")

        action = action.lower()
        if action not in {"approve", "reject"}:
            raise ValueError("Action must be 'approve' or 'reject'")

        if actor_role == "admin":
            ManagerUpgradeService._finalize(db, req, action, actor_user_id, note)
            return ManagerUpgradeService._to_read_model(db, req)

        if actor_role != "manager":
            raise ValueError("Only manager or admin can process requests")

        vote = db.query(ManagerUpgradeVoteDB).filter(
            ManagerUpgradeVoteDB.request_id == request_id,
            ManagerUpgradeVoteDB.manager_user_id == actor_user_id,
        ).first()
        if vote:
            vote.vote = action
            vote.note = note
            vote.created_at = datetime.utcnow()
        else:
            vote = ManagerUpgradeVoteDB(
                request_id=request_id,
                manager_user_id=actor_user_id,
                vote=action,
                note=note,
            )
            db.add(vote)
        db.commit()

        approve_votes, reject_votes, total_managers = ManagerUpgradeService._count_votes(db, request_id)
        if total_managers > 0 and approve_votes > total_managers / 2:
            req = db.query(ManagerUpgradeRequestDB).filter(ManagerUpgradeRequestDB.request_id == request_id).first()
            if req and req.status == "pending":
                ManagerUpgradeService._finalize(db, req, "approve", actor_user_id, "Approved by manager majority vote")
        elif total_managers > 0 and reject_votes > total_managers / 2:
            req = db.query(ManagerUpgradeRequestDB).filter(ManagerUpgradeRequestDB.request_id == request_id).first()
            if req and req.status == "pending":
                ManagerUpgradeService._finalize(db, req, "reject", actor_user_id, note or "Rejected by manager majority vote")

        req = db.query(ManagerUpgradeRequestDB).filter(ManagerUpgradeRequestDB.request_id == request_id).first()
        if not req:
            raise ValueError("Request not found after processing")
        return ManagerUpgradeService._to_read_model(db, req)

    @staticmethod
    def _finalize(db: Session, req: ManagerUpgradeRequestDB, action: str, actor_user_id: int, note: Optional[str]) -> None:
        req.updated_at = datetime.utcnow()
        req.approved_by = actor_user_id
        req.approved_at = datetime.utcnow()

        if action == "approve":
            manager_role = ManagerUpgradeService._find_role(db, "manager")
            if not manager_role:
                raise ValueError("Role 'manager' not found")
            target = db.query(UserDB).filter(UserDB.user_id == req.target_user_id).first()
            if not target:
                raise ValueError("Target user not found")
            target.role_id = manager_role.role_id
            target.user_type = "manager"
            target.updated_at = datetime.utcnow()
            req.status = "approved"
            req.rejection_reason = None
        else:
            req.status = "rejected"
            req.rejection_reason = note or "Rejected"

        db.commit()

    @staticmethod
    def _to_read_model(db: Session, row: ManagerUpgradeRequestDB) -> ManagerUpgradeRequestRead:
        target = db.query(UserDB).filter(UserDB.user_id == row.target_user_id).first()
        nominator = db.query(UserDB).filter(UserDB.user_id == row.nominated_by).first() if row.nominated_by else None
        approve_votes, reject_votes, total_managers = ManagerUpgradeService._count_votes(db, row.request_id)
        ratio = (approve_votes / total_managers) if total_managers else 0.0

        return ManagerUpgradeRequestRead(
            request_id=row.request_id,
            target_user_id=row.target_user_id,
            target_username=target.username if target else "",
            target_email=target.email if target else "",
            purpose=row.purpose,
            status=row.status,
            requested_by_role=row.requested_by_role,
            nominated_by=row.nominated_by,
            nominated_by_username=nominator.username if nominator else None,
            approved_by=row.approved_by,
            approved_at=row.approved_at,
            rejection_reason=row.rejection_reason,
            approve_votes=approve_votes,
            reject_votes=reject_votes,
            total_managers=total_managers,
            approval_ratio=round(ratio, 4),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _count_votes(db: Session, request_id: int) -> tuple[int, int, int]:
        approve_votes = db.query(ManagerUpgradeVoteDB).filter(
            ManagerUpgradeVoteDB.request_id == request_id,
            ManagerUpgradeVoteDB.vote == "approve",
        ).count()
        reject_votes = db.query(ManagerUpgradeVoteDB).filter(
            ManagerUpgradeVoteDB.request_id == request_id,
            ManagerUpgradeVoteDB.vote == "reject",
        ).count()
        total_managers = ManagerUpgradeService._count_managers(db)
        return approve_votes, reject_votes, total_managers

    @staticmethod
    def _count_managers(db: Session) -> int:
        manager_role = ManagerUpgradeService._find_role(db, "manager")
        if not manager_role:
            return 0
        return db.query(UserDB).filter(UserDB.role_id == manager_role.role_id).count()

    @staticmethod
    def _find_role(db: Session, role_name: str) -> Optional[RoleDB]:
        role_name = role_name.lower()
        for role in db.query(RoleDB).all():
            if (role.role_name or "").lower() == role_name:
                return role
        return None

    @staticmethod
    def _is_role(db: Session, role_id: Optional[int], role_name: str) -> bool:
        if role_id is None:
            return False
        role = db.query(RoleDB).filter(RoleDB.role_id == role_id).first()
        if not role:
            return False
        current = (role.role_name or "").strip().lower()
        expected = (role_name or "").strip().lower()
        if expected in {"analyst", "risk analyst"}:
            return current in {"analyst", "risk analyst"}
        return current == expected

    @staticmethod
    def _has_pending_request(db: Session, target_user_id: int) -> bool:
        return db.query(ManagerUpgradeRequestDB).filter(
            ManagerUpgradeRequestDB.target_user_id == target_user_id,
            ManagerUpgradeRequestDB.status == "pending",
        ).first() is not None
