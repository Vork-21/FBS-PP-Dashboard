"""Enhanced payment metrics calculation functionality - Phase 1"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
from models import (
    Customer, PaymentPlan, PaymentMetrics, CustomerStatus, 
    PaymentFrequency, PaymentRoadmapEntry
)

class EnhancedPaymentCalculator:
    """Enhanced calculator supporting multiple payment plans per customer"""
    
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
        """Calculate payment metrics for a single payment plan"""
        if plan.has_issues or plan.monthly_amount == 0:
            return None
        
        # Basic calculations
        percent_paid = ((plan.total_original - plan.total_open) / plan.total_original * 100) if plan.total_original > 0 else 0
        actual_payments = plan.total_original - plan.total_open
        
        # Time-based calculations
        if plan.earliest_date:
            months_elapsed = (datetime.now() - plan.earliest_date).days / 30.44
            
            # Calculate expected payments based on frequency
            if plan.frequency == PaymentFrequency.MONTHLY:
                expected_payments = months_elapsed * plan.monthly_amount
                payment_periods = months_elapsed
            elif plan.frequency == PaymentFrequency.QUARTERLY:
                payment_periods = months_elapsed / 3
                expected_payments = payment_periods * plan.monthly_amount
            elif plan.frequency == PaymentFrequency.BIMONTHLY:
                payment_periods = months_elapsed / 2
                expected_payments = payment_periods * plan.monthly_amount
            else:
                expected_payments = 0
                payment_periods = 0
            
            payment_difference = actual_payments - expected_payments
            
            # Calculate months behind
            if plan.monthly_amount > 0 and payment_difference < 0:
                if plan.frequency == PaymentFrequency.MONTHLY:
                    months_behind = abs(payment_difference) / plan.monthly_amount
                elif plan.frequency == PaymentFrequency.QUARTERLY:
                    months_behind = abs(payment_difference) / plan.monthly_amount * 3
                elif plan.frequency == PaymentFrequency.BIMONTHLY:
                    months_behind = abs(payment_difference) / plan.monthly_amount * 2
                else:
                    months_behind = 0
            else:
                months_behind = 0
            
            # Determine status
            if plan.total_open == 0:
                status = CustomerStatus.COMPLETED
            elif months_behind > 0.5:
                status = CustomerStatus.BEHIND
            else:
                status = CustomerStatus.CURRENT
            
            # Project completion
            if plan.monthly_amount > 0 and plan.total_open > 0:
                if plan.frequency == PaymentFrequency.MONTHLY:
                    months_remaining = plan.total_open / plan.monthly_amount
                elif plan.frequency == PaymentFrequency.QUARTERLY:
                    months_remaining = (plan.total_open / plan.monthly_amount) * 3
                elif plan.frequency == PaymentFrequency.BIMONTHLY:
                    months_remaining = (plan.total_open / plan.monthly_amount) * 2
                else:
                    months_remaining = plan.total_open / plan.monthly_amount
                
                projected_completion = datetime.now() + timedelta(days=months_remaining * 30.44)
            else:
                months_remaining = 0
                projected_completion = None
            
            # Generate payment roadmap
            roadmap = self._generate_payment_roadmap(plan, months_remaining)
            
            return PaymentMetrics(
                customer_name=plan.customer_name,
                plan_id=plan.plan_id,
                monthly_payment=plan.monthly_amount,
                frequency=plan.frequency.value,
                total_owed=plan.total_open,
                original_amount=plan.total_original,
                percent_paid=percent_paid,
                months_elapsed=round(months_elapsed, 1),
                expected_payments=round(expected_payments, 2),
                actual_payments=round(actual_payments, 2),
                payment_difference=round(payment_difference, 2),
                months_behind=round(months_behind, 1),
                status=status,
                projected_completion=projected_completion,
                months_remaining=round(months_remaining, 1),
                class_field=plan.class_filter,
                payment_roadmap=roadmap
            )
        
        return None
    
    def _generate_payment_roadmap(self, plan: PaymentPlan, months_remaining: float) -> List[Dict]:
        """Generate payment roadmap/timeline for a payment plan"""
        roadmap = []
        
        if plan.monthly_amount <= 0 or months_remaining <= 0:
            return roadmap
        
        current_date = datetime.now()
        remaining_balance = plan.total_open
        
        # Determine payment interval
        if plan.frequency == PaymentFrequency.MONTHLY:
            interval_months = 1
        elif plan.frequency == PaymentFrequency.QUARTERLY:
            interval_months = 3
        elif plan.frequency == PaymentFrequency.BIMONTHLY:
            interval_months = 2
        else:
            interval_months = 1
        
        # Generate roadmap entries
        payment_count = 0
        max_payments = 60  # Limit to 5 years of payments
        
        while remaining_balance > 0 and payment_count < max_payments:
            payment_date = current_date + timedelta(days=payment_count * interval_months * 30.44)
            payment_amount = min(plan.monthly_amount, remaining_balance)
            
            roadmap_entry = {
                'payment_number': payment_count + 1,
                'date': payment_date.strftime('%Y-%m-%d'),
                'expected_payment': round(payment_amount, 2),
                'remaining_balance': round(remaining_balance - payment_amount, 2),
                'is_overdue': payment_date < current_date,
                'description': f'Payment {payment_count + 1} - {plan.frequency.value}'
            }
            
            roadmap.append(roadmap_entry)
            remaining_balance -= payment_amount
            payment_count += 1
        
        return roadmap
    
    def calculate_portfolio_metrics(self, all_metrics: List[PaymentMetrics]) -> Dict:
        """Calculate aggregate metrics for entire portfolio"""
        if not all_metrics:
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
        
        # Group by customer to avoid double counting
        customers_by_status = {}
        plans_by_class = {}
        plans_by_frequency = {}
        
        total_outstanding = sum(m.total_owed for m in all_metrics)
        expected_monthly = 0
        
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
        
        total_behind_amount = sum(abs(m.payment_difference) for m in behind_metrics)
        
        return {
            'total_customers': len(customers_by_status),
            'total_plans': len(all_metrics),
            'total_outstanding': total_outstanding,
            'expected_monthly': expected_monthly,
            'customers_current': status_counts[CustomerStatus.CURRENT],
            'customers_behind': status_counts[CustomerStatus.BEHIND], 
            'customers_completed': status_counts[CustomerStatus.COMPLETED],
            'average_months_behind': round(average_months_behind, 1),
            'total_behind_amount': total_behind_amount,
            'percentage_behind': (status_counts[CustomerStatus.BEHIND] / len(customers_by_status) * 100) if customers_by_status else 0,
            'plans_by_class': plans_by_class,
            'plans_by_frequency': plans_by_frequency
        }
    
    def get_customers_by_class(self, all_metrics: List[PaymentMetrics], class_filter: str) -> List[PaymentMetrics]:
        """Filter metrics by class"""
        return [m for m in all_metrics if m.class_field == class_filter]
    
    def get_customers_by_status(self, all_metrics: List[PaymentMetrics], status: CustomerStatus) -> List[PaymentMetrics]:
        """Filter metrics by status"""
        return [m for m in all_metrics if m.status == status]
    
    def prioritize_collections(self, all_metrics: List[PaymentMetrics]) -> List[PaymentMetrics]:
        """Prioritize customers for collections based on various factors"""
        # Filter to only behind customers
        behind_customers = [m for m in all_metrics if m.status == CustomerStatus.BEHIND]
        
        # Sort by multiple criteria:
        # 1. Months behind (descending)
        # 2. Total amount owed (descending)
        # 3. Payment difference (ascending - most negative first)
        
        return sorted(behind_customers, 
                     key=lambda m: (-m.months_behind, -m.total_owed, m.payment_difference))
    
    def calculate_recovery_scenarios(self, metrics: PaymentMetrics) -> Dict:
        """Calculate different recovery scenarios for a behind customer"""
        if metrics.status != CustomerStatus.BEHIND or metrics.monthly_payment == 0:
            return {}
        
        scenarios = {}
        
        # Scenario 1: Catch up in 3 months
        catch_up_3_months = (abs(metrics.payment_difference) + (metrics.monthly_payment * 3)) / 3
        scenarios['catch_up_3_months'] = {
            'monthly_payment': round(catch_up_3_months, 2),
            'total_period': 3,
            'description': 'Catch up in 3 months',
            'total_additional': round(abs(metrics.payment_difference), 2)
        }
        
        # Scenario 2: Catch up in 6 months
        catch_up_6_months = (abs(metrics.payment_difference) + (metrics.monthly_payment * 6)) / 6
        scenarios['catch_up_6_months'] = {
            'monthly_payment': round(catch_up_6_months, 2),
            'total_period': 6,
            'description': 'Catch up in 6 months',
            'total_additional': round(abs(metrics.payment_difference), 2)
        }
        
        # Scenario 3: Double payment until caught up
        double_payment_months = abs(metrics.payment_difference) / metrics.monthly_payment
        scenarios['double_payment'] = {
            'monthly_payment': round(metrics.monthly_payment * 2, 2),
            'total_period': round(double_payment_months, 1),
            'description': 'Double regular payment until caught up',
            'total_additional': round(abs(metrics.payment_difference), 2)
        }
        
        return scenarios
    
    def generate_class_summary(self, all_metrics: List[PaymentMetrics]) -> Dict[str, Dict]:
        """Generate summary by class"""
        class_summary = {}
        
        for metric in all_metrics:
            class_key = metric.class_field or 'Unknown'
            
            if class_key not in class_summary:
                class_summary[class_key] = {
                    'total_customers': 0,
                    'total_plans': 0,
                    'total_owed': 0,
                    'customers_behind': 0,
                    'expected_monthly': 0,
                    'customers': set()
                }
            
            class_summary[class_key]['total_plans'] += 1
            class_summary[class_key]['total_owed'] += metric.total_owed
            class_summary[class_key]['customers'].add(metric.customer_name)
            
            if metric.status == CustomerStatus.BEHIND:
                class_summary[class_key]['customers_behind'] += 1
            
            # Normalize expected monthly
            if metric.frequency == 'monthly':
                class_summary[class_key]['expected_monthly'] += metric.monthly_payment
            elif metric.frequency == 'quarterly':
                class_summary[class_key]['expected_monthly'] += metric.monthly_payment / 3
            elif metric.frequency == 'bimonthly':
                class_summary[class_key]['expected_monthly'] += metric.monthly_payment / 2
        
        # Convert sets to counts
        for class_key in class_summary:
            class_summary[class_key]['total_customers'] = len(class_summary[class_key]['customers'])
            del class_summary[class_key]['customers']  # Remove the set
        
        return class_summary