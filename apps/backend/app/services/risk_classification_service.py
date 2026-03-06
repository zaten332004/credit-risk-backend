"""
Risk Classification System - Based on SBV Circular 11/2021/TT-NHNN
(and updated regulations like 31/2024/TT-NHNN)

Classified loans into 5 risk groups based on days overdue
"""
from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, Tuple


class RiskGroup(Enum):
    """SBV Risk Classification Groups"""
    
    GROUP_1 = {
        "id": 1,
        "name": "Nợ đủ tiêu chuẩn",
        "name_en": "Standard Loans",
        "description": "Within due date or overdue less than 10 days",
        "description_vn": "Trong hạn hoặc quá hạn dưới 10 ngày",
        "days_from": 0,
        "days_to": 9,
        "risk_level": "Rất thấp",
        "provision_rate": 0.0,  # 0% provision
        "color": "green",
        "icon": "check_circle"
    }
    
    GROUP_2 = {
        "id": 2,
        "name": "Nợ cần chú ý",
        "name_en": "Loans Requiring Attention",
        "description": "Overdue from 10 to less than 90 days",
        "description_vn": "Quá hạn từ 10 ngày đến dưới 90 ngày",
        "days_from": 10,
        "days_to": 89,
        "risk_level": "Thấp",
        "provision_rate": 0.01,  # 1% provision
        "color": "yellow",
        "icon": "warning"
    }
    
    GROUP_3 = {
        "id": 3,
        "name": "Nợ dưới tiêu chuẩn",
        "name_en": "Substandard Loans",
        "description": "Overdue from 91 to 180 days (Beginning of bad debt)",
        "description_vn": "Quá hạn từ 91 đến 180 ngày (Bắt đầu là nợ xấu)",
        "days_from": 91,
        "days_to": 180,
        "risk_level": "Trung bình cao",
        "provision_rate": 0.25,  # 25% provision
        "color": "orange",
        "icon": "info"
    }
    
    GROUP_4 = {
        "id": 4,
        "name": "Nợ nghi ngờ",
        "name_en": "Doubtful Loans",
        "description": "Overdue from 181 to 360 days",
        "description_vn": "Quá hạn từ 181 đến 360 ngày",
        "days_from": 181,
        "days_to": 360,
        "risk_level": "Cao",
        "provision_rate": 0.50,  # 50% provision
        "color": "red",
        "icon": "error_outline"
    }
    
    GROUP_5 = {
        "id": 5,
        "name": "Nợ có khả năng mất vốn",
        "name_en": "Loss Loans",
        "description": "Overdue over 360 days or unrecoverable",
        "description_vn": "Quá hạn trên 360 ngày hoặc mất khả năng thu hồi",
        "days_from": 361,
        "days_to": 999999,  # Very large number
        "risk_level": "Rất cao",
        "provision_rate": 1.0,  # 100% provision
        "color": "dark_red",
        "icon": "cancel"
    }


@dataclass
class RiskClassification:
    """Risk classification result"""
    risk_group_id: int
    risk_group_name: str
    risk_group_name_en: str
    risk_level: str
    days_overdue: int
    days_from: int
    days_to: int
    provision_rate: float
    color: str
    icon: str
    classification_date: datetime
    description: str


