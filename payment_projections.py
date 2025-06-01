"""
FIXED Payment Projections Calculator - Handles Behind Customers Properly
- Uses 15th of month for all payment dates
- Provides scenarios for customers who need renegotiation
- Always uses whole months (no decimals)
- Caps deficits at balance owed
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import calendar
import math

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
    timeline: List[Dict]
    status: str  # NEW: current, behind, needs_renegotiation
    months_behind: int  # NEW: For tracking delinquency
    renegotiation_needed: bool  # NEW: Flag for contact needed

class PaymentProjectionCalculator:
    """FIXED Payment projection calculator with proper behind customer handling"""
    
    def __init__(self):
        self.frequency_months = {
            'monthly': 1,
            'quarterly': 3, 
            'bimonthly': 2,
            'undefined': 1
        }
        self.payment_day = 15  # All payments on 15th of month
    
    def calculate_customer_projections(self, customers_data: Dict, months_ahead: int = 12, scenario: str = 'current') -> List[CustomerProjection]:
        """
        FIXED: Calculate payment projections including behind customers
        
        Scenarios:
        - 'current': Show projections if customers continue current behavior
        - 'restart': Show projections if customers restart payment plans today
        - 'renegotiate': Show projections if payment plans are renegotiated
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
        
        # Sort by priority: behind customers first, then by monthly payment
        projections.sort(key=lambda x: (
            0 if x.renegotiation_needed else 1,  # Behind customers first
            -x.total_monthly_payment  # Then by payment amount
        ))
        
        return projections
    
    def _calculate_single_customer_projection(self, customer, months_ahead: int, scenario: str) -> Optional[CustomerProjection]:
        """FIXED: Calculate projection for a single customer with proper behind handling"""
        
        # Get valid payment plans
        valid_plans = []
        behind_plans = []
        
        for plan in customer.payment_plans:
            if plan.monthly_amount > 0 and plan.total_open > 0:
                # Check if customer is behind on this plan
                months_behind = self._calculate_months_behind_for_plan(plan)
                
                if months_behind > 0:
                    behind_plans.append((plan, months_behind))
                else:
                    valid_plans.append(plan)
        
        # Determine customer status and handling
        total_months_behind = sum(months for _, months in behind_plans)
        all_plans = valid_plans + [plan for plan, _ in behind_plans]
        
        if not all_plans:
            return None
        
        # Determine projection approach
        if total_months_behind > 0:
            if scenario == 'current':
                # For behind customers in 'current' scenario, show what happens if they don't catch up
                return self._project_behind_customer_current(customer, all_plans, behind_plans, months_ahead)
            elif scenario == 'restart':
                # Show what happens if they restart today (ignore past due)
                return self._project_customer_restart(customer, all_plans, months_ahead)
            elif scenario == 'renegotiate':
                # Show what happens with new payment terms
                return self._project_customer_renegotiate(customer, all_plans, behind_plans, months_ahead)
        else:
            # Customer is current - normal projection
            return self._project_current_customer(customer, valid_plans, months_ahead)
    
    def _calculate_months_behind_for_plan(self, plan) -> int:
        """Calculate how many months behind a plan is - FIXED to whole numbers"""
        if not plan.earliest_date:
            return 0
        
        # Calculate months elapsed since first invoice
        days_elapsed = (datetime.now() - plan.earliest_date).days
        months_elapsed = math.ceil(days_elapsed / 30.44)  # Always round up
        
        # Calculate expected payments
        if plan.frequency.value == 'monthly':
            expected_payments = months_elapsed * plan.monthly_amount
        elif plan.frequency.value == 'quarterly':
            quarterly_periods = months_elapsed // 3
            expected_payments = quarterly_periods * plan.monthly_amount
        elif plan.frequency.value == 'bimonthly':
            bimonthly_periods = months_elapsed // 2
            expected_payments = bimonthly_periods * plan.monthly_amount
        else:
            expected_payments = months_elapsed * plan.monthly_amount
        
        # Calculate actual payments
        actual_payments = plan.total_original - plan.total_open
        
        # Calculate months behind
        payment_deficit = expected_payments - actual_payments
        
        if payment_deficit <= 0:
            return 0
        
        # FIXED: Cap deficit at total owed and convert to months
        capped_deficit = min(payment_deficit, plan.total_open)
        
        if plan.monthly_amount > 0:
            months_behind_decimal = capped_deficit / plan.monthly_amount
            
            # Adjust for frequency
            if plan.frequency.value == 'quarterly':
                months_behind_decimal *= 3
            elif plan.frequency.value == 'bimonthly':
                months_behind_decimal *= 2
            
            return math.ceil(months_behind_decimal)  # Always whole numbers
        
        return 0
    
    def _project_behind_customer_current(self, customer, all_plans, behind_plans, months_ahead) -> CustomerProjection:
        """Project what happens if behind customer continues current behavior"""
        
        total_months_behind = sum(months for _, months in behind_plans)
        total_monthly = sum(plan.monthly_amount for plan in all_plans)
        total_owed = sum(plan.total_open for plan in all_plans)
        
        # For behind customers in current scenario, show minimal projections
        # They need to be contacted for renegotiation
        timeline = []
        
        for month in range(1, months_ahead + 1):
            month_date = self._get_payment_date_for_month(month)
            
            # Behind customers likely won't make regular payments
            # Show only plans that are current
            monthly_payment = 0
            active_plans = 0
            plan_details = []
            
            # Only include plans that aren't behind
            current_plans = [plan for plan in all_plans if (plan, 0) not in behind_plans]
            
            for plan in current_plans:
                payment_info = self._calculate_plan_payment_for_month(plan, month, 'current')
                if payment_info and payment_info['payment_amount'] > 0:
                    monthly_payment += payment_info['payment_amount']
                    active_plans += 1
                    plan_details.append(payment_info)
            
            timeline.append({
                'month': month,
                'date': month_date.isoformat(),
                'monthly_payment': round(monthly_payment, 2),
                'active_plans': active_plans,
                'plan_details': plan_details,
                'note': 'Behind customer - contact needed' if total_months_behind > 0 else ''
            })
        
        return CustomerProjection(
            customer_name=customer.customer_name,
            total_monthly_payment=total_monthly,
            total_owed=total_owed,
            completion_month=0,  # Unknown until renegotiation
            plan_count=len(all_plans),
            timeline=timeline,
            status='behind' if total_months_behind > 0 else 'current',
            months_behind=total_months_behind,
            renegotiation_needed=total_months_behind > 0
        )
    
    def _project_customer_restart(self, customer, all_plans, months_ahead) -> CustomerProjection:
        """Project what happens if customer restarts payment plan today"""
        
        total_monthly = sum(plan.monthly_amount for plan in all_plans)
        total_owed = sum(plan.total_open for plan in all_plans)
        
        # Calculate completion assuming they start fresh today
        if total_monthly > 0:
            # Find the plan that takes longest to complete
            max_completion_month = 0
            for plan in all_plans:
                plan_completion = self._get_plan_completion_month_restart(plan)
                max_completion_month = max(max_completion_month, plan_completion)
            
            completion_month = min(max_completion_month, months_ahead)
        else:
            completion_month = months_ahead
        
        # Generate timeline assuming fresh start
        timeline = []
        for month in range(1, months_ahead + 1):
            month_date = self._get_payment_date_for_month(month)
            
            monthly_payment = 0
            active_plans = 0
            plan_details = []
            
            for plan in all_plans:
                payment_info = self._calculate_plan_payment_for_month(plan, month, 'restart')
                if payment_info and payment_info['payment_amount'] > 0:
                    monthly_payment += payment_info['payment_amount']
                    active_plans += 1
                    plan_details.append(payment_info)
            
            timeline.append({
                'month': month,
                'date': month_date.isoformat(),
                'monthly_payment': round(monthly_payment, 2),
                'active_plans': active_plans,
                'plan_details': plan_details,
                'note': 'Restart scenario' if month == 1 else ''
            })
        
        return CustomerProjection(
            customer_name=customer.customer_name,
            total_monthly_payment=total_monthly,
            total_owed=total_owed,
            completion_month=completion_month,
            plan_count=len(all_plans),
            timeline=timeline,
            status='restart',
            months_behind=0,  # Reset to 0 in restart scenario
            renegotiation_needed=False
        )
    
    def _project_customer_renegotiate(self, customer, all_plans, behind_plans, months_ahead) -> CustomerProjection:
        """Project what happens with renegotiated payment terms"""
        
        # For renegotiation scenario, suggest extended terms or reduced payments
        total_owed = sum(plan.total_open for plan in all_plans)
        
        # Suggest payment plan that completes in reasonable time (24-36 months)
        suggested_monthly = total_owed / 30  # 30-month plan
        
        timeline = []
        remaining_balance = total_owed
        
        for month in range(1, months_ahead + 1):
            month_date = self._get_payment_date_for_month(month)
            
            if remaining_balance > 0:
                payment_amount = min(suggested_monthly, remaining_balance)
                remaining_balance -= payment_amount
                
                timeline.append({
                    'month': month,
                    'date': month_date.isoformat(),
                    'monthly_payment': round(payment_amount, 2),
                    'active_plans': len(all_plans),
                    'plan_details': [{
                        'plan_id': 'renegotiated_plan',
                        'payment_amount': round(payment_amount, 2),
                        'payment_number': month,
                        'total_payments': math.ceil(total_owed / suggested_monthly),
                        'frequency': 'monthly',
                        'is_final_payment': remaining_balance <= 0
                    }],
                    'note': 'Proposed renegotiated terms'
                })
            else:
                timeline.append({
                    'month': month,
                    'date': month_date.isoformat(),
                    'monthly_payment': 0,
                    'active_plans': 0,
                    'plan_details': [],
                    'note': 'Plan completed'
                })
        
        completion_month = math.ceil(total_owed / suggested_monthly) if suggested_monthly > 0 else 0
        
        return CustomerProjection(
            customer_name=customer.customer_name,
            total_monthly_payment=suggested_monthly,
            total_owed=total_owed,
            completion_month=min(completion_month, months_ahead),
            plan_count=len(all_plans),
            timeline=timeline,
            status='renegotiate',
            months_behind=sum(months for _, months in behind_plans),
            renegotiation_needed=True
        )
    
    def _project_current_customer(self, customer, valid_plans, months_ahead) -> CustomerProjection:
        """Project current customer - normal handling"""
        
        total_monthly = sum(plan.monthly_amount for plan in valid_plans)
        total_owed = sum(plan.total_open for plan in valid_plans)
        
        # Calculate completion
        max_completion_month = 0
        for plan in valid_plans:
            plan_completion = self._get_plan_completion_month(plan)
            max_completion_month = max(max_completion_month, plan_completion)
        
        timeline = []
        for month in range(1, months_ahead + 1):
            month_date = self._get_payment_date_for_month(month)
            
            monthly_payment = 0
            active_plans = 0
            plan_details = []
            
            for plan in valid_plans:
                payment_info = self._calculate_plan_payment_for_month(plan, month, 'current')
                if payment_info and payment_info['payment_amount'] > 0:
                    monthly_payment += payment_info['payment_amount']
                    active_plans += 1
                    plan_details.append(payment_info)
            
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
            completion_month=min(max_completion_month, months_ahead),
            plan_count=len(valid_plans),
            timeline=timeline,
            status='current',
            months_behind=0,
            renegotiation_needed=False
        )
    
    def _get_payment_date_for_month(self, month_number: int) -> datetime:
        """Get payment date for a given month (always 15th)"""
        current_date = datetime.now()
        target_date = current_date + relativedelta(months=month_number)
        # Always use 15th of month
        return target_date.replace(day=self.payment_day)
    
    def _calculate_plan_payment_for_month(self, plan, month: int, scenario: str) -> Optional[Dict]:
        """FIXED: Calculate payment for specific plan and month"""
        
        frequency_months = self._get_frequency_months(plan.frequency.value)
        
        # Check if this month is a payment month
        is_payment_month = ((month - 1) % frequency_months) == 0
        
        if not is_payment_month:
            return None
        
        # Calculate payment number
        payment_number = ((month - 1) // frequency_months) + 1
        
        # Calculate total payments needed
        total_payments_needed = math.ceil(plan.total_open / plan.monthly_amount)
        
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
        
        # Calculate remaining balance
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
        return self.frequency_months.get(frequency.lower(), 1)
    
    def _get_plan_completion_month(self, plan) -> int:
        """Calculate completion month for current plan"""
        if plan.monthly_amount <= 0:
            return 0
        
        frequency_months = self._get_frequency_months(plan.frequency.value)
        total_payments = math.ceil(plan.total_open / plan.monthly_amount)
        
        return ((total_payments - 1) * frequency_months) + 1
    
    def _get_plan_completion_month_restart(self, plan) -> int:
        """Calculate completion month if plan restarts today"""
        return self._get_plan_completion_month(plan)  # Same calculation
    
    def generate_portfolio_summary(self, projections: List[CustomerProjection], months_ahead: int = 12) -> Dict:
        """Generate portfolio summary with behind customer analysis"""
        
        if not projections:
            return self._empty_portfolio_summary()
        
        monthly_summaries = []
        total_expected = 0
        
        # Categorize customers
        current_customers = [p for p in projections if p.status == 'current']
        behind_customers = [p for p in projections if p.status == 'behind']
        restart_customers = [p for p in projections if p.status == 'restart']
        renegotiation_customers = [p for p in projections if p.status == 'renegotiate']
        
        for month in range(1, months_ahead + 1):
            month_total = 0
            active_customers = 0
            completing_customers = 0
            behind_count = 0
            
            for projection in projections:
                if month <= len(projection.timeline):
                    month_data = projection.timeline[month - 1]
                    month_total += month_data['monthly_payment']
                    
                    if month_data['monthly_payment'] > 0:
                        active_customers += 1
                    
                    if projection.status == 'behind':
                        behind_count += 1
                    
                    # Check if any plan completes this month
                    for detail in month_data.get('plan_details', []):
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
                'behind_customers': behind_count,
                'cumulative_total': round(total_expected, 2)
            })
        
        return {
            'monthly_projections': monthly_summaries,
            'summary': {
                'total_customers': len(projections),
                'current_customers': len(current_customers),
                'behind_customers': len(behind_customers),
                'customers_needing_renegotiation': len(renegotiation_customers),
                'total_expected_collection': round(total_expected, 2),
                'average_monthly': round(total_expected / months_ahead, 2) if months_ahead > 0 else 0,
                'customers_with_payments': len([p for p in projections if any(m['monthly_payment'] > 0 for m in p.timeline)]),
                'total_months_behind': sum(p.months_behind for p in behind_customers),
                'potential_recovery_amount': sum(p.total_owed for p in behind_customers)
            },
            'customer_categories': {
                'current': len(current_customers),
                'behind': len(behind_customers),
                'restart_scenario': len(restart_customers),
                'renegotiation_needed': len(renegotiation_customers)
            }
        }
    
    def _empty_portfolio_summary(self) -> Dict:
        """Return empty portfolio summary"""
        return {
            'monthly_projections': [],
            'summary': {
                'total_customers': 0,
                'total_expected_collection': 0,
                'average_monthly': 0,
                'customers_with_payments': 0
            }
        }
    
    def get_renegotiation_candidates(self, projections: List[CustomerProjection]) -> List[Dict]:
        """Get list of customers who need renegotiation"""
        candidates = []
        
        for projection in projections:
            if projection.renegotiation_needed:
                candidates.append({
                    'customer_name': projection.customer_name,
                    'months_behind': projection.months_behind,
                    'total_owed': projection.total_owed,
                    'current_monthly': projection.total_monthly_payment,
                    'suggested_monthly': projection.total_owed / 30,  # 30-month plan
                    'priority': 'high' if projection.months_behind > 6 else 
                              'medium' if projection.months_behind > 3 else 'low'
                })
        
        # Sort by months behind (most behind first)
        candidates.sort(key=lambda x: -x['months_behind'])
        return candidates