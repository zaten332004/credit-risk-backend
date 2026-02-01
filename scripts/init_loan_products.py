"""
Script to insert loan products into database
Based on Vietnamese banking standards
"""
from datetime import datetime
from sqlalchemy import text, inspect
from app.db.session import engine, SessionLocal
from app.db.loan_product_models import LoanProductDB, LoanPricingRuleDB, LoanApprovalLimitDB


def create_loan_product_tables():
    """Create all loan product related tables"""
    print("Creating loan product tables...")
    
    # Import all models to ensure they're registered
    from app.db.loan_product_models import (
        LoanProductDB, LoanPricingRuleDB, 
        LoanApprovalLimitDB, LoanApprovalDB, 
        LoanProductRequirementDB
    )
    # Import existing models to resolve foreign keys
    from app.db.models import LoanFacilityDB, CustomerDB
    
    # Create only loan product related tables (skip those with external FK)
    from app.db.session import Base
    
    # Create tables one by one, skipping those with unresolved FKs
    try:
        # Create core product tables first
        LoanProductDB.__table__.create(bind=engine, checkfirst=True)
        LoanPricingRuleDB.__table__.create(bind=engine, checkfirst=True)
        LoanApprovalLimitDB.__table__.create(bind=engine, checkfirst=True)
        LoanProductRequirementDB.__table__.create(bind=engine, checkfirst=True)
        
        # LoanApprovalDB requires Loan_Facility which may not exist, so skip it
        # It will be created later when Loan_Facility exists
        print("✓ Core product tables created successfully")
        print("  Note: Loan_Approval table will be created when Loan_Facility exists")
    except Exception as e:
        print(f"  Some tables may already exist: {str(e)}")