class RiskClassificationService:
    """Service for classifying loans into risk groups based on SBV regulations"""
    
    # Risk group mapping
    RISK_GROUPS = {
        group.value["id"]: group.value
        for group in RiskGroup
    }
    
    @staticmethod
    def classify_by_days_overdue(days_overdue: int) -> RiskClassification:
        """
        Classify loan into risk group based on days overdue
        
        Args:
            days_overdue: Number of days the loan is overdue
            
        Returns:
            RiskClassification object with all details
        """
        # Find matching risk group
        for group_enum in RiskGroup:
            group_data = group_enum.value
            if group_data["days_from"] <= days_overdue <= group_data["days_to"]:
                return RiskClassification(
                    risk_group_id=group_data["id"],
                    risk_group_name=group_data["name"],
                    risk_group_name_en=group_data["name_en"],
                    risk_level=group_data["risk_level"],
                    days_overdue=days_overdue,
                    days_from=group_data["days_from"],
                    days_to=group_data["days_to"],
                    provision_rate=group_data["provision_rate"],
                    color=group_data["color"],
                    icon=group_data["icon"],
                    classification_date=datetime.utcnow(),
                    description=group_data["description_vn"]
                )
        
        # Default to Group 5 if not found
        group_data = RiskGroup.GROUP_5.value
        return RiskClassification(
            risk_group_id=group_data["id"],
            risk_group_name=group_data["name"],
            risk_group_name_en=group_data["name_en"],
            risk_level=group_data["risk_level"],
            days_overdue=days_overdue,
            days_from=group_data["days_from"],
            days_to=group_data["days_to"],
            provision_rate=group_data["provision_rate"],
            color=group_data["color"],
            icon=group_data["icon"],
            classification_date=datetime.utcnow(),
            description=group_data["description_vn"]
        )
    
    @staticmethod
    def classify_by_due_date(due_date: datetime) -> RiskClassification:
        """
        Classify loan based on due date
        
        Args:
            due_date: The due date of the loan
            
        Returns:
            RiskClassification object
        """
        today = datetime.utcnow().date()
        due_date_only = due_date.date() if isinstance(due_date, datetime) else due_date
        
        days_overdue = (today - due_date_only).days
        
        # If not overdue yet
        if days_overdue < 0:
            days_overdue = 0
        
        return RiskClassificationService.classify_by_days_overdue(days_overdue)
    
    @staticmethod
    def classify_by_payment_date(due_date: datetime, last_payment_date: Optional[datetime] = None) -> RiskClassification:
        """
        Classify loan based on due date and last payment date
        
        Args:
            due_date: Original due date
            last_payment_date: Last payment made (if any)
            
        Returns:
            RiskClassification object
        """
        today = datetime.utcnow().date()
        
        # If last payment was made after due date, use last payment date as reference
        if last_payment_date:
            last_payment_only = last_payment_date.date() if isinstance(last_payment_date, datetime) else last_payment_date
            days_overdue = (today - last_payment_only).days
        else:
            due_date_only = due_date.date() if isinstance(due_date, datetime) else due_date
            days_overdue = (today - due_date_only).days
        
        if days_overdue < 0:
            days_overdue = 0
        
        return RiskClassificationService.classify_by_days_overdue(days_overdue)
    
    @staticmethod
    def get_all_risk_groups() -> list[Dict]:
        """Get all risk groups with their details"""
        return [
            {
                "id": group.value["id"],
                "name": group.value["name"],
                "name_en": group.value["name_en"],
                "description": group.value["description"],
                "description_vn": group.value["description_vn"],
                "days_range": f"{group.value['days_from']}-{group.value['days_to']}",
                "risk_level": group.value["risk_level"],
                "provision_rate": f"{group.value['provision_rate']*100:.0f}%",
                "color": group.value["color"]
            }
            for group in RiskGroup
        ]
    
    @staticmethod
    def get_risk_group_by_id(group_id: int) -> Optional[Dict]:
        """Get specific risk group details by ID"""
        return RiskClassificationService.RISK_GROUPS.get(group_id)
    
    @staticmethod
    def calculate_provisions(principal_amount: float, risk_group_id: int) -> Tuple[float, float]:
        """
        Calculate provision amount for a loan based on risk group
        
        Args:
            principal_amount: Outstanding principal amount
            risk_group_id: Risk group ID (1-5)
            
        Returns:
            Tuple of (provision_amount, remaining_amount)
        """
        group = RiskClassificationService.RISK_GROUPS.get(risk_group_id)
        if not group:
            return 0, principal_amount
        
        provision_rate = group["provision_rate"]
        provision_amount = principal_amount * provision_rate
        remaining_amount = principal_amount - provision_amount
        
        return provision_amount, remaining_amount
    
    @staticmethod
    def get_risk_summary() -> Dict:
        """Get summary of all risk groups"""
        summary = {
            "total_groups": len(RiskGroup),
            "groups": []
        }
        
        for group_enum in RiskGroup:
            group_data = group_enum.value
            summary["groups"].append({
                "id": group_data["id"],
                "name": group_data["name"],
                "name_en": group_data["name_en"],
                "risk_level": group_data["risk_level"],
                "days_overdue": f"{group_data['days_from']}-{group_data['days_to']}",
                "provision_rate": f"{group_data['provision_rate']*100:.0f}%"
            })
        
        return summary


if __name__ == "__main__":
    # Test examples
    print("=" * 80)
    print("SBV RISK CLASSIFICATION SYSTEM")
    print("=" * 80)
    print()
    
    # Example 1: Classify by days overdue
    print("Example 1: Loan overdue by 5 days")
    result = RiskClassificationService.classify_by_days_overdue(5)
    print(f"  Risk Group: {result.risk_group_name} (ID: {result.risk_group_id})")
    print(f"  Risk Level: {result.risk_level}")
    print(f"  Provision Rate: {result.provision_rate*100:.0f}%")
    print()
    
    # Example 2: Classify by days overdue
    print("Example 2: Loan overdue by 100 days")
    result = RiskClassificationService.classify_by_days_overdue(100)
    print(f"  Risk Group: {result.risk_group_name} (ID: {result.risk_group_id})")
    print(f"  Risk Level: {result.risk_level}")
    print(f"  Provision Rate: {result.provision_rate*100:.0f}%")
    print()
    
    # Example 3: Calculate provisions
    print("Example 3: Calculate provision for VND 100,000,000 in Group 3")
    provision, remaining = RiskClassificationService.calculate_provisions(100_000_000, 3)
    print(f"  Provision Amount: VND {provision:,.0f}")
    print(f"  Remaining Amount: VND {remaining:,.0f}")
    print()
    
    # Example 4: Get all risk groups
    print("Example 4: All Risk Groups Summary")
    print()
    for group in RiskClassificationService.get_all_risk_groups():
        print(f"  Group {group['id']}: {group['name']}")
        print(f"    English: {group['name_en']}")
        print(f"    Days Overdue: {group['days_range']}")
        print(f"    Risk Level: {group['risk_level']}")
        print(f"    Provision Rate: {group['provision_rate']}")
        print()
