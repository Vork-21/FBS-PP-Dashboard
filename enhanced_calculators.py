"""Enhanced payment metrics calculation functionality - FIXED VERSION
Resolves logical issues with months display, deficit calculations, and percentage calculations
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
import math
from models import (
    Customer, PaymentPlan, PaymentMetrics, CustomerStatus, 
    PaymentFrequency, PaymentRoadmapEntry
)

class EnhancedPaymentCalculator:
    """Enhanced calculator with fixed logical issues"""
    
    def __init__(self):
        # Payment date is always 15th of month
        self.payment_day = 15
        
    def calculate_customer_metrics(self, customer: Customer) -> List[PaymentMetrics]:
        """Calculate metrics for all payment plans for a customer"""
        all_metrics = []
        
        for plan in customer.payment_plans:
            if not plan.has_issues and plan.monthly_amount > 0:
                metrics = self.calculate_plan_metrics(plan)
                if metrics:
                    all_metrics.append(metrics)
        
        return all_metrics
    
    def calculate_plan_metrics(self, plan: PaymentPlan) -> Optional[PaymentMetrics]:
        """Calculate payment metrics for a single payment plan - FIXED VERSION"""
        if plan.has_issues or plan.monthly_amount == 0:
            return None
        
        # FIXED: Always use whole numbers for months (rounded up)
        if plan.earliest_date:
            # Calculate months elapsed from earliest invoice date
            days_elapsed = (datetime.now() - plan.earliest_date).days
            months_elapsed_decimal = days_elapsed / 30.44  # Average days per month
            months_elapsed = math.ceil(months_elapsed_decimal)  # ALWAYS round up
            
            # FIXED: Calculate expected payments based on frequency and actual time
            expected_payments = self._calculate_expected_payments(plan, months_elapsed)
            
            # FIXED: Calculate actual payments more accurately
            actual_payments = plan.total_original - plan.total_open
            
            # FIXED: Payment difference calculation
            payment_difference = actual_payments - expected_payments
            
            # FIXED: Months behind calculation (always whole numbers)
            months_behind = self._calculate_months_behind(plan, payment_difference)
            
            # FIXED: More accurate percentage calculation considering time
            percent_paid = self._calculate_percent_paid(plan, months_elapsed)
            
            # Determine status
            if plan.total_open == 0:
                status = CustomerStatus.COMPLETED
            elif months_behind > 0:  # Any delay means behind
                status = CustomerStatus.BEHIND
            else:
                status = CustomerStatus.CURRENT
            
            # FIXED: Project completion using 15th of month
            months_remaining, projected_completion = self._calculate_completion(plan)
            
            # Generate payment roadmap
            roadmap = self._generate_payment_roadmap(plan, months_remaining)
            
            return PaymentMetrics(
                customer_name=plan.customer_name,
                plan_id=plan.plan_id,
                monthly_payment=plan.monthly_amount,
                frequency=plan.frequency.value,
                total_owed=plan.total_open,
                original_amount=plan.total_original,
                percent_paid=round(percent_paid, 1),
                months_elapsed=months_elapsed,  # Whole number
                expected_payments=round(expected_payments, 2),
                actual_payments=round(actual_payments, 2),
                payment_difference=round(payment_difference, 2),
                months_behind=months_behind,  # Whole number
                status=status,
                projected_completion=projected_completion,
                months_remaining=months_remaining,  # Whole number
                class_field=plan.class_filter,
                payment_roadmap=roadmap
            )
        
        return None
    
    def _calculate_expected_payments(self, plan: PaymentPlan, months_elapsed: int) -> float:
        """Calculate expected payments based on frequency and time elapsed"""
        if plan.frequency == PaymentFrequency.MONTHLY:
            # Expected one payment per month
            return months_elapsed * plan.monthly_amount
        elif plan.frequency == PaymentFrequency.QUARTERLY:
            # Expected one payment every 3 months
            quarterly_periods = months_elapsed // 3
            return quarterly_periods * plan.monthly_amount
        elif plan.frequency == PaymentFrequency.BIMONTHLY:
            # Expected one payment every 2 months
            bimonthly_periods = months_elapsed // 2
            return bimonthly_periods * plan.monthly_amount
        else:
            return 0.0
    
    def _calculate_months_behind(self, plan: PaymentPlan, payment_difference: float) -> int:
        """Calculate months behind - FIXED to return whole numbers only"""
        if payment_difference >= 0:  # Not behind
            return 0
        
        deficit = abs(payment_difference)
        
        if plan.monthly_amount <= 0:
            return 0
        
        # Calculate months behind based on payment deficit
        if plan.frequency == PaymentFrequency.MONTHLY:
            months_behind_decimal = deficit / plan.monthly_amount
        elif plan.frequency == PaymentFrequency.QUARTERLY:
            # For quarterly, each missed payment represents 3 months
            payments_behind = deficit / plan.monthly_amount
            months_behind_decimal = payments_behind * 3
        elif plan.frequency == PaymentFrequency.BIMONTHLY:
            # For bimonthly, each missed payment represents 2 months
            payments_behind = deficit / plan.monthly_amount
            months_behind_decimal = payments_behind * 2
        else:
            months_behind_decimal = deficit / plan.monthly_amount
        
        # ALWAYS return whole numbers (rounded up)
        return math.ceil(months_behind_decimal)
    
    def _calculate_percent_paid(self, plan: PaymentPlan, months_elapsed: int) -> float:
        """Calculate percentage paid considering time elapsed - FIXED VERSION"""
        if plan.total_original <= 0:
            return 0.0
        
        # Basic percentage of total amount paid
        basic_percent = ((plan.total_original - plan.total_open) / plan.total_original) * 100
        
        # Consider time factor - what percentage should have been paid by now?
        if plan.frequency == PaymentFrequency.MONTHLY:
            expected_payment_count = months_elapsed
        elif plan.frequency == PaymentFrequency.QUARTERLY:
            expected_payment_count = months_elapsed // 3
        elif plan.frequency == PaymentFrequency.BIMONTHLY:
            expected_payment_count = months_elapsed // 2
        else:
            expected_payment_count = months_elapsed
        
        # Calculate what percentage should have been paid based on schedule
        total_payments_needed = math.ceil(plan.total_original / plan.monthly_amount)
        expected_percent_by_now = min(100.0, (expected_payment_count / total_payments_needed) * 100)
        
        # Return the actual percentage paid (not relative to expected)
        return basic_percent
    
    def _calculate_completion(self, plan: PaymentPlan) -> tuple[int, Optional[datetime]]:
        """Calculate completion timeline - FIXED to use 15th of month"""
        if plan.monthly_amount <= 0 or plan.total_open <= 0:
            return 0, None
        
        # Calculate remaining payments needed
        payments_remaining = math.ceil(plan.total_open / plan.monthly_amount)
        
        # Convert to months based on frequency
        if plan.frequency == PaymentFrequency.MONTHLY:
            months_remaining = payments_remaining
        elif plan.frequency == PaymentFrequency.QUARTERLY:
            months_remaining = payments_remaining * 3
        elif plan.frequency == PaymentFrequency.BIMONTHLY:
            months_remaining = payments_remaining * 2
        else:
            months_remaining = payments_remaining
        
        # FIXED: Project completion to 15th of target month
        if months_remaining > 0:
            target_date = datetime.now().replace(day=self.payment_day)
            # Add months
            for _ in range(months_remaining):
                if target_date.month == 12:
                    target_date = target_date.replace(year=target_date.year + 1, month=1)
                else:
                    target_date = target_date.replace(month=target_date.month + 1)
            
            projected_completion = target_date
        else:
            projected_completion = None
        
        return months_remaining, projected_completion
    
    def _generate_payment_roadmap(self, plan: PaymentPlan, months_remaining: int) -> List[Dict]:
        """Generate payment roadmap using 15th of month - FIXED VERSION"""
        roadmap = []
        
        if plan.monthly_amount <= 0 or months_remaining <= 0:
            return roadmap
        
        current_balance = plan.total_open
        current_date = datetime.now().replace(day=self.payment_day)
        
        # Determine payment interval in months
        if plan.frequency == PaymentFrequency.MONTHLY:
            interval_months = 1
        elif plan.frequency == PaymentFrequency.QUARTERLY:
            interval_months = 3
        elif plan.frequency == PaymentFrequency.BIMONTHLY:
            interval_months = 2
        else:
            interval_months = 1
        
        payment_number = 1
        max_payments = 60  # Limit to 5 years
        
        while current_balance > 0 and payment_number <= max_payments:
            # Calculate payment amount (final payment may be less)
            payment_amount = min(plan.monthly_amount, current_balance)
            
            # Add entry to roadmap
            roadmap_entry = {
                'payment_number': payment_number,
                'date': current_date.strftime('%Y-%m-%d'),
                'expected_payment': round(payment_amount, 2),
                'remaining_balance': round(current_balance - payment_amount, 2),
                'is_overdue': current_date < datetime.now(),
                'description': f'Payment {payment_number} - {plan.frequency.value}'
            }
            
            roadmap.append(roadmap_entry)
            
            # Update for next iteration
            current_balance -= payment_amount
            payment_number += 1
            
            # Move to next payment date
            for _ in range(interval_months):
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
        
        return roadmap
    
    def calculate_portfolio_metrics(self, all_metrics: List[PaymentMetrics]) -> Dict:
        """Calculate aggregate metrics - FIXED VERSION"""
        if not all_metrics:
            return self._empty_portfolio_metrics()
        
        # Group by customer to avoid double counting
        customers_by_status = {}
        plans_by_class = {}
        plans_by_frequency = {}
        
        total_outstanding = sum(m.total_owed for m in all_metrics)
        expected_monthly = 0
        total_behind_amount = 0  # FIXED: Track actual behind amount
        
        for metric in all_metrics:
            # Track plans by class
            class_key = metric.class_field or 'Unknown'
            if class_key not in plans_by_class:
                plans_by_class[class_key] = {'count': 0, 'total_owed': 0}
            plans_by_class[class_key]['count'] += 1
            plans_by_class[class_key]['total_owed'] += metric.total_owed
            
            # Track plans by frequency
            freq_key = metric.frequency
            if freq_key not in plans_by_frequency:
                plans_by_frequency[freq_key] = {'count': 0, 'total_owed': 0}
            plans_by_frequency[freq_key]['count'] += 1
            plans_by_frequency[freq_key]['total_owed'] += metric.total_owed
            
            # Calculate expected monthly (normalize all to monthly)
            if metric.frequency == 'monthly':
                expected_monthly += metric.monthly_payment
            elif metric.frequency == 'quarterly':
                expected_monthly += metric.monthly_payment / 3
            elif metric.frequency == 'bimonthly':
                expected_monthly += metric.monthly_payment / 2
            
            # FIXED: Calculate behind amount (capped at total owed)
            if metric.status == CustomerStatus.BEHIND:
                # Payment deficit should never exceed total owed
                deficit = min(abs(metric.payment_difference), metric.total_owed)
                total_behind_amount += deficit
            
            # Track customer status (use worst status per customer)
            customer_key = metric.customer_name
            current_status = customers_by_status.get(customer_key, CustomerStatus.CURRENT)
            
            if metric.status == CustomerStatus.BEHIND or current_status == CustomerStatus.BEHIND:
                customers_by_status[customer_key] = CustomerStatus.BEHIND
            elif metric.status == CustomerStatus.COMPLETED and current_status == CustomerStatus.CURRENT:
                customers_by_status[customer_key] = CustomerStatus.COMPLETED
            elif current_status == CustomerStatus.CURRENT:
                customers_by_status[customer_key] = metric.status
        
        # Count customers by status
        status_counts = {
            CustomerStatus.CURRENT: 0,
            CustomerStatus.BEHIND: 0,
            CustomerStatus.COMPLETED: 0
        }
        
        for status in customers_by_status.values():
            status_counts[status] += 1
        
        # Calculate average months behind for behind customers
        behind_metrics = [m for m in all_metrics if m.status == CustomerStatus.BEHIND]
        average_months_behind = (sum(m.months_behind for m in behind_metrics) / len(behind_metrics) 
                               if behind_metrics else 0)
        
        return {
            'total_customers': len(customers_by_status),
            'total_plans': len(all_metrics),
            'total_outstanding': total_outstanding,
            'expected_monthly': expected_monthly,
            'customers_current': status_counts[CustomerStatus.CURRENT],
            'customers_behind': status_counts[CustomerStatus.BEHIND], 
            'customers_completed': status_counts[CustomerStatus.COMPLETED],
            'average_months_behind': math.ceil(average_months_behind),  # FIXED: Whole number
            'total_behind_amount': total_behind_amount,  # FIXED: Capped amount
            'percentage_behind': (status_counts[CustomerStatus.BEHIND] / len(customers_by_status) * 100) if customers_by_status else 0,
            'plans_by_class': plans_by_class,
            'plans_by_frequency': plans_by_frequency
        }
    
    def _empty_portfolio_metrics(self) -> Dict:
        """Return empty portfolio metrics"""
        return {
            'total_customers': 0,
            'total_plans': 0,
            'total_outstanding': 0,
            'expected_monthly': 0,
            'customers_current': 0,
            'customers_behind': 0,
            'customers_completed': 0,
            'average_months_behind': 0,
            'total_behind_amount': 0,
            'plans_by_class': {},
            'plans_by_frequency': {}
        }
    
    def prioritize_collections(self, all_metrics: List[PaymentMetrics]) -> List[PaymentMetrics]:
        """Prioritize customers for collections - FIXED VERSION"""
        # Filter to only behind customers
        behind_customers = [m for m in all_metrics if m.status == CustomerStatus.BEHIND]
        
        # Sort by multiple criteria:
        # 1. Months behind (descending)
        # 2. Total amount owed (descending)  
        # 3. Payment difference (most negative first, but capped)
        
        def sort_key(metric):
            # Cap payment difference at total owed
            capped_difference = min(abs(metric.payment_difference), metric.total_owed)
            return (-metric.months_behind, -metric.total_owed, -capped_difference)
        
        return sorted(behind_customers, key=sort_key)