def insert_loan_products():
    """Insert all 5 loan products"""
    session = SessionLocal()
    
    try:
        products_data = [
            {
                "product_code": "TIN_CHAP_01",
                "product_name": "Vay tín chấp cá nhân",
                "product_name_en": "Unsecured Personal Loan",
                "category": "unsecured",
                "min_amount": 10_000_000,
                "max_amount": 500_000_000,
                "min_term_months": 12,
                "max_term_months": 84,
                "min_interest_rate": 12.0,
                "max_interest_rate": 24.0,
                "typical_interest_rate": 18.0,
                "promotion_interest_rate": None,
                "collateral_required": False,
                "collateral_type": None,
                "ltv_ratio": None,
                "max_dti_ratio": 50.0,
                "min_credit_score": 600,
                "processing_time_days": 3,
                "approval_authority": "branch_manager",
                "description": "Vay không cần tài sản đảm bảo, dựa trên lương/thu nhập ổn định. Hạn mức 10-500M VND, thời hạn 1-7 năm.",
                "eligible_customers": "individual,small_business",
                "required_documents": "ID,salary_slip,employment_letter,bank_statement",
                "risk_factors": "income_stability,credit_history,debt_burden"
            },
            {
                "product_code": "TIN_CHAP_02",
                "product_name": "Vay kinh doanh tín chấp",
                "product_name_en": "Unsecured Business Loan",
                "category": "unsecured",
                "min_amount": 50_000_000,
                "max_amount": 500_000_000,
                "min_term_months": 6,
                "max_term_months": 84,
                "min_interest_rate": 10.0,
                "max_interest_rate": 18.0,
                "typical_interest_rate": 14.0,
                "promotion_interest_rate": None,
                "collateral_required": False,
                "collateral_type": None,
                "ltv_ratio": None,
                "max_dti_ratio": 60.0,
                "min_credit_score": 550,
                "processing_time_days": 5,
                "approval_authority": "credit_committee",
                "description": "Vay tín chấp cho hộ kinh doanh/doanh nghiệp nhỏ, dựa thu nhập kinh doanh. Hạn mức 50-500M VND.",
                "eligible_customers": "business,self_employed",
                "required_documents": "ID,business_registration,tax_return,bank_statement,business_plan",
                "risk_factors": "revenue_stability,business_history,market_conditions"
            },
            {
                "product_code": "THE_CHAP_01",
                "product_name": "Vay thế chấp sổ đỏ/sổ hồng",
                "product_name_en": "Secured Real Estate Mortgage",
                "category": "secured",
                "min_amount": 100_000_000,
                "max_amount": 5_000_000_000,
                "min_term_months": 60,
                "max_term_months": 420,
                "min_interest_rate": 6.0,
                "max_interest_rate": 12.0,
                "typical_interest_rate": 8.5,
                "promotion_interest_rate": 5.5,
                "collateral_required": True,
                "collateral_type": "real_estate",
                "ltv_ratio": 85.0,
                "max_dti_ratio": 50.0,
                "min_credit_score": 650,
                "processing_time_days": 15,
                "approval_authority": "credit_committee",
                "description": "Vay thế chấp bằng sổ đỏ hoặc sổ hồng. Hạn mức 70-90% giá trị bất động sản, thời hạn 5-35 năm, lãi suất 6-12%.",
                "eligible_customers": "individual,business",
                "required_documents": "ID,property_deed,property_valuation,marriage_certificate,bank_statement",
                "risk_factors": "property_value,location,customer_creditworthiness"
            },
            {
                "product_code": "THE_CHAP_02",
                "product_name": "Vay thế chấp ô tô",
                "product_name_en": "Secured Vehicle Loan",
                "category": "secured",
                "min_amount": 50_000_000,
                "max_amount": 2_000_000_000,
                "min_term_months": 12,
                "max_term_months": 84,
                "min_interest_rate": 7.0,
                "max_interest_rate": 13.0,
                "typical_interest_rate": 10.0,
                "promotion_interest_rate": 6.5,
                "collateral_required": True,
                "collateral_type": "vehicle",
                "ltv_ratio": 80.0,
                "max_dti_ratio": 50.0,
                "min_credit_score": 600,
                "processing_time_days": 7,
                "approval_authority": "branch_manager",
                "description": "Vay thế chấp bằng ô tô hoặc xe máy. Hạn mức 70-80% giá trị xe, thời hạn 1-7 năm, lãi suất 7-13%.",
                "eligible_customers": "individual,business",
                "required_documents": "ID,vehicle_registration,vehicle_valuation,insurance,bank_statement",
                "risk_factors": "vehicle_condition,vehicle_age,resale_value"
            },
            {
                "product_code": "THE_CHAP_03",
                "product_name": "Vay thế chấp sổ tiết kiệm",
                "product_name_en": "Secured Savings Loan",
                "category": "secured",
                "min_amount": 10_000_000,
                "max_amount": 1_000_000_000,
                "min_term_months": 3,
                "max_term_months": 60,
                "min_interest_rate": 4.0,
                "max_interest_rate": 8.0,
                "typical_interest_rate": 6.0,
                "promotion_interest_rate": None,
                "collateral_required": True,
                "collateral_type": "savings_account",
                "ltv_ratio": 95.0,
                "max_dti_ratio": 50.0,
                "min_credit_score": 500,
                "processing_time_days": 1,
                "approval_authority": "branch_manager",
                "description": "Vay thế chấp bằng sổ tiết kiệm. Hạn mức 90-100% giá trị sổ, lãi suất 4-8%, phê duyệt nhanh nhất (1 ngày).",
                "eligible_customers": "individual",
                "required_documents": "ID,savings_book,bank_statement",
                "risk_factors": "savings_stability"
            }
        ]
        
        # Check if products already exist
        existing = session.query(LoanProductDB).count()
        if existing > 0:
            print(f"⚠ Found {existing} existing products. Skipping insertion.")
            return
        
        # Insert products
        for product_data in products_data:
            product = LoanProductDB(**product_data)
            session.add(product)
        
        session.commit()
        print(f"✓ Inserted {len(products_data)} loan products successfully")
        
        # Display inserted products
        products = session.query(LoanProductDB).all()
        print("\nInserted Loan Products:")
        print("-" * 100)
        print(f"{'ID':<3} {'Code':<15} {'Product Name':<40} {'Category':<12} {'Rate':<10}")
        print("-" * 100)
        for p in products:
            rate_range = f"{p.min_interest_rate:.1f}%-{p.max_interest_rate:.1f}%"
            print(f"{p.product_id:<3} {p.product_code:<15} {p.product_name:<40} {p.category:<12} {rate_range:<10}")
        
    except Exception as e:
        session.rollback()
        print(f"✗ Error inserting products: {str(e)}")
        raise
    finally:
        session.close()


