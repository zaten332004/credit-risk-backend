"""
Test Risk Classification Service
"""
import sys
sys.path.insert(0, '../')

from app.services.risk_classification_service import RiskClassificationService

def test_risk_classification():
    """Test risk classification examples"""
    
    print("=" * 80)
    print("RISK CLASSIFICATION SERVICE - TEST EXAMPLES")
    print("=" * 80)
    print()
    
    # Test 1: Classify by days overdue
    print("TEST 1: Classify loan overdue by 5 days")
    print("-" * 80)
    result = RiskClassificationService.classify_by_days_overdue(5)
    print(f"Days Overdue: {result.days_overdue}")
    print(f"Risk Group: {result.risk_group_name} (ID: {result.risk_group_id})")
    print(f"Risk Level: {result.risk_level}")
    print(f"Days Range: {result.days_from}-{result.days_to}")
    print(f"Provision Rate: {result.provision_rate*100:.0f}%")
    print(f"Description: {result.description}")
    print()
    
    # Test 2: Classify by days overdue (higher risk)
    print("TEST 2: Classify loan overdue by 95 days")
    print("-" * 80)
    result = RiskClassificationService.classify_by_days_overdue(95)
    print(f"Days Overdue: {result.days_overdue}")
    print(f"Risk Group: {result.risk_group_name} (ID: {result.risk_group_id})")
    print(f"Risk Level: {result.risk_level}")
    print(f"Provision Rate: {result.provision_rate*100:.0f}%")
    print()
    
    # Test 3: Classify by days overdue (highest risk)
    print("TEST 3: Classify loan overdue by 400 days")
    print("-" * 80)
    result = RiskClassificationService.classify_by_days_overdue(400)
    print(f"Days Overdue: {result.days_overdue}")
    print(f"Risk Group: {result.risk_group_name} (ID: {result.risk_group_id})")
    print(f"Risk Level: {result.risk_level}")
    print(f"Provision Rate: {result.provision_rate*100:.0f}%")
    print()
    
    # Test 4: Calculate provisions
    print("TEST 4: Calculate provision for VND 1,000,000,000")
    print("-" * 80)
    principal = 1_000_000_000
    
    for group_id in range(1, 6):
        provision, remaining = RiskClassificationService.calculate_provisions(principal, group_id)
        group = RiskClassificationService.get_risk_group_by_id(group_id)
        print(f"Group {group_id} ({group['name']}):")
        print(f"  Provision: VND {provision:,.0f}")
        print(f"  Remaining: VND {remaining:,.0f}")
    print()
    
    # Test 5: Display all risk groups
    print("TEST 5: All Risk Groups Summary")
    print("-" * 80)
    groups = RiskClassificationService.get_all_risk_groups()
    
    for group in groups:
        print(f"\nGroup {group['id']}: {group['name']}")
        print(f"  English: {group['name_en']}")
        print(f"  Description: {group['description']}")
        print(f"  Days Overdue: {group['days_range']}")
        print(f"  Risk Level: {group['risk_level']}")
        print(f"  Provision Rate: {group['provision_rate']}")
    print()
    
    # Test 6: Get risk summary
    print("TEST 6: Risk Summary")
    print("-" * 80)
    summary = RiskClassificationService.get_risk_summary()
    print(f"Total Risk Groups: {summary['total_groups']}")
    print()
    for group in summary['groups']:
        print(f"  {group['id']}. {group['name']} - {group['risk_level']}")
    print()
    
    print("=" * 80)
    print("✓ All tests completed successfully!")
    print("=" * 80)

if __name__ == "__main__":
    test_risk_classification()
