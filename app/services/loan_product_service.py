"""
Loan Product Types Management System
Based on Vietnamese Banking Standards
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from datetime import datetime


class LoanProductType(Enum):
    """Loan product types"""
    
    UNSECURED_PERSONAL = {
        "id": 1,
        "name": "Vay tín chấp cá nhân",
        "name_en": "Unsecured Personal Loan",
        "description": "Vay không cần tài sản đảm bảo, dựa trên lương/thu nhập ổn định",
        "category": "unsecured",
        "min_amount": 10_000_000,  # 10M VND
        "max_amount": 500_000_000,  # 500M VND
        "typical_max_amount": 900_000_000,  # Some banks up to 1B
        "min_term_months": 12,
        "max_term_months": 84,  # 7 years
        "typical_term_months": 36,  # 3 years
        "min_interest_rate": 12.0,
        "max_interest_rate": 24.0,
        "typical_interest_rate": 18.0,
        "max_loan_to_income_ratio": 15,  # Max 15x monthly income
        "collateral_required": False,
        "eligible_customers": ["individual", "small_business"],
        "required_documents": ["ID", "salary_slip", "employment_letter", "bank_statement"],
        "risk_factors": ["income_stability", "credit_history", "debt_burden"],
        "max_dti_ratio": 50,  # Max 50% DTI
        "min_credit_score": 600,
        "processing_time_days": 3,
        "approval_authority": "branch_manager"
    }
    
    UNSECURED_BUSINESS = {
        "id": 2,
        "name": "Vay kinh doanh tín chấp",
        "name_en": "Unsecured Business Loan",
        "description": "Vay tín chấp cho hộ kinh doanh/doanh nghiệp nhỏ, dựa thu nhập kinh doanh",
        "category": "unsecured",
        "min_amount": 50_000_000,  # 50M VND
        "max_amount": 500_000_000,  # 500M VND
        "typical_max_amount": 1_000_000_000,  # Up to 1B for good customers
        "min_term_months": 6,
        "max_term_months": 84,  # 7 years
        "typical_term_months": 24,  # 2 years
        "min_interest_rate": 10.0,
        "max_interest_rate": 18.0,
        "typical_interest_rate": 14.0,
        "max_loan_to_revenue_ratio": 2,  # Max 2x annual revenue
        "collateral_required": False,
        "eligible_customers": ["business", "self_employed"],
        "required_documents": ["ID", "business_registration", "tax_return", "bank_statement", "business_plan"],
        "risk_factors": ["revenue_stability", "business_history", "market_conditions"],
        "max_dti_ratio": 60,  # Max 60% DTI for business
        "min_credit_score": 550,
        "processing_time_days": 5,
        "approval_authority": "credit_committee"
    }
    
    SECURED_MORTGAGE = {
        "id": 3,
        "name": "Vay thế chấp sổ đỏ/sổ hồng",
        "name_en": "Secured Real Estate Mortgage",
        "description": "Vay thế chấp bằng sổ đỏ hoặc sổ hồng, có thể dùng để mua nhà, sửa nhà, kinh doanh",
        "category": "secured",
        "min_amount": 100_000_000,  # 100M VND
        "max_amount": 5_000_000_000,  # 5B VND
        "typical_max_amount": 10_000_000_000,  # Up to 10B for premium customers
        "min_term_months": 60,  # 5 years
        "max_term_months": 420,  # 35 years
        "typical_term_months": 240,  # 20 years
        "min_interest_rate": 6.0,
        "max_interest_rate": 12.0,
        "typical_interest_rate": 8.5,
        "promotion_interest_rate": 5.5,  # Promotional rate 5.5-8%
        "ltv_ratio": 0.85,  # Loan-to-Value: 70-90% of property value
        "collateral_required": True,
        "collateral_type": "real_estate",
        "eligible_customers": ["individual", "business"],
        "required_documents": ["ID", "property_deed", "property_valuation", "marriage_certificate", "bank_statement"],
        "risk_factors": ["property_value", "location", "customer_creditworthiness"],
        "max_dti_ratio": 50,
        "min_credit_score": 650,
        "processing_time_days": 15,
        "approval_authority": "credit_committee"
    }
    
    SECURED_VEHICLE = {
        "id": 4,
        "name": "Vay thế chấp ô tô",
        "name_en": "Secured Vehicle Loan",
        "description": "Vay thế chấp bằng ô tô hoặc xe máy (đăng ký lần đầu hoặc xe cũ)",
        "category": "secured",
        "min_amount": 50_000_000,  # 50M VND
        "max_amount": 2_000_000_000,  # 2B VND
        "typical_max_amount": 3_000_000_000,  # Up to 3B
        "min_term_months": 12,
        "max_term_months": 84,  # 7 years
        "typical_term_months": 48,  # 4 years
        "min_interest_rate": 7.0,
        "max_interest_rate": 13.0,
        "typical_interest_rate": 10.0,
        "promotion_interest_rate": 6.5,  # Promotional rate 6.5-7.5%
        "ltv_ratio": 0.80,  # LTV: 70-80% of vehicle value
        "collateral_required": True,
        "collateral_type": "vehicle",
        "eligible_customers": ["individual", "business"],
        "required_documents": ["ID", "vehicle_registration", "vehicle_valuation", "insurance", "bank_statement"],
        "risk_factors": ["vehicle_condition", "vehicle_age", "resale_value"],
        "max_dti_ratio": 50,
        "min_credit_score": 600,
        "processing_time_days": 7,
        "approval_authority": "branch_manager"
    }
    
    SECURED_SAVINGS = {
        "id": 5,
        "name": "Vay thế chấp sổ tiết kiệm",
        "name_en": "Secured Savings Loan",
        "description": "Vay thế chấp bằng sổ tiết kiệm (hạn mức = 90-100% sổ tiết kiệm)",
        "category": "secured",
        "min_amount": 10_000_000,  # 10M VND
        "max_amount": 1_000_000_000,  # 1B VND
        "typical_max_amount": 500_000_000,
        "min_term_months": 3,
        "max_term_months": 60,  # Up to 5 years
        "typical_term_months": 12,
        "min_interest_rate": 4.0,
        "max_interest_rate": 8.0,
        "typical_interest_rate": 6.0,
        "ltv_ratio": 0.95,  # LTV: 90-100% of savings value
        "collateral_required": True,
        "collateral_type": "savings_account",
        "eligible_customers": ["individual"],
        "required_documents": ["ID", "savings_book", "bank_statement"],
        "risk_factors": ["savings_stability"],
        "max_dti_ratio": 50,
        "min_credit_score": 500,  # Lowest requirement
        "processing_time_days": 1,  # Fastest
        "approval_authority": "branch_manager"
    }


@dataclass
class LoanProduct:
    """Loan product details"""
    product_id: int
    product_name: str
    product_name_en: str
    category: str  # unsecured, secured
    min_amount: float
    max_amount: float
    min_term_months: int
    max_term_months: int
    min_interest_rate: float
    max_interest_rate: float
    ltv_ratio: Optional[float]  # For secured loans
    collateral_required: bool
    collateral_type: Optional[str]
    max_dti_ratio: float
    min_credit_score: int
    processing_time_days: int


@dataclass
class LoanApprovalCriteria:
    """Criteria for loan approval"""
    product_id: int
    product_name: str
    
    # Amount criteria
    min_loan_amount: float
    max_loan_amount: float
    max_loan_to_income: Optional[float]  # For personal
    max_loan_to_revenue: Optional[float]  # For business
    
    # Customer criteria
    min_credit_score: int
    max_dti_ratio: float
    min_monthly_income: float
    
    # Collateral criteria (if applicable)
    collateral_required: bool
    min_ltv_ratio: float
    max_ltv_ratio: float
    
    # Term criteria
    min_term_months: int
    max_term_months: int
    
    # Rate criteria
    min_rate: float
    max_rate: float


class LoanProductService:
    """Service for managing loan products"""
    
    PRODUCTS = {
        product.value["id"]: product.value
        for product in LoanProductType
    }
    
    @staticmethod
    def get_all_products() -> List[Dict]:
        """Get all loan products"""
        return [
            {
                "id": product.value["id"],
                "name": product.value["name"],
                "name_en": product.value["name_en"],
                "category": product.value["category"],
                "min_amount": f"VND {product.value['min_amount']:,}",
                "max_amount": f"VND {product.value['max_amount']:,}",
                "interest_rate": f"{product.value['min_interest_rate']:.1f}%-{product.value['max_interest_rate']:.1f}%",
                "term": f"{product.value['min_term_months']}-{product.value['max_term_months']} tháng"
            }
            for product in LoanProductType
        ]
    
    @staticmethod
    def get_product_by_id(product_id: int) -> Optional[Dict]:
        """Get specific product details"""
        return LoanProductService.PRODUCTS.get(product_id)
    
    @staticmethod
    def recommend_product_for_customer(
        age: int,
        annual_income: float,
        monthly_income: float,
        credit_score: int,
        customer_type: str,  # individual, business, self_employed
        collateral_available: Optional[str] = None,  # real_estate, vehicle, savings
        dti_ratio: float = 0
    ) -> List[Dict]:
        """
        Recommend suitable loan products for customer
        """
        recommendations = []
        
        for product_enum in LoanProductType:
            product = product_enum.value
            product_id = product["id"]
            
            # Check eligibility
            eligible = True
            reasons = []
            
            # 1. Check customer type
            if customer_type.lower() not in product["eligible_customers"]:
                eligible = False
                reasons.append(f"Customer type '{customer_type}' not eligible for {product['name']}")
            
            # 2. Check credit score
            if credit_score < product["min_credit_score"]:
                eligible = False
                reasons.append(f"Credit score {credit_score} below minimum {product['min_credit_score']}")
            
            # 3. Check DTI ratio
            if dti_ratio > product["max_dti_ratio"]:
                eligible = False
                reasons.append(f"DTI ratio {dti_ratio:.1f}% exceeds maximum {product['max_dti_ratio']}%")
            
            # 4. Check collateral requirement
            if product["collateral_required"] and not collateral_available:
                eligible = False
                reasons.append(f"Collateral '{product['collateral_type']}' required but not available")
            
            # 5. Check if collateral type matches
            if collateral_available and product["collateral_required"]:
                if collateral_available != product["collateral_type"]:
                    eligible = False
                    reasons.append(f"Collateral type '{collateral_available}' not suitable for {product['name']}")
            
            if eligible:
                # Calculate maximum loan amount
                max_by_income = float('inf')
                if "max_loan_to_income_ratio" in product:
                    max_by_income = monthly_income * product["max_loan_to_income_ratio"]
                
                max_by_revenue = float('inf')
                if "max_loan_to_revenue_ratio" in product:
                    max_by_revenue = annual_income * product["max_loan_to_revenue_ratio"]
                
                max_loan = min(
                    product["max_amount"],
                    max_by_income,
                    max_by_revenue
                )
                
                recommendations.append({
                    "product_id": product_id,
                    "product_name": product["name"],
                    "product_name_en": product["name_en"],
                    "category": product["category"],
                    "min_amount": product["min_amount"],
                    "max_amount": int(max_loan),
                    "interest_rate_range": f"{product['min_interest_rate']:.1f}%-{product['max_interest_rate']:.1f}%",
                    "term_range": f"{product['min_term_months']}-{product['max_term_months']} tháng",
                    "processing_time": f"{product['processing_time_days']} ngày",
                    "reason": "Eligible"
                })
        
        return recommendations
    
    @staticmethod
    def calculate_max_loan_amount(
        product_id: int,
        monthly_income: float,
        annual_income: float,
        collateral_value: Optional[float] = None
    ) -> Tuple[float, str]:
        """
        Calculate maximum loan amount for a specific product
        """
        product = LoanProductService.PRODUCTS.get(product_id)
        if not product:
            return 0, "Product not found"
        
        max_amount = product["max_amount"]
        reason = "Based on product maximum"
        
        # For unsecured loans, limit by income
        if not product["collateral_required"]:
            if "max_loan_to_income_ratio" in product:
                income_based_max = monthly_income * product["max_loan_to_income_ratio"]
                if income_based_max < max_amount:
                    max_amount = income_based_max
                    reason = f"Limited by {product['max_loan_to_income_ratio']}x monthly income"
            
            if "max_loan_to_revenue_ratio" in product:
                revenue_based_max = annual_income * product["max_loan_to_revenue_ratio"]
                if revenue_based_max < max_amount:
                    max_amount = revenue_based_max
                    reason = f"Limited by {product['max_loan_to_revenue_ratio']}x annual revenue"
        
        # For secured loans, limit by collateral value
        else:
            if collateral_value:
                ltv = product.get("ltv_ratio", 0.8)
                collateral_based_max = collateral_value * ltv
                if collateral_based_max < max_amount:
                    max_amount = collateral_based_max
                    reason = f"Limited by {ltv*100:.0f}% LTV of collateral value"
        
        return max_amount, reason
    
    @staticmethod
    def calculate_monthly_payment(
        loan_amount: float,
        annual_interest_rate: float,
        term_months: int
    ) -> float:
        """
        Calculate monthly payment using standard amortization formula
        Payment = P * [r(1+r)^n] / [(1+r)^n - 1]
        where P = principal, r = monthly rate, n = number of months
        """
        monthly_rate = annual_interest_rate / 100 / 12
        
        if monthly_rate == 0:
            return loan_amount / term_months
        
        numerator = loan_amount * monthly_rate * ((1 + monthly_rate) ** term_months)
        denominator = ((1 + monthly_rate) ** term_months) - 1
        
        return numerator / denominator
    
    @staticmethod
    def calculate_total_interest(
        loan_amount: float,
        annual_interest_rate: float,
        term_months: int
    ) -> float:
        """Calculate total interest paid"""
        monthly_payment = LoanProductService.calculate_monthly_payment(
            loan_amount,
            annual_interest_rate,
            term_months
        )
        total_paid = monthly_payment * term_months
        return total_paid - loan_amount
    
    @staticmethod
    def generate_loan_scenario(
        product_id: int,
        loan_amount: float,
        annual_interest_rate: float,
        term_months: int
    ) -> Dict:
        """Generate detailed loan scenario"""
        product = LoanProductService.PRODUCTS.get(product_id)
        if not product:
            return {}
        
        monthly_payment = LoanProductService.calculate_monthly_payment(
            loan_amount,
            annual_interest_rate,
            term_months
        )
        
        total_interest = LoanProductService.calculate_total_interest(
            loan_amount,
            annual_interest_rate,
            term_months
        )
        
        total_amount = loan_amount + total_interest
        
        return {
            "product": product["name"],
            "loan_amount": loan_amount,
            "interest_rate": annual_interest_rate,
            "term_months": term_months,
            "monthly_payment": monthly_payment,
            "total_interest": total_interest,
            "total_amount_paid": total_amount,
            "daily_interest": (loan_amount * annual_interest_rate / 100) / 365
        }
    
    @staticmethod
    def compare_products(loan_amount: float, term_months: int) -> List[Dict]:
        """
        Compare all products for given loan amount and term
        """
        comparisons = []
        
        for product_enum in LoanProductType:
            product = product_enum.value
            
            # Check if product supports this amount and term
            if (loan_amount < product["min_amount"] or 
                loan_amount > product["max_amount"] or
                term_months < product["min_term_months"] or
                term_months > product["max_term_months"]):
                continue
            
            # Calculate with typical interest rate
            scenario = LoanProductService.generate_loan_scenario(
                product["id"],
                loan_amount,
                product["typical_interest_rate"],
                term_months
            )
            
            comparisons.append({
                "product_id": product["id"],
                "product_name": product["name"],
                "category": product["category"],
                "interest_rate": product["typical_interest_rate"],
                "monthly_payment": scenario["monthly_payment"],
                "total_interest": scenario["total_interest"],
                "collateral_required": product["collateral_required"]
            })
        
        # Sort by monthly payment (lowest first)
        return sorted(comparisons, key=lambda x: x["monthly_payment"])


if __name__ == "__main__":
    # Test examples
    print("=" * 90)
    print("LOAN PRODUCT MANAGEMENT SYSTEM")
    print("=" * 90)
    print()
    
    # Example 1: List all products
    print("EXAMPLE 1: All Available Loan Products")
    print("-" * 90)
    products = LoanProductService.get_all_products()
    for product in products:
        print(f"{product['id']}. {product['name']}")
        print(f"   Amount: {product['min_amount']} - {product['max_amount']}")
        print(f"   Rate: {product['interest_rate']}")
        print(f"   Term: {product['term']}")
        print()
    
    # Example 2: Recommend products for customer
    print("EXAMPLE 2: Product Recommendation for Customer")
    print("-" * 90)
    recommendations = LoanProductService.recommend_product_for_customer(
        age=35,
        annual_income=500_000_000,
        monthly_income=40_000_000,
        credit_score=700,
        customer_type="individual",
        collateral_available="real_estate",
        dti_ratio=25
    )
    print(f"Found {len(recommendations)} suitable products:")
    for rec in recommendations:
        print(f"\n✓ {rec['product_name']}")
        print(f"  Max Loan: VND {rec['max_amount']:,.0f}")
        print(f"  Rate: {rec['interest_rate_range']}")
        print(f"  Processing: {rec['processing_time']}")
    print()
    
    # Example 3: Calculate maximum loan
    print("EXAMPLE 3: Maximum Loan Amount Calculation")
    print("-" * 90)
    max_loan, reason = LoanProductService.calculate_max_loan_amount(
        product_id=1,  # Unsecured Personal
        monthly_income=40_000_000,
        annual_income=500_000_000
    )
    print(f"Product: Unsecured Personal Loan")
    print(f"Max Loan: VND {max_loan:,.0f}")
    print(f"Reason: {reason}")
    print()
    
    # Example 4: Loan scenario
    print("EXAMPLE 4: Loan Scenario (Unsecured Personal Loan)")
    print("-" * 90)
    scenario = LoanProductService.generate_loan_scenario(
        product_id=1,
        loan_amount=300_000_000,
        annual_interest_rate=18,
        term_months=36
    )
    print(f"Loan Amount: VND {scenario['loan_amount']:,.0f}")
    print(f"Interest Rate: {scenario['interest_rate']}% per annum")
    print(f"Term: {scenario['term_months']} months")
    print(f"Monthly Payment: VND {scenario['monthly_payment']:,.0f}")
    print(f"Total Interest: VND {scenario['total_interest']:,.0f}")
    print(f"Total Amount Paid: VND {scenario['total_amount_paid']:,.0f}")
    print()
    
    # Example 5: Compare products
    print("EXAMPLE 5: Product Comparison for VND 200M, 24 months")
    print("-" * 90)
    comparisons = LoanProductService.compare_products(
        loan_amount=200_000_000,
        term_months=24
    )
    print(f"{'Product':<35} {'Rate':<8} {'Monthly':<20} {'Total Interest':<20}")
    print("-" * 90)
    for comp in comparisons:
        print(f"{comp['product_name']:<35} {comp['interest_rate']:.1f}%   "
              f"VND {comp['monthly_payment']:>15,.0f}  VND {comp['total_interest']:>15,.0f}")
    print()
    
    print("=" * 90)
    print("✓ All test cases completed successfully!")
    print("=" * 90)