def insert_pricing_rules():
    """Insert pricing rules for different customer segments"""
    session = SessionLocal()
    
    try:
        # Get all products
        products = session.query(LoanProductDB).all()
        
        if not products:
            print("⚠ No products found. Please insert products first.")
            return
        
        pricing_data = []
        
        # Unsecured personal loan pricing by credit score
        unsecured_personal = next((p for p in products if p.product_code == "TIN_CHAP_01"), None)
        if unsecured_personal:
            pricing_data.extend([
                {
                    "product_id": unsecured_personal.product_id,
                    "customer_type": "individual",
                    "credit_score_min": 700,
                    "credit_score_max": 999,
                    "base_interest_rate": 12.0,
                    "risk_premium": 2.0,
                    "final_interest_rate": 14.0,
                    "loyalty_discount": 1.0,
                    "early_repayment_discount": 0.5
                },
                {
                    "product_id": unsecured_personal.product_id,
                    "customer_type": "individual",
                    "credit_score_min": 650,
                    "credit_score_max": 699,
                    "base_interest_rate": 15.0,
                    "risk_premium": 3.0,
                    "final_interest_rate": 18.0,
                    "loyalty_discount": 0.5,
                    "early_repayment_discount": 0.3
                },
                {
                    "product_id": unsecured_personal.product_id,
                    "customer_type": "individual",
                    "credit_score_min": 600,
                    "credit_score_max": 649,
                    "base_interest_rate": 18.0,
                    "risk_premium": 6.0,
                    "final_interest_rate": 24.0,
                    "loyalty_discount": 0.0,
                    "early_repayment_discount": 0.0
                }
            ])
        
        # Unsecured business loan pricing
        unsecured_business = next((p for p in products if p.product_code == "TIN_CHAP_02"), None)
        if unsecured_business:
            pricing_data.extend([
                {
                    "product_id": unsecured_business.product_id,
                    "customer_type": "business",
                    "credit_score_min": 700,
                    "credit_score_max": 999,
                    "base_interest_rate": 10.0,
                    "risk_premium": 2.0,
                    "final_interest_rate": 12.0,
                    "loyalty_discount": 1.0,
                    "early_repayment_discount": 0.5
                },
                {
                    "product_id": unsecured_business.product_id,
                    "customer_type": "business",
                    "credit_score_min": 600,
                    "credit_score_max": 699,
                    "base_interest_rate": 12.0,
                    "risk_premium": 4.0,
                    "final_interest_rate": 16.0,
                    "loyalty_discount": 0.5,
                    "early_repayment_discount": 0.0
                }
            ])
        
        # Secured real estate mortgage pricing
        secured_realestate = next((p for p in products if p.product_code == "THE_CHAP_01"), None)
        if secured_realestate:
            pricing_data.extend([
                {
                    "product_id": secured_realestate.product_id,
                    "customer_type": "individual",
                    "credit_score_min": 700,
                    "credit_score_max": 999,
                    "base_interest_rate": 6.0,
                    "risk_premium": 1.0,
                    "final_interest_rate": 7.0,
                    "loyalty_discount": 1.5,
                    "early_repayment_discount": 1.0
                },
                {
                    "product_id": secured_realestate.product_id,
                    "customer_type": "individual",
                    "credit_score_min": 650,
                    "credit_score_max": 699,
                    "base_interest_rate": 7.5,
                    "risk_premium": 1.5,
                    "final_interest_rate": 9.0,
                    "loyalty_discount": 1.0,
                    "early_repayment_discount": 0.5
                }
            ])
        
        # Check if pricing rules already exist
        existing = session.query(LoanPricingRuleDB).count()
        if existing > 0:
            print(f"⚠ Found {existing} existing pricing rules. Skipping insertion.")
            return
        
        # Insert pricing rules
        for rule_data in pricing_data:
            rule = LoanPricingRuleDB(**rule_data)
            session.add(rule)
        
        session.commit()
        print(f"✓ Inserted {len(pricing_data)} pricing rules successfully")
        
    except Exception as e:
        session.rollback()
        print(f"✗ Error inserting pricing rules: {str(e)}")
        raise
    finally:
        session.close()


