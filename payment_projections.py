"""
Payment Projections Calculator - Clean Python Implementation
Handles all payment frequencies correctly without JavaScript complexity
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import calendar

@dataclass
class PaymentProjection:
    """Single payment projection entry"""
    month_number: int
    date: datetime
    payment_amount: float
    payment_number: int
    total_payments: int
    frequency: str
    is_final_payment: bool
    remaining_balance: float
    plan_id: str
    class_field: Optional[str] = None

@dataclass
class CustomerProjection:
    """Complete customer projection timeline"""
    customer_name: str
    total_monthly_payment: float
    total_owed: float
    completion_month: int
    plan_count: int
    timeline: List[Dict]  # Monthly timeline with payment details

class PaymentProjectionCalculator:
    """Clean Python-based payment projection calculator"""
    
    def __init__(self):
        self.frequency_months = {
            'monthly': 1,
            'quarterly': 3, 
            'bimonthly': 2,
            'undefined': 1
        }
    
    def calculate_customer_projections(self, customers_data: Dict, months_ahead: int = 12, scenario: str = 'current') -> List[CustomerProjection]:
        """
        Calculate payment projections for all customers
        
        Args:
            customers_data: Customer data from enhanced_main.py results
            months_ahead: Number of months to project
            scenario: 'current' or 'restart' (restart ignores months_behind)
        """
        projections = []
        
        # Extract customer data - adapt to your data structure
        if 'all_customers' in customers_data:
            customers = customers_data['all_customers']
        else:
            customers = customers_data
            
        for customer_name, customer in customers.items():
            projection = self._calculate_single_customer_projection(
                customer, months_ahead, scenario
            )
            if projection:
                projections.append(projection)
        
        # Sort by total monthly payment (highest first)
        projections.sort(key=lambda x: x.total_monthly_payment, reverse=True)
        return projections
    
    def _calculate_single_customer_projection(self, customer, months_ahead: int, scenario: str) -> Optional[CustomerProjection]:
        """Calculate projection for a single customer with all their payment plans"""
        
        # Get valid payment plans (ones with payment amounts)
        valid_plans = []
        for plan in customer.payment_plans:
            if not plan.has_issues and plan.monthly_amount > 0 and plan.total_open > 0:
                valid_plans.append(plan)
        
        if not valid_plans:
            return None
        
        # Generate monthly timeline
        timeline = []
        total_monthly = sum(plan.monthly_amount for plan in valid_plans)
        total_owed = sum(plan.total_open for plan in valid_plans)
        max_completion_month = 0
        
        for month in range(1, months_ahead + 1):
            month_date = datetime.now() + relativedelta(months=month)
            month_date = month_date.replace(day=calendar.monthrange(month_date.year, month_date.month)[1])
            
            monthly_payment = 0
            active_plans = 0
            plan_details = []
            
            for plan in valid_plans:
                payment_info = self._calculate_plan_payment_for_month(
                    plan, month, scenario
                )
                
                if payment_info and payment_info['payment_amount'] > 0:
                    monthly_payment += payment_info['payment_amount']
                    active_plans += 1
                    plan_details.append(payment_info)
                    
                    # Track completion month
                    completion_month = self._get_plan_completion_month(plan, scenario)
                    max_completion_month = max(max_completion_month, completion_month)
            
            timeline.append({
                'month': month,
                'date': month_date.isoformat(),
                'monthly_payment': round(monthly_payment, 2),
                'active_plans': active_plans,
                'plan_details': plan_details
            })
        
        return CustomerProjection(
            customer_name=customer.customer_name,
            total_monthly_payment=total_monthly,
            total_owed=total_owed,
            completion_month=max_completion_month,
            plan_count=len(valid_plans),
            timeline=timeline
        )
    
    def _calculate_plan_payment_for_month(self, plan, month: int, scenario: str) -> Optional[Dict]:
        """
        FIXED: Calculate if a payment is due for a specific plan in a specific month
        This is the core logic that was broken in JavaScript
        """
        
        # Get payment frequency in months
        frequency_months = self._get_frequency_months(plan.frequency.value)
        
        # Calculate months behind (0 if restart scenario)
        months_behind = 0 if scenario == 'restart' else getattr(plan, 'months_behind', 0)
        
        # FIXED LOGIC: Check if this month is a payment month
        # For quarterly: payments should be in months 1, 4, 7, 10, 13...
        # For monthly: payments should be in months 1, 2, 3, 4, 5...
        # For bimonthly: payments should be in months 1, 3, 5, 7, 9...
        
        # Start payments from month 1, then every frequency_months
        is_payment_month = ((month - 1) % frequency_months) == 0
        
        if not is_payment_month:
            return None
        
        # FIXED: Calculate which payment number this is (starting from 1)
        payment_number = ((month - 1) // frequency_months) + 1
        
        # Calculate total payments needed
        total_payments_needed = self._calculate_total_payments_needed(plan)
        
        # Check if we've completed all payments
        if payment_number > total_payments_needed:
            return None
        
        # Calculate payment amount
        payment_amount = plan.monthly_amount
        is_final_payment = (payment_number == total_payments_needed)
        
        if is_final_payment:
            # Final payment - pay exact remaining balance
            previous_payments = (payment_number - 1) * plan.monthly_amount
            remaining = max(0, plan.total_open - previous_payments)
            payment_amount = min(payment_amount, remaining)
        
        # Calculate remaining balance after this payment
        total_paid_after = payment_number * plan.monthly_amount
        remaining_balance = max(0, plan.total_open - total_paid_after)
        
        if is_final_payment:
            remaining_balance = 0
        
        return {
            'plan_id': plan.plan_id,
            'payment_amount': round(payment_amount, 2),
            'payment_number': payment_number,
            'total_payments': total_payments_needed,
            'frequency': plan.frequency.value,
            'class_field': getattr(plan, 'class_filter', None),
            'is_final_payment': is_final_payment,
            'remaining_balance': round(remaining_balance, 2)
        }
    
    def _get_frequency_months(self, frequency: str) -> int:
        """Get payment frequency in months"""
        frequency_lower = frequency.lower()
        return self.frequency_months.get(frequency_lower, 1)
    
    def _calculate_total_payments_needed(self, plan) -> int:
        """Calculate total number of payments needed to pay off the plan"""
        if plan.monthly_amount <= 0:
            return 0
        return max(1, int(plan.total_open / plan.monthly_amount) + (1 if plan.total_open % plan.monthly_amount > 0 else 0))
    
    def _get_plan_completion_month(self, plan, scenario: str) -> int:
        """Calculate which month the plan will be completed"""
        frequency_months = self._get_frequency_months(plan.frequency.value)
        total_payments = self._calculate_total_payments_needed(plan)
        
        # Calculate completion month: (last_payment_number - 1) * frequency + 1
        completion_month = ((total_payments - 1) * frequency_months) + 1
        
        return completion_month
    
    def generate_portfolio_summary(self, projections: List[CustomerProjection], months_ahead: int = 12) -> Dict:
        """Generate portfolio-wide payment projections summary"""
        
        monthly_summaries = []
        total_expected = 0
        
        for month in range(1, months_ahead + 1):
            month_total = 0
            active_customers = 0
            completing_customers = 0
            
            for projection in projections:
                if month <= len(projection.timeline):
                    month_data = projection.timeline[month - 1]
                    month_total += month_data['monthly_payment']
                    
                    if month_data['monthly_payment'] > 0:
                        active_customers += 1
                    
                    # Check if any plan completes this month
                    for detail in month_data['plan_details']:
                        if detail.get('is_final_payment', False):
                            completing_customers += 1
            
            total_expected += month_total
            
            month_date = datetime.now() + relativedelta(months=month)
            
            monthly_summaries.append({
                'month': month,
                'date': month_date.isoformat(),
                'expected_payment': round(month_total, 2),
                'active_customers': active_customers,
                'completing_customers': completing_customers,
                'cumulative_total': round(total_expected, 2)
            })
        
        return {
            'monthly_projections': monthly_summaries,
            'summary': {
                'total_customers': len(projections),
                'total_expected_collection': round(total_expected, 2),
                'average_monthly': round(total_expected / months_ahead, 2) if months_ahead > 0 else 0,
                'customers_with_payments': len([p for p in projections if any(m['monthly_payment'] > 0 for m in p.timeline)])
            }
        }
    
    def get_customer_details(self, customer_name: str, projections: List[CustomerProjection]) -> Optional[Dict]:
        """Get detailed projection for a specific customer"""
        
        customer_projection = next((p for p in projections if p.customer_name == customer_name), None)
        
        if not customer_projection:
            return None
        
        return {
            'customer_name': customer_projection.customer_name,
            'total_monthly_payment': customer_projection.total_monthly_payment,
            'total_owed': customer_projection.total_owed,
            'completion_month': customer_projection.completion_month,
            'plan_count': customer_projection.plan_count,
            'timeline': customer_projection.timeline,
            'payment_months': [i + 1 for i, month in enumerate(customer_projection.timeline) if month['monthly_payment'] > 0],
            'total_projected': sum(month['monthly_payment'] for month in customer_projection.timeline)
        }


# Example usage function for testing
def test_projections():
    """Test function to verify projections work correctly"""
    
    # This would normally come from your enhanced_main.py results
    # Creating mock data that matches your models structure
    
    from models import Customer, PaymentPlan, PaymentFrequency
    
    # Mock customers for testing
    test_customers = {
        'NFN KASHIF': Customer(
            customer_name='NFN KASHIF',
            payment_plans=[PaymentPlan(
                customer_name='NFN KASHIF',
                plan_id='NFN_KASHIF_plan_1',
                monthly_amount=500,
                frequency=PaymentFrequency.MONTHLY,
                total_original=4500,
                total_open=4500,
                invoices=[],
                earliest_date=datetime.now(),
                latest_date=datetime.now(),
                has_issues=False
            )]
        ),
        'Amirjon Tursunov': Customer(
            customer_name='Amirjon Tursunov',
            payment_plans=[PaymentPlan(
                customer_name='Amirjon Tursunov',
                plan_id='Amirjon_plan_1',
                monthly_amount=1000,
                frequency=PaymentFrequency.QUARTERLY,
                total_original=4000,
                total_open=4000,
                invoices=[],
                earliest_date=datetime.now(),
                latest_date=datetime.now(),
                has_issues=False
            )]
        )
    }
    
    # Test the calculator
    calculator = PaymentProjectionCalculator()
    projections = calculator.calculate_customer_projections(test_customers, 12)
    
    print("Test Results:")
    for projection in projections:
        print(f"\n{projection.customer_name}:")
        payment_months = [i + 1 for i, month in enumerate(projection.timeline) if month['monthly_payment'] > 0]
        print(f"  Payment months: {payment_months[:6]}...")
        
        for i, month in enumerate(projection.timeline[:6]):
            if month['monthly_payment'] > 0:
                details = month['plan_details'][0] if month['plan_details'] else {}
                payment_num = details.get('payment_number', 'N/A')
                total_payments = details.get('total_payments', 'N/A')
                print(f"  Month {month['month']}: ${month['monthly_payment']} (Payment {payment_num}/{total_payments})")

if __name__ == "__main__":
    test_projections()