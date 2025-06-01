"""Enhanced data models for the payment plan analysis system - Phase 1"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Union
from enum import Enum

class IssueSeverity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

class PaymentFrequency(Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    BIMONTHLY = "bimonthly"
    UNDEFINED = "undefined"

class CustomerStatus(Enum):
    CURRENT = "current"
    BEHIND = "behind"
    COMPLETED = "completed"
    UNKNOWN = "unknown"

class ErrorType(Enum):
    """Enhanced error types for comprehensive tracking"""
    NO_PAYMENT_TERMS = "no_payment_terms"
    MULTIPLE_PAYMENT_TERMS = "multiple_payment_terms"
    MISSING_OPEN_BALANCE = "missing_open_balance"
    FUTURE_DATED = "future_dated"
    ASTERISK_INVOICE = "asterisk_invoice"
    MIXED_INVOICE_STATUS = "mixed_invoice_status"
    NESTED_CUSTOMER = "nested_customer"
    MISSING_INVOICE_NUMBERS = "missing_invoice_numbers"
    TYPO_PAYMENT_TERMS = "typo_payment_terms"
    INVALID_DATE_FORMAT = "invalid_date_format"
    MISSING_CLASS = "missing_class"
    INVALID_AMOUNT = "invalid_amount"
    MISSING_CUSTOMER_NAME = "missing_customer_name"
    FORMATTING_ERROR = "formatting_error"

@dataclass
class Invoice:
    """Represents a single invoice - enhanced with Class field"""
    invoice_number: str
    date: Optional[datetime]
    payment_terms: Optional[str]
    original_amount: float
    open_balance: float
    class_field: Optional[str] = None  # The "Class" column (BR, TSA, KL, etc.)
    raw_data: Dict = field(default_factory=dict)

@dataclass
class CustomerIssue:
    """Enhanced issue tracking with more error types"""
    customer_name: str
    issue_type: ErrorType
    severity: IssueSeverity
    description: str
    affected_invoices: List[str]
    impact: str
    suggested_fix: Optional[str] = None
    field_name: Optional[str] = None  # Which field has the issue
    current_value: Optional[str] = None  # Current problematic value
    
    def to_dict(self):
        return {
            'customer_name': self.customer_name,
            'issue_type': self.issue_type.value,
            'severity': self.severity.value,
            'description': self.description,
            'affected_invoices': self.affected_invoices,
            'impact': self.impact,
            'suggested_fix': self.suggested_fix,
            'field_name': self.field_name,
            'current_value': self.current_value
        }

@dataclass
class PaymentPlan:
    """Enhanced payment plan supporting multiple plans per customer"""
    customer_name: str
    plan_id: str  # Unique identifier for this specific plan
    monthly_amount: float
    frequency: PaymentFrequency
    total_original: float
    total_open: float
    invoices: List[Invoice]
    earliest_date: Optional[datetime]
    latest_date: Optional[datetime]
    class_filter: Optional[str] = None  # Dominant class for this plan
    has_issues: bool = False
    issues: List[CustomerIssue] = field(default_factory=list)
    is_nested: bool = False
    parent_customer: Optional[str] = None
    payment_terms_raw: Optional[str] = None  # Store original payment terms string

@dataclass
class Customer:
    """New model to represent a customer with potentially multiple payment plans"""
    customer_name: str
    payment_plans: List[PaymentPlan] = field(default_factory=list)
    total_open_balance: float = 0.0
    total_original_amount: float = 0.0
    all_classes: List[str] = field(default_factory=list)  # All classes across all plans
    has_multiple_plans: bool = False
    overall_status: CustomerStatus = CustomerStatus.UNKNOWN
    earliest_date: Optional[datetime] = None
    latest_date: Optional[datetime] = None

@dataclass
class PaymentMetrics:
    """Enhanced metrics with plan-specific tracking"""
    customer_name: str
    plan_id: str  # Which plan these metrics are for
    monthly_payment: float
    frequency: str
    total_owed: float
    original_amount: float
    percent_paid: float
    months_elapsed: float
    expected_payments: float
    actual_payments: float
    payment_difference: float
    months_behind: float
    status: CustomerStatus
    projected_completion: Optional[datetime]
    months_remaining: float
    class_field: Optional[str] = None
    payment_roadmap: List[Dict] = field(default_factory=list)  # Payment timeline

@dataclass
class DataQualityReport:
    """Comprehensive data quality tracking"""
    timestamp: datetime
    total_rows_processed: int
    total_customers_found: int
    total_invoices_processed: int
    total_invoices_with_open_balance: int
    total_invoices_ignored: int  # invoices with 0 open balance
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    errors_by_customer: Dict[str, List[Dict]] = field(default_factory=dict)
    typos_found: List[Dict] = field(default_factory=list)
    missing_fields: List[Dict] = field(default_factory=list)
    formatting_issues: List[Dict] = field(default_factory=list)
    classes_found: List[str] = field(default_factory=list)
    
@dataclass 
class PaymentRoadmapEntry:
    """Individual entry in a payment roadmap"""
    date: datetime
    expected_payment: float
    description: str
    is_past_due: bool = False
    actual_payment: Optional[float] = None