def insert_approval_limits():
    """Insert approval limits by authority level"""
    session = SessionLocal()
    
    try:
        # Get all products
        products = session.query(LoanProductDB).all()
        
        if not products:
            print("⚠ No products found. Please insert products first.")
            return
        
        approval_limits_data = []
        
        for product in products:
            # Branch manager can approve up to product max or 500M
            branch_max = min(int(product.max_amount), 500_000_000)
            
            approval_limits_data.extend([
                {
                    "product_id": product.product_id,
                    "approval_level": "branch_manager",
                    "min_approval_amount": int(product.min_amount),
                    "max_approval_amount": branch_max,
                    "min_customer_credit_score": product.min_credit_score,
                    "max_dti_ratio": product.max_dti_ratio,
                    "max_processing_days": product.processing_time_days,
                    "required_documents": ""
                },
                {
                    "product_id": product.product_id,
                    "approval_level": "credit_committee",
                    "min_approval_amount": branch_max + 1,
                    "max_approval_amount": int(product.max_amount),
                    "min_customer_credit_score": product.min_credit_score + 50,
                    "max_dti_ratio": max(product.max_dti_ratio - 10, 40),
                    "max_processing_days": product.processing_time_days + 5,
                    "required_documents": "Full credit assessment, valuation report"
                }
            ])
        
        # Check if limits already exist
        existing = session.query(LoanApprovalLimitDB).count()
        if existing > 0:
            print(f"⚠ Found {existing} existing approval limits. Skipping insertion.")
            return
        
        # Insert approval limits
        for limit_data in approval_limits_data:
            limit = LoanApprovalLimitDB(**limit_data)
            session.add(limit)
        
        session.commit()
        print(f"✓ Inserted {len(approval_limits_data)} approval limits successfully")
        
    except Exception as e:
        session.rollback()
        print(f"✗ Error inserting approval limits: {str(e)}")
        raise
    finally:
        session.close()


def display_product_summary():
    """Display summary of all loan products"""
    session = SessionLocal()
    
    try:
        products = session.query(LoanProductDB).all()
        
        if not products:
            print("No products found")
            return
        
        print("\n" + "=" * 120)
        print("LOAN PRODUCTS SUMMARY")
        print("=" * 120)
        
        for product in products:
            print(f"\n{product.product_id}. {product.product_name} ({product.product_code})")
            print(f"   Category: {product.category}")
            print(f"   Amount: VND {product.min_amount:,} - {product.max_amount:,}")
            print(f"   Term: {product.min_term_months} - {product.max_term_months} months")
            print(f"   Interest Rate: {product.min_interest_rate}% - {product.max_interest_rate}%")
            print(f"   Typical Rate: {product.typical_interest_rate}%")
            if product.promotion_interest_rate:
                print(f"   Promotional Rate: {product.promotion_interest_rate}%")
            print(f"   Collateral Required: {'Yes' if product.collateral_required else 'No'}")
            if product.collateral_required:
                print(f"   Collateral Type: {product.collateral_type} (LTV: {product.ltv_ratio}%)")
            print(f"   Max DTI: {product.max_dti_ratio}%")
            print(f"   Min Credit Score: {product.min_credit_score}")
            print(f"   Processing Time: {product.processing_time_days} days")
            print(f"   Approval Authority: {product.approval_authority}")
            print(f"   Description: {product.description}")
        
        print("\n" + "=" * 120)
        
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 120)
    print("LOAN PRODUCT DATABASE INITIALIZATION")
    print("=" * 120)
    print()
    
    try:
        # Create tables
        create_loan_product_tables()
        print()
        
        # Insert products
        insert_loan_products()
        print()
        
        # Insert pricing rules
        insert_pricing_rules()
        print()
        
        # Insert approval limits
        insert_approval_limits()
        print()
        
        # Display summary
        display_product_summary()
        
        print("\n✓ Database initialization completed successfully!")
        print("=" * 120)
        
    except Exception as e:
        print(f"\n✗ Error during initialization: {str(e)}")
        raise
