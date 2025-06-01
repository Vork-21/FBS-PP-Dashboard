"""Fixed CSV parsing functionality - Resolves customer attribution issues"""

import pandas as pd
import re
from typing import List, Tuple, Optional, Dict
from datetime import datetime, date
from models import (
    Invoice, PaymentPlan, Customer, PaymentFrequency, 
    CustomerIssue, IssueSeverity, ErrorType, DataQualityReport
)

class EnhancedPaymentPlanParser:
    """Fixed parser with correct customer attribution logic"""
    
    def __init__(self):
        self.raw_data = None
        self.customers = {}
        self.data_quality_report = None
        self.errors_found = []
        self.total_rows_processed = 0
        self.total_invoices_ignored = 0
        
        # Enhanced typo corrections
        self.payment_term_corrections = {
            'quaterly': 'quarterly',
            'qtrly': 'quarterly',
            'montly': 'monthly',
            'monthl;y': 'monthly',
            'bimonthly': 'bimonthly',
            'bi-monthly': 'bimonthly',
            'a month': 'monthly',
            'month': 'monthly',
            'per month': 'monthly'
        }
        
    def load_csv(self, file_path: str) -> pd.DataFrame:
        """Load CSV file with enhanced error tracking"""
        try:
            self.raw_data = pd.read_csv(file_path, header=0)
            self.total_rows_processed = len(self.raw_data)
        except Exception as e:
            raise ValueError(f"Failed to load CSV: {str(e)}")
        
        # Standardize column names
        column_mapping = {
            'Unnamed: 0': '_0',
            'Unnamed: 1': '_1', 
            'Unnamed: 2': '_2',
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in self.raw_data.columns:
                self.raw_data.rename(columns={old_col: new_col}, inplace=True)
                
        return self.raw_data
    
    def parse_amount(self, value) -> Tuple[float, Optional[str]]:
        """Convert amount with enhanced error tracking"""
        error = None
        if pd.isna(value) or value == '':
            return 0.0, None
        if isinstance(value, (int, float)):
            return float(value), None
        
        original_value = str(value)
        cleaned = original_value.replace('$', '').replace(',', '').strip()
        
        # Check for Excel errors
        if '#REF!' in original_value:
            error = "Excel reference error"
            return 0.0, error
        elif not re.match(r'^[\d.,\s$-]+$', original_value.replace('#REF!', '')):
            error = f"Invalid characters in amount: {original_value}"
            
        try:
            return float(cleaned) if cleaned and cleaned != '' else 0.0, error
        except:
            return 0.0, f"Cannot parse amount: {original_value}"
    
    def parse_date(self, date_str) -> Tuple[Optional[datetime], Optional[str]]:
        """Parse date with enhanced validation"""
        if pd.isna(date_str):
            return None, None
            
        try:
            parsed_date = pd.to_datetime(date_str)
            
            # Check for future dates (flag but don't reject)
            current_date = datetime.now().date()
            if parsed_date.date() > current_date:
                days_in_future = (parsed_date.date() - current_date).days
                if days_in_future > 365:
                    return parsed_date, f"Date far in future: {date_str}"
                else:
                    return parsed_date, f"Future date: {date_str}"
            
            return parsed_date, None
        except:
            return None, f"Invalid date format: {date_str}"
    
    def normalize_payment_terms(self, terms: str) -> Tuple[float, PaymentFrequency, List[str]]:
        """Enhanced payment terms parsing with better pattern recognition"""
        issues_found = []
        
        if pd.isna(terms) or not terms:
            return (0.0, PaymentFrequency.UNDEFINED, issues_found)
        
        original_terms = str(terms).strip()
        terms_lower = original_terms.lower()
        
        # Check for typos and suggest corrections
        for typo, correction in self.payment_term_corrections.items():
            if typo in terms_lower and typo != correction:
                issues_found.append({
                    'original': original_terms,
                    'typo': typo,
                    'suggested': correction,
                    'field': 'payment_terms',
                    'type': 'typo'
                })
                terms_lower = terms_lower.replace(typo, correction)
        
        # Extract amount with improved regex
        amount_match = re.search(r'(\d+(?:\.\d{2})?)', terms_lower)
        amount = float(amount_match.group(1)) if amount_match else 0.0
        
        # Determine frequency
        if any(term in terms_lower for term in ['bimonthly', 'bi-monthly']):
            frequency = PaymentFrequency.BIMONTHLY
        elif any(term in terms_lower for term in ['quarterly', 'qtrly']):
            frequency = PaymentFrequency.QUARTERLY
        elif any(term in terms_lower for term in ['monthly', 'month', 'per month', 'a month']):
            frequency = PaymentFrequency.MONTHLY
        else:
            frequency = PaymentFrequency.UNDEFINED
            if amount > 0:
                issues_found.append({
                    'original': original_terms,
                    'issue': 'unclear_frequency',
                    'suggested': 'Specify monthly, quarterly, or bimonthly',
                    'field': 'payment_terms',
                    'type': 'unclear_terms'
                })
            
        return (amount, frequency, issues_found)
    
    def parse_customers(self) -> Dict[str, Customer]:
        """FIXED customer parsing with proper invoice attribution"""
        if self.raw_data is None:
            raise ValueError("No data loaded. Call load_csv first.")
        
        # Store all customer data as we parse
        all_customer_data = {}
        current_customer = None
        total_invoices_processed = 0
        classes_found = set()
        
        print(f"🔍 Starting to parse {len(self.raw_data)} rows...")
        
        for idx, row in self.raw_data.iterrows():
            # Skip completely empty rows
            if row.isna().all():
                continue
                
            # Debug: Print processing info for first few rows
            if idx < 10:
                print(f"Row {idx}: _1='{row.get('_1', '')}', Type='{row.get('Type', '')}', Open Balance='{row.get('Open Balance', '')}'")
            
            # CASE 1: Invoice row - process invoice
            if row.get('Type') == 'Invoice':
                total_invoices_processed += 1
                
                # Parse amounts first to determine if we should process this invoice
                open_balance, balance_error = self.parse_amount(row.get('Open Balance'))
                original_amount, amount_error = self.parse_amount(row.get('Amount'))
                
                # ONLY process invoices with open balance > 0
                if open_balance > 0:
                    # Determine which customer this invoice belongs to
                    invoice_customer = None
                    
                    # Check if customer name is in same row (_1 column)
                    if pd.notna(row.get('_1', '')) and str(row.get('_1', '')).strip():
                        potential_customer = str(row.get('_1', '')).strip()
                        if not self._is_total_row_text(potential_customer):
                            invoice_customer = potential_customer
                    
                    # If no customer in same row, use the last known customer
                    if not invoice_customer and current_customer:
                        invoice_customer = current_customer
                    
                    if invoice_customer:
                        # Parse the invoice
                        invoice = self._parse_invoice_row(row, idx)
                        
                        # Initialize customer data if first time seeing this customer
                        if invoice_customer not in all_customer_data:
                            all_customer_data[invoice_customer] = []
                            print(f"📝 New customer found: {invoice_customer}")
                        
                        # Add invoice to customer
                        all_customer_data[invoice_customer].append(invoice)
                        
                        # Track classes
                        if invoice.class_field:
                            classes_found.add(invoice.class_field)
                        
                        print(f"   ✅ Added invoice {invoice.invoice_number} to {invoice_customer} (${open_balance:.2f})")
                    else:
                        print(f"   ❌ No customer found for invoice at row {idx}")
                else:
                    # Track ignored invoices (paid off)
                    self.total_invoices_ignored += 1
                    
                # Track parsing errors
                if balance_error or amount_error:
                    self._track_parsing_error(current_customer or f"Row {idx}", 
                                            balance_error or amount_error, idx)
            
            # CASE 2: Customer name row (not an invoice, has name in _1 or _2)
            elif self._is_customer_name_row(row):
                potential_customer = str(row.get('_1', '')).strip()
                if potential_customer and not self._is_total_row_text(potential_customer):
                    current_customer = potential_customer
                    print(f"🏷️  Customer header found: {current_customer}")
            
            # CASE 3: Nested customer (name in _2 column)
            elif self._is_nested_customer_row(row):
                nested_customer = str(row.get('_2', '')).strip()
                if nested_customer and not self._is_total_row_text(nested_customer):
                    current_customer = nested_customer
                    print(f"🏷️  Nested customer found: {current_customer}")
            
            # CASE 4: Total row - signals end of customer section
            elif self._is_total_row(row):
                total_customer = self._extract_customer_from_total(row)
                if total_customer:
                    print(f"🏁 Total row for: {total_customer}")
                current_customer = None  # Reset current customer
        
        print(f"\n📊 Parsing complete:")
        print(f"   Total invoices processed: {total_invoices_processed}")
        print(f"   Invoices with open balance: {total_invoices_processed - self.total_invoices_ignored}")
        print(f"   Customers found: {len(all_customer_data)}")
        
        # Now create Customer objects from parsed data
        for customer_name, invoices in all_customer_data.items():
            if invoices:  # Only create customer if they have invoices
                print(f"\n🏗️  Creating customer object for {customer_name} with {len(invoices)} invoices")
                self._create_customer_object(customer_name, invoices, classes_found)
        
        # Generate data quality report
        self._generate_data_quality_report(total_invoices_processed, classes_found)
        
        print(f"\n✅ Final result: {len(self.customers)} customers created")
        return self.customers
    
    def _create_customer_object(self, customer_name: str, invoices: List[Invoice], classes_found: set):
        """Create a Customer object with proper payment plan consolidation"""
        if not invoices:
            return
        
        # FIXED: Group invoices by normalized payment terms to avoid over-segmentation
        plans_by_terms = {}
        
        for inv in invoices:
            # Normalize payment terms to group similar ones together
            normalized_terms = self._normalize_terms_key(inv.payment_terms)
            
            if normalized_terms not in plans_by_terms:
                plans_by_terms[normalized_terms] = []
            plans_by_terms[normalized_terms].append(inv)
        
        print(f"   📋 Customer {customer_name} has {len(plans_by_terms)} distinct payment term groups:")
        for terms, plan_invoices in plans_by_terms.items():
            print(f"      - '{terms}': {len(plan_invoices)} invoices")
        
        # Create customer with consolidated payment plans
        customer = Customer(customer_name=customer_name)
        
        for plan_idx, (terms_key, plan_invoices) in enumerate(plans_by_terms.items()):
            plan_id = f"{customer_name}_plan_{plan_idx + 1}"
            
            # Calculate totals for this plan
            total_original = sum(inv.original_amount for inv in plan_invoices)
            total_open = sum(inv.open_balance for inv in plan_invoices)
            
            # Get dates
            dates = [inv.date for inv in plan_invoices if inv.date]
            earliest_date = min(dates) if dates else None
            latest_date = max(dates) if dates else None
            
            # Parse payment terms
            monthly_amount, frequency, typos = self.normalize_payment_terms(terms_key)
            
            # Track typos
            for typo_info in typos:
                self._track_typo(customer_name, typo_info)
            
            # Determine dominant class for this plan
            plan_classes = [inv.class_field for inv in plan_invoices if inv.class_field]
            dominant_class = max(set(plan_classes), key=plan_classes.count) if plan_classes else None
            
            payment_plan = PaymentPlan(
                customer_name=customer_name,
                plan_id=plan_id,
                monthly_amount=monthly_amount,
                frequency=frequency,
                total_original=total_original,
                total_open=total_open,
                invoices=plan_invoices,
                earliest_date=earliest_date,
                latest_date=latest_date,
                class_filter=dominant_class,
                payment_terms_raw=terms_key if terms_key != "no_terms" else None
            )
            
            customer.payment_plans.append(payment_plan)
        
        # Set customer-level properties
        customer.total_open_balance = sum(plan.total_open for plan in customer.payment_plans)
        customer.total_original_amount = sum(plan.total_original for plan in customer.payment_plans)
        customer.has_multiple_plans = len(customer.payment_plans) > 1
        customer.all_classes = list(set(inv.class_field for plan in customer.payment_plans 
                                      for inv in plan.invoices if inv.class_field))
        
        # Set overall dates
        all_dates = [plan.earliest_date for plan in customer.payment_plans if plan.earliest_date]
        customer.earliest_date = min(all_dates) if all_dates else None
        all_dates = [plan.latest_date for plan in customer.payment_plans if plan.latest_date]
        customer.latest_date = max(all_dates) if all_dates else None
        
        self.customers[customer_name] = customer
        print(f"   ✅ Created customer with {len(customer.payment_plans)} payment plans, total open: ${customer.total_open_balance:.2f}")
    
    def _normalize_terms_key(self, payment_terms: str) -> str:
        """Normalize payment terms to prevent over-segmentation of payment plans"""
        if not payment_terms or pd.isna(payment_terms):
            return "no_terms"
        
        terms = str(payment_terms).strip().lower()
        
        # Apply typo corrections
        for typo, correction in self.payment_term_corrections.items():
            terms = terms.replace(typo, correction)
        
        # Standardize common variations
        terms = re.sub(r'\s+', ' ', terms)  # normalize whitespace
        terms = terms.replace('per month', 'monthly')
        terms = terms.replace('a month', 'monthly')
        terms = terms.replace('each month', 'monthly')
        
        return terms if terms != "" else "no_terms"
    
    def _parse_invoice_row(self, row, row_index: int) -> Invoice:
        """Parse invoice with enhanced error tracking"""
        # Parse amounts with error tracking
        open_balance, balance_error = self.parse_amount(row.get('Open Balance'))
        original_amount, amount_error = self.parse_amount(row.get('Amount'))
        
        # Parse date with error tracking  
        date_value, date_error = self.parse_date(row.get('Date'))
        
        # Get invoice number with special marker detection
        invoice_num = str(row.get('Num', '')) if pd.notna(row.get('Num')) else ''
        
        # Check for special markers
        if '*' in invoice_num:
            self._track_field_error('Invoice Number', f'Asterisk marker in {invoice_num}', invoice_num, row_index)
        if '/' in invoice_num:
            self._track_field_error('Invoice Number', f'Slash notation in {invoice_num}', invoice_num, row_index)
        
        # Get payment terms
        payment_terms = str(row.get('FOB', '')) if pd.notna(row.get('FOB')) else None
        
        # Get class field
        class_field = str(row.get('Class', '')) if pd.notna(row.get('Class')) else None
        
        # Track errors for this invoice
        if balance_error:
            self._track_field_error('Open Balance', balance_error, invoice_num, row_index)
        if amount_error:
            self._track_field_error('Amount', amount_error, invoice_num, row_index)
        if date_error:
            self._track_field_error('Date', date_error, invoice_num, row_index)
        if not class_field:
            self._track_field_error('Class', 'Missing class field', invoice_num, row_index)
            
        return Invoice(
            invoice_number=invoice_num,
            date=date_value,
            payment_terms=payment_terms,
            original_amount=original_amount,
            open_balance=open_balance,
            class_field=class_field,
            raw_data=row.to_dict()
        )
    
    def _is_customer_name_row(self, row) -> bool:
        """Check if row contains a customer name"""
        return (pd.notna(row.get('_1', '')) and 
                row.get('Type') != 'Invoice' and 
                not self._is_total_row_text(str(row.get('_1', ''))))
    
    def _is_nested_customer_row(self, row) -> bool:
        """Check if row contains a nested customer"""
        return (pd.notna(row.get('_2', '')) and 
                row.get('Type') != 'Invoice' and 
                not self._is_total_row_text(str(row.get('_2', ''))))
    
    def _is_total_row(self, row) -> bool:
        """Check if row is a total row"""
        return (pd.notna(row.get('_1', '')) and 
                self._is_total_row_text(str(row.get('_1', ''))))
    
    def _is_total_row_text(self, text: str) -> bool:
        """Check if text indicates a total row"""
        text_clean = text.strip().lower()
        return text_clean.startswith(('total', 'TOTAL')) or text_clean == 'total'
    
    def _extract_customer_from_total(self, row) -> Optional[str]:
        """Extract customer name from total row"""
        total_text = str(row.get('_1', '')).strip()
        if total_text.lower().startswith('total '):
            return total_text[6:].strip()  # Remove "Total " prefix
        return None
    
    def _track_parsing_error(self, customer_name: str, error: str, row_index: int):
        """Track parsing errors"""
        self.errors_found.append({
            'customer': customer_name,
            'error': error,
            'row': row_index,
            'type': 'parsing_error'
        })
    
    def _track_field_error(self, field_name: str, error: str, invoice_num: str, row_index: int):
        """Track field-specific errors"""
        self.errors_found.append({
            'field': field_name,
            'error': error,
            'invoice': invoice_num,
            'row': row_index,
            'type': 'field_error'
        })
    
    def _track_typo(self, customer_name: str, typo_info: Dict):
        """Track typos found"""
        self.errors_found.append({
            'customer': customer_name,
            'typo_info': typo_info,
            'type': 'typo'
        })
    
    def _generate_data_quality_report(self, total_invoices_processed: int, classes_found: set):
        """Generate comprehensive data quality report"""
        self.data_quality_report = DataQualityReport(
            timestamp=datetime.now(),
            total_rows_processed=self.total_rows_processed,
            total_customers_found=len(self.customers),
            total_invoices_processed=total_invoices_processed,
            total_invoices_with_open_balance=total_invoices_processed - self.total_invoices_ignored,
            total_invoices_ignored=self.total_invoices_ignored,
            classes_found=sorted(list(classes_found))
        )
        
        # Categorize errors
        for error in self.errors_found:
            error_type = error.get('type', 'unknown')
            self.data_quality_report.errors_by_type[error_type] = \
                self.data_quality_report.errors_by_type.get(error_type, 0) + 1