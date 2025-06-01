"""Enhanced issue detection and analysis functionality - Phase 1"""

from typing import List, Dict, Set
from datetime import datetime
from models import (
    Customer, PaymentPlan, CustomerIssue, IssueSeverity, ErrorType,
    DataQualityReport
)

class EnhancedIssueAnalyzer:
    """Enhanced analyzer supporting multiple plans and comprehensive error detection"""
    
    def __init__(self):
        self.issues = []
        self.quality_metrics = {}
        
    def analyze_customer(self, customer: Customer) -> List[CustomerIssue]:
        """Analyze a customer with potentially multiple payment plans"""
        customer_issues = []
        
        # Analyze each payment plan separately
        for plan in customer.payment_plans:
            plan_issues = self._analyze_payment_plan(plan)
            customer_issues.extend(plan_issues)
            
            # Update plan's issue status
            plan.has_issues = len(plan_issues) > 0
            plan.issues = plan_issues
        
        # Analyze customer-level issues
        customer_level_issues = self._analyze_customer_level_issues(customer)
        customer_issues.extend(customer_level_issues)
        
        return customer_issues
    
    def _analyze_payment_plan(self, plan: PaymentPlan) -> List[CustomerIssue]:
        """Analyze a single payment plan for issues"""
        plan_issues = []
        
        # Check for no payment terms
        if plan.monthly_amount == 0 or plan.frequency.value == 'undefined':
            plan_issues.append(CustomerIssue(
                customer_name=plan.customer_name,
                issue_type=ErrorType.NO_PAYMENT_TERMS,
                severity=IssueSeverity.CRITICAL,
                description=f'Plan {plan.plan_id}: No payment terms specified',
                affected_invoices=[inv.invoice_number for inv in plan.invoices],
                impact=f'Cannot calculate payment schedule for ${plan.total_open:,.2f} balance',
                suggested_fix='Add payment amount and frequency to FOB field',
                field_name='FOB',
                current_value=plan.payment_terms_raw
            ))
        
        # Check for future dates
        today = datetime.now()
        future_invoices = []
        for inv in plan.invoices:
            if inv.date and inv.date > today:
                future_invoices.append(inv.invoice_number)
                
        if future_invoices:
            plan_issues.append(CustomerIssue(
                customer_name=plan.customer_name,
                issue_type=ErrorType.FUTURE_DATED,
                severity=IssueSeverity.WARNING,
                description=f'Plan {plan.plan_id}: Has future-dated invoices',
                affected_invoices=future_invoices,
                impact='Payment calculations may be incorrect',
                suggested_fix='Verify invoice dates and correct if needed',
                field_name='Date'
            ))
        
        # Check for asterisk in invoice numbers
        asterisk_invoices = [inv.invoice_number for inv in plan.invoices if '*' in inv.invoice_number]
        if asterisk_invoices:
            plan_issues.append(CustomerIssue(
                customer_name=plan.customer_name,
                issue_type=ErrorType.ASTERISK_INVOICE,
                severity=IssueSeverity.INFO,
                description=f'Plan {plan.plan_id}: Invoice numbers contain asterisk (*)',
                affected_invoices=asterisk_invoices,
                impact='May indicate special handling required',
                suggested_fix='Review if asterisk notation is intentional'
            ))
        
        # Check for missing invoice numbers
        missing_num_invoices = []
        for i, inv in enumerate(plan.invoices):
            if not inv.invoice_number or inv.invoice_number.strip() == '':
                missing_num_invoices.append(f'Invoice {i+1}')
                
        if missing_num_invoices:
            plan_issues.append(CustomerIssue(
                customer_name=plan.customer_name,
                issue_type=ErrorType.MISSING_INVOICE_NUMBERS,
                severity=IssueSeverity.INFO,
                description=f'Plan {plan.plan_id}: {len(missing_num_invoices)} invoices have no invoice number',
                affected_invoices=missing_num_invoices,
                impact='May complicate tracking specific invoices',
                suggested_fix='Add unique invoice numbers',
                field_name='Num'
            ))
        
        # Check for missing class fields
        missing_class_invoices = [inv.invoice_number for inv in plan.invoices if not inv.class_field]
        if missing_class_invoices:
            plan_issues.append(CustomerIssue(
                customer_name=plan.customer_name,
                issue_type=ErrorType.MISSING_CLASS,
                severity=IssueSeverity.WARNING,
                description=f'Plan {plan.plan_id}: {len(missing_class_invoices)} invoices missing class designation',
                affected_invoices=missing_class_invoices,
                impact='Cannot filter or categorize these invoices properly',
                suggested_fix='Add class designation (BR, TSA, KL, etc.)',
                field_name='Class'
            ))
        
        # Check for invalid amounts
        invalid_amount_invoices = []
        for inv in plan.invoices:
            if inv.open_balance < 0 or inv.original_amount < 0:
                invalid_amount_invoices.append(inv.invoice_number)
        
        if invalid_amount_invoices:
            plan_issues.append(CustomerIssue(
                customer_name=plan.customer_name,
                issue_type=ErrorType.INVALID_AMOUNT,
                severity=IssueSeverity.CRITICAL,
                description=f'Plan {plan.plan_id}: Invoices with negative amounts',
                affected_invoices=invalid_amount_invoices,
                impact='Negative amounts will cause calculation errors',
                suggested_fix='Correct negative amounts or review invoice entries',
                field_name='Amount/Open Balance'
            ))
        
        # Check if open balance > original amount (impossible scenario)
        impossible_balance_invoices = []
        for inv in plan.invoices:
            if inv.open_balance > inv.original_amount and inv.original_amount > 0:
                impossible_balance_invoices.append(inv.invoice_number)
        
        if impossible_balance_invoices:
            plan_issues.append(CustomerIssue(
                customer_name=plan.customer_name,
                issue_type=ErrorType.INVALID_AMOUNT,
                severity=IssueSeverity.CRITICAL,
                description=f'Plan {plan.plan_id}: Open balance exceeds original amount',
                affected_invoices=impossible_balance_invoices,
                impact='Impossible balance scenario - data error',
                suggested_fix='Review and correct amount fields',
                field_name='Open Balance vs Amount'
            ))
        
        # Check for nested customer
        if plan.is_nested:
            plan_issues.append(CustomerIssue(
                customer_name=plan.customer_name,
                issue_type=ErrorType.NESTED_CUSTOMER,
                severity=IssueSeverity.WARNING,
                description=f'Plan {plan.plan_id}: Nested under {plan.parent_customer}',
                affected_invoices=[],
                impact='May need to be combined with parent customer',
                suggested_fix='Decide if this should be merged with parent customer'
            ))
        
        return plan_issues
    
    def _analyze_customer_level_issues(self, customer: Customer) -> List[CustomerIssue]:
        """Analyze issues at the customer level (across all plans)"""
        customer_issues = []
        
        # Check for multiple payment plans
        if customer.has_multiple_plans:
            # Check if multiple plans have different payment terms
            unique_terms = set()
            for plan in customer.payment_plans:
                if plan.payment_terms_raw:
                    unique_terms.add(plan.payment_terms_raw)
            
            if len(unique_terms) > 1:
                all_invoices = []
                for plan in customer.payment_plans:
                    all_invoices.extend([inv.invoice_number for inv in plan.invoices])
                
                customer_issues.append(CustomerIssue(
                    customer_name=customer.customer_name,
                    issue_type=ErrorType.MULTIPLE_PAYMENT_TERMS,
                    severity=IssueSeverity.WARNING,
                    description=f'Customer has {len(customer.payment_plans)} different payment plans with different terms',
                    affected_invoices=all_invoices,
                    impact='Unclear which payment schedule takes precedence',
                    suggested_fix='Consolidate to single payment plan or clarify which is current',
                    field_name='FOB',
                    current_value=', '.join(unique_terms)
                ))
        
        # Check for mixed classes across plans
        if len(customer.all_classes) > 1:
            customer_issues.append(CustomerIssue(
                customer_name=customer.customer_name,
                issue_type=ErrorType.FORMATTING_ERROR,
                severity=IssueSeverity.INFO,
                description=f'Customer has invoices across multiple classes: {", ".join(customer.all_classes)}',
                affected_invoices=[],
                impact='May need separate tracking by class',
                suggested_fix='Review if customer should be split by class or consolidated',
                field_name='Class',
                current_value=', '.join(customer.all_classes)
            ))
        
        return customer_issues
    
    def analyze_all_customers(self, customers: Dict[str, Customer]) -> Dict[str, List[Customer]]:
        """Analyze all customers and categorize them"""
        clean_customers = []
        problematic_customers = []
        self.issues = []
        
        for customer_name, customer in customers.items():
            customer_issues = self.analyze_customer(customer)
            
            if customer_issues:
                problematic_customers.append(customer)
                self.issues.extend(customer_issues)
            else:
                clean_customers.append(customer)
        
        return {
            'clean': clean_customers,
            'problematic': problematic_customers
        }
    
    def get_issue_summary(self) -> Dict[str, int]:
        """Get summary count of issues by type"""
        issue_counts = {}
        for issue in self.issues:
            issue_type = issue.issue_type.value
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        return issue_counts
    
    def get_critical_issues(self) -> List[CustomerIssue]:
        """Get only critical issues"""
        return [issue for issue in self.issues if issue.severity == IssueSeverity.CRITICAL]
    
    def get_issues_by_customer(self, customer_name: str) -> List[CustomerIssue]:
        """Get all issues for a specific customer"""
        return [issue for issue in self.issues if issue.customer_name == customer_name]
    
    def get_issues_by_class(self, class_filter: str) -> List[CustomerIssue]:
        """Get issues filtered by class"""
        # This would need customer data to filter properly
        # For now, return all issues - will enhance in reporting phase
        return self.issues
    
    def get_typo_report(self) -> List[Dict]:
        """Generate report of all typos found"""
        typo_issues = []
        for issue in self.issues:
            if issue.issue_type == ErrorType.TYPO_PAYMENT_TERMS:
                typo_issues.append({
                    'customer': issue.customer_name,
                    'field': issue.field_name,
                    'current_value': issue.current_value,
                    'suggested_fix': issue.suggested_fix,
                    'affected_invoices': issue.affected_invoices
                })
        return typo_issues
    
    def generate_error_highlight_data(self, customers: Dict[str, Customer]) -> List[Dict]:
        """Generate data for error highlighting in downloadable reports"""
        error_highlights = []
        
        for customer_name, customer in customers.items():
            for plan in customer.payment_plans:
                for invoice in plan.invoices:
                    highlight_data = {
                        'customer_name': customer_name,
                        'plan_id': plan.plan_id,
                        'invoice_number': invoice.invoice_number,
                        'date': invoice.date,
                        'payment_terms': invoice.payment_terms,
                        'original_amount': invoice.original_amount,
                        'open_balance': invoice.open_balance,
                        'class_field': invoice.class_field,
                        'errors': [],
                        'highlight_fields': []
                    }
                    
                    # Check for errors in this specific invoice
                    for issue in plan.issues:
                        if invoice.invoice_number in issue.affected_invoices:
                            highlight_data['errors'].append({
                                'type': issue.issue_type.value,
                                'severity': issue.severity.value,
                                'description': issue.description,
                                'field': issue.field_name
                            })
                            
                            if issue.field_name:
                                highlight_data['highlight_fields'].append(issue.field_name)
                    
                    error_highlights.append(highlight_data)
        
        return error_highlights