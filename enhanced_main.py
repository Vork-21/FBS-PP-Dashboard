"""Enhanced main orchestration for payment plan analysis - Phase 1"""

from typing import Dict, List
import sys
import pandas as pd

# Import enhanced modules
from enhanced_parsers import EnhancedPaymentPlanParser
from enhanced_analyzers import EnhancedIssueAnalyzer
from enhanced_calculators import EnhancedPaymentCalculator
from enhanced_reporters import EnhancedReportGenerator
from payment_projections import PaymentProjectionCalculator


class EnhancedPaymentPlanAnalysisSystem:
    """Enhanced system orchestrating all components with multi-plan support"""
    
    def __init__(self, output_dir: str = './reports'):
        self.parser = EnhancedPaymentPlanParser()
        self.analyzer = EnhancedIssueAnalyzer()
        self.calculator = EnhancedPaymentCalculator()
        self.reporter = EnhancedReportGenerator(output_dir)
        self.results = None
        
    def analyze_file(self, csv_path: str, class_filter: str = None) -> Dict:
        """Run complete enhanced analysis on a CSV file"""
        
        print("\n" + "="*80)
        print("ENHANCED PAYMENT PLAN ANALYSIS SYSTEM")
        print("="*80 + "\n")
        
        # Step 1: Load and parse data (only unpaid invoices)
        print("📂 Loading CSV file...")
        try:
            self.parser.load_csv(csv_path)
            print("✅ File loaded successfully")
        except Exception as e:
            print(f"❌ Error loading file: {str(e)}")
            return None
        
        print("\n📊 Parsing customer data (focusing on unpaid invoices only)...")
        customers = self.parser.parse_customers()
        total_plans = sum(len(c.payment_plans) for c in customers.values())
        customers_with_multiple_plans = sum(1 for c in customers.values() if c.has_multiple_plans)
        
        print(f"✅ Found {len(customers)} customers with {total_plans} payment plans")
        print(f"   📋 {customers_with_multiple_plans} customers have multiple payment plans")
        
        # Show data quality summary
        if self.parser.data_quality_report:
            report = self.parser.data_quality_report
            print(f"   📊 Processed {report.total_invoices_processed} invoices")
            print(f"   💰 {report.total_invoices_with_open_balance} with open balances")
            print(f"   ✅ {report.total_invoices_ignored} paid invoices ignored")
            print(f"   🏷️  Classes found: {', '.join(report.classes_found)}")
        
        # Step 2: Analyze data quality
        print("\n🔍 Analyzing data quality...")
        categorized = self.analyzer.analyze_all_customers(customers)
        clean_customers = categorized['clean']
        problematic_customers = categorized['problematic']
        
        print(f"  ✅ Clean customers: {len(clean_customers)}")
        print(f"  ⚠️  Problematic customers: {len(problematic_customers)}")
        print(f"  📋 Total issues found: {len(self.analyzer.issues)}")
        
        # Show issue breakdown
        issue_summary = self.analyzer.get_issue_summary()
        if issue_summary:
            print("\n  Issue types found:")
            for issue_type, count in sorted(issue_summary.items(), key=lambda x: x[1], reverse=True):
                print(f"    - {issue_type.replace('_', ' ').title()}: {count}")
        
        # Step 3: Calculate metrics for clean customers
        print("\n💰 Calculating payment metrics...")
        all_metrics = []
        for customer in clean_customers:
            customer_metrics = self.calculator.calculate_customer_metrics(customer)
            all_metrics.extend(customer_metrics)
        
        print(f"✅ Calculated metrics for {len(all_metrics)} payment plans")
        print(f"   👥 Covering {len(set(m.customer_name for m in all_metrics))} customers")
        
        # Apply class filter if specified
        if class_filter:
            filtered_metrics = [m for m in all_metrics if m.class_field == class_filter]
            print(f"🏷️  Filtered to {len(filtered_metrics)} plans in class '{class_filter}'")
            all_metrics = filtered_metrics
        
        # Calculate portfolio metrics
        portfolio_metrics = self.calculator.calculate_portfolio_metrics(all_metrics)
        print(f"\n  Portfolio summary:")
        print(f"    - Total customers tracked: {portfolio_metrics['total_customers']}")
        print(f"    - Total plans tracked: {portfolio_metrics['total_plans']}")
        print(f"    - Total tracked balance: ${portfolio_metrics['total_outstanding']:,.2f}")
        print(f"    - Expected monthly: ${portfolio_metrics['expected_monthly']:,.2f}")
        print(f"    - Customers behind: {portfolio_metrics['customers_behind']} ({portfolio_metrics['percentage_behind']:.1f}%)")
        
        # Show class breakdown
        if portfolio_metrics['plans_by_class']:
            print(f"\n  Breakdown by class:")
            for class_name, data in sorted(portfolio_metrics['plans_by_class'].items(), 
                                         key=lambda x: x[1]['total_owed'], reverse=True):
                print(f"    - {class_name}: {data['count']} plans, ${data['total_owed']:,.2f}")
        
        # Step 4: Generate enhanced reports
        print("\n📝 Generating enhanced reports...")
        quality_report = self.reporter.generate_comprehensive_quality_report(
            customers, 
            clean_customers,
            problematic_customers,
            self.analyzer.issues,
            self.parser.data_quality_report
        )
        
        dashboard_data = self.reporter.generate_enhanced_dashboard_data(
            customers,
            clean_customers,
            problematic_customers,
            all_metrics
        )
        
        timestamp = self.reporter.save_all_reports(
            quality_report,
            dashboard_data,
            self.analyzer.issues,
            all_metrics,
            customers
        )
        
        # Step 5: Display enhanced summary
        self._print_enhanced_summary(quality_report, dashboard_data, portfolio_metrics)
        
        # Store results
        self.results = {
            'quality_report': quality_report,
            'dashboard_data': dashboard_data,
            'portfolio_metrics': portfolio_metrics,
            'timestamp': timestamp,
            'all_customers': customers,
            'all_metrics': all_metrics,
            'data_quality_report': self.parser.data_quality_report
        }
        
        return self.results
    
    def get_customer_details(self, customer_name: str) -> Dict:
        """Get detailed information for a specific customer"""
        if not self.results:
            print("⚠️  No analysis results available. Run analyze_file first.")
            return None
        
        customers = self.results['all_customers']
        customer = customers.get(customer_name)
        
        if not customer:
            print(f"❌ Customer '{customer_name}' not found.")
            return None
        
        # Get metrics for this customer
        customer_metrics = [m for m in self.results['all_metrics'] if m.customer_name == customer_name]
        
        return {
            'customer_info': {
                'name': customer.customer_name,
                'total_plans': len(customer.payment_plans),
                'total_open_balance': customer.total_open_balance,
                'all_classes': customer.all_classes,
                'has_multiple_plans': customer.has_multiple_plans
            },
            'payment_plans': [{
                'plan_id': plan.plan_id,
                'monthly_amount': plan.monthly_amount,
                'frequency': plan.frequency.value,
                'total_open': plan.total_open,
                'class_filter': plan.class_filter,
                'has_issues': plan.has_issues,
                'issues': [issue.to_dict() for issue in plan.issues]
            } for plan in customer.payment_plans],
            'metrics': [m.__dict__ for m in customer_metrics],
            'payment_roadmaps': [m.payment_roadmap for m in customer_metrics]
        }
    
    def get_customers_by_class(self, class_name: str) -> List[Dict]:
        """Get all customers in a specific class"""
        if not self.results:
            return []
        
        customers = self.results['all_customers']
        class_customers = []
        
        for customer in customers.values():
            if class_name in customer.all_classes:
                class_customers.append({
                    'customer_name': customer.customer_name,
                    'total_open_balance': customer.total_open_balance,
                    'total_plans': len(customer.payment_plans),
                    'has_issues': any(plan.has_issues for plan in customer.payment_plans)
                })
        
        return sorted(class_customers, key=lambda x: x['total_open_balance'], reverse=True)
    
    def get_collection_priorities(self, class_filter: str = None) -> List[Dict]:
        """Get prioritized list for collections"""
        if not self.results:
            return []
        
        metrics = self.results['all_metrics']
        if class_filter:
            metrics = [m for m in metrics if m.class_field == class_filter]
        
        prioritized = self.calculator.prioritize_collections(metrics)
        
        return [{
            'customer_name': m.customer_name,
            'plan_id': m.plan_id,
            'months_behind': m.months_behind,
            'total_owed': m.total_owed,
            'payment_difference': m.payment_difference,
            'class_field': m.class_field,
            'recovery_scenarios': self.calculator.calculate_recovery_scenarios(m)
        } for m in prioritized[:20]]  # Top 20
    
    def export_for_excel(self, output_path: str = None, include_roadmaps: bool = True):
        """Export enhanced analysis results to Excel"""
        if not self.results:
            print("⚠️  No analysis results available. Run analyze_file first.")
            return
        
        if not output_path:
            output_path = f"enhanced_payment_analysis_{self.results['timestamp']}.xlsx"
        
        # Create Excel writer
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Sheet 1: Executive Summary
            summary_data = {
                'Metric': [
                    'Total Customers',
                    'Customers with Multiple Plans',
                    'Total Payment Plans',
                    'Clean Customers',
                    'Problematic Customers',
                    'Total Outstanding (All)',
                    'Total Outstanding (Tracked)',
                    'Total Outstanding (Untracked)',
                    'Expected Monthly Collection',
                    'Customers Behind',
                    'Data Quality Score (%)'
                ],
                'Value': [
                    self.results['quality_report']['summary']['total_customers'],
                    self.results['quality_report']['summary']['customers_with_multiple_plans'],
                    self.results['quality_report']['summary']['total_payment_plans'],
                    self.results['quality_report']['summary']['clean_customers'],
                    self.results['quality_report']['summary']['problematic_customers'],
                    f"${self.results['quality_report']['summary']['total_outstanding']:,.2f}",
                    f"${self.results['dashboard_data']['summary_metrics']['total_outstanding_tracked']:,.2f}",
                    f"${self.results['dashboard_data']['summary_metrics']['total_outstanding_untracked']:,.2f}",
                    f"${self.results['dashboard_data']['summary_metrics']['expected_monthly_collection']:,.2f}",
                    self.results['dashboard_data']['summary_metrics']['customers_behind'],
                    f"{self.results['quality_report']['summary']['data_quality_score']:.1f}%"
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Executive Summary', index=False)
            
            # Sheet 2: Customer Summaries
            if self.results['dashboard_data']['customer_summaries']:
                customer_df = pd.DataFrame(self.results['dashboard_data']['customer_summaries'])
                # Flatten plan details for the summary
                customer_df = customer_df.drop('plan_details', axis=1)
                customer_df.to_excel(writer, sheet_name='Customer Summaries', index=False)
            
            # Sheet 3: Payment Plan Details
            if self.results['dashboard_data']['payment_plan_details']:
                plans_df = pd.DataFrame(self.results['dashboard_data']['payment_plan_details'])
                if not include_roadmaps:
                    plans_df = plans_df.drop('payment_roadmap', axis=1, errors='ignore')
                plans_df.to_excel(writer, sheet_name='Payment Plan Details', index=False)
            
            # Sheet 4: Class Analysis
            if self.results['dashboard_data']['class_summaries']:
                class_data = []
                for class_name, data in self.results['dashboard_data']['class_summaries'].items():
                    class_data.append({
                        'Class': class_name,
                        'Total Customers': data['total_customers'],
                        'Total Plans': data['total_plans'],
                        'Total Owed': data['total_owed'],
                        'Customers Behind': data['customers_behind'],
                        'Expected Monthly': data['expected_monthly']
                    })
                pd.DataFrame(class_data).to_excel(writer, sheet_name='Class Analysis', index=False)
            
            # Sheet 5: Problematic Customers
            if self.results['dashboard_data']['skipped_customers']:
                problem_df = pd.DataFrame(self.results['dashboard_data']['skipped_customers'])
                problem_df.to_excel(writer, sheet_name='Problematic Customers', index=False)
        
        print(f"\n📊 Enhanced Excel report saved: {output_path}")
    
    def _print_enhanced_summary(self, quality_report: Dict, dashboard_data: Dict, portfolio_metrics: Dict):
        """Print enhanced analysis summary"""
        print("\n" + "="*80)
        print("ENHANCED ANALYSIS COMPLETE")
        print("="*80)
        
        print(f"\n📊 OVERVIEW:")
        print(f"  Total Customers: {quality_report['summary']['total_customers']}")
        print(f"  - Clean: {quality_report['summary']['clean_customers']} ({quality_report['summary']['data_quality_score']:.1f}%)")
        print(f"  - Problematic: {quality_report['summary']['problematic_customers']} ({quality_report['summary']['percentage_with_issues']:.1f}%)")
        print(f"  - With Multiple Plans: {quality_report['summary']['customers_with_multiple_plans']}")
        print(f"  Total Payment Plans: {quality_report['summary']['total_payment_plans']}")
        print(f"  Total Outstanding: ${quality_report['summary']['total_outstanding']:,.2f}")
        
        print(f"\n💵 FINANCIAL TRACKING:")
        print(f"  Tracked: ${dashboard_data['summary_metrics']['total_outstanding_tracked']:,.2f}")
        print(f"  Untracked: ${dashboard_data['summary_metrics']['total_outstanding_untracked']:,.2f}")
        percentage_tracked = (dashboard_data['summary_metrics']['total_outstanding_tracked'] / 
                            quality_report['summary']['total_outstanding'] * 100 
                            if quality_report['summary']['total_outstanding'] > 0 else 0)
        print(f"  Coverage: {percentage_tracked:.1f}% of total balance is trackable")
        print(f"  Expected Monthly: ${dashboard_data['summary_metrics']['expected_monthly_collection']:,.2f}")
        
        print(f"\n📋 DATA PROCESSING:")
        print(f"  Rows Processed: {quality_report['data_processing']['total_rows_processed']}")
        print(f"  Invoices Processed: {quality_report['data_processing']['total_invoices_processed']}")
        print(f"  Unpaid Invoices: {quality_report['data_processing']['invoices_with_open_balance']}")
        print(f"  Paid Invoices Ignored: {quality_report['data_processing']['invoices_ignored_zero_balance']}")
        
        if quality_report['data_processing']['classes_found']:
            print(f"  Classes Found: {', '.join(quality_report['data_processing']['classes_found'])}")
        
        print(f"\n🚨 CRITICAL ISSUES:")
        critical_issues = quality_report.get('critical_issues_requiring_immediate_attention', [])
        if critical_issues:
            for issue in critical_issues[:3]:  # Top 3
                print(f"  - {issue['issue_type']}: {issue['customers_affected']} customers affected")
        else:
            print("  No critical issues found! 🎉")
        
        if quality_report['recommendations']:
            print(f"\n🎯 TOP RECOMMENDATIONS:")
            for i, rec in enumerate(quality_report['recommendations'][:3], 1):
                print(f"  {i}. {rec['action']}")
                print(f"     Impact: {rec['impact']}")
                if 'affected_balance' in rec:
                    print(f"     Amount: ${rec['affected_balance']:,.2f}")
                print(f"     Urgency: {rec.get('urgency', 'Medium')}")
        
        print(f"\n✅ Enhanced reports saved with timestamp: {self.reporter.timestamp}")
        print(f"📁 Location: {self.reporter.output_dir}/")
        print("📊 Error-highlighted Excel file generated for data cleanup")

    def get_payment_projections(self, months_ahead: int = 12, scenario: str = 'current', class_filter: str = None) -> Dict:
        """Get payment projections using the Python calculator"""
        if not self.results:
            print("⚠️  No analysis results available. Run analyze_file first.")
            return None
        
        try:
            calculator = PaymentProjectionCalculator()
            
            # Get customer data
            customers_data = self.results['all_customers']
            
            # Apply class filter if specified
            if class_filter:
                filtered_customers = {}
                for name, customer in customers_data.items():
                    if class_filter in customer.all_classes:
                        filtered_customers[name] = customer
                customers_data = filtered_customers
            
            # Calculate projections
            projections = calculator.calculate_customer_projections(
                customers_data, months_ahead, scenario
            )
            
            # Generate portfolio summary
            portfolio_summary = calculator.generate_portfolio_summary(projections, months_ahead)
            
            return {
                'customer_projections': [
                    {
                        'customer_name': proj.customer_name,
                        'total_monthly_payment': proj.total_monthly_payment,
                        'total_owed': proj.total_owed,
                        'completion_month': proj.completion_month,
                        'plan_count': proj.plan_count,
                        'timeline': proj.timeline
                    } for proj in projections
                ],
                'portfolio_summary': portfolio_summary,
                'parameters': {
                    'months_ahead': months_ahead,
                    'scenario': scenario,
                    'class_filter': class_filter,
                    'total_customers': len(projections)
                }
            }
            
        except Exception as e:
            print(f"❌ Error calculating projections: {str(e)}")
            return None

    def get_customer_projection_details(self, customer_name: str, months_ahead: int = 12, scenario: str = 'current') -> Dict:
        """Get detailed projection for a specific customer"""
        if not self.results:
            print("⚠️  No analysis results available. Run analyze_file first.")
            return None
        
        customers = self.results['all_customers']
        if customer_name not in customers:
            print(f"❌ Customer '{customer_name}' not found.")
            return None
        
        try:
            calculator = PaymentProjectionCalculator()
            
            # Calculate projections for this customer only
            single_customer_data = {customer_name: customers[customer_name]}
            projections = calculator.calculate_customer_projections(
                single_customer_data, months_ahead, scenario
            )
            
            if not projections:
                print(f"❌ No valid projections for customer '{customer_name}'")
                return None
            
            # Get detailed info
            customer_details = calculator.get_customer_details(customer_name, projections)
            return customer_details
            
        except Exception as e:
            print(f"❌ Error calculating customer projection: {str(e)}")
            return None

    def analyze_projection_scenarios(self, customer_name: str = None, class_filter: str = None) -> Dict:
        """Analyze different projection scenarios (current vs restart)"""
        if not self.results:
            return None
        
        try:
            current_projections = self.get_payment_projections(12, 'current', class_filter)
            restart_projections = self.get_payment_projections(12, 'restart', class_filter)
            
            if not current_projections or not restart_projections:
                return None
            
            # Compare scenarios
            current_total = current_projections['portfolio_summary']['summary']['total_expected_collection']
            restart_total = restart_projections['portfolio_summary']['summary']['total_expected_collection']
            
            improvement = restart_total - current_total
            improvement_percentage = (improvement / current_total * 100) if current_total > 0 else 0
            
            return {
                'current_scenario': current_projections,
                'restart_scenario': restart_projections,
                'comparison': {
                    'current_total': current_total,
                    'restart_total': restart_total,
                    'improvement_amount': improvement,
                    'improvement_percentage': improvement_percentage,
                    'recommendation': 'Consider customer outreach for payment plan restart' if improvement > 0 else 'Current trajectory is optimal'
                }
            }
            
        except Exception as e:
            print(f"❌ Error analyzing projection scenarios: {str(e)}")
            return None

    def export_projections_to_excel(self, output_path: str = None, months_ahead: int = 12, include_scenarios: bool = True):
        """Export payment projections to Excel with multiple scenarios"""
        if not self.results:
            print("⚠️  No analysis results available. Run analyze_file first.")
            return
        
        if not output_path:
            output_path = f"payment_projections_{self.results['timestamp']}.xlsx"
        
        try:
            import pandas as pd
            
            # Get projections for both scenarios
            current_projections = self.get_payment_projections(months_ahead, 'current')
            restart_projections = self.get_payment_projections(months_ahead, 'restart') if include_scenarios else None
            
            if not current_projections:
                print("❌ Could not generate projections for export")
                return
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                
                # Sheet 1: Projection Summary
                summary_data = {
                    'Metric': [
                        'Total Customers with Projections',
                        'Total Expected Monthly (Current)',
                        'Total 12-Month Collection (Current)',
                        'Average Completion Time (months)',
                        'Customers On Track',
                        'Customers Behind'
                    ],
                    'Current Scenario': [
                        current_projections['parameters']['total_customers'],
                        f"${current_projections['portfolio_summary']['summary']['average_monthly']:,.2f}",
                        f"${current_projections['portfolio_summary']['summary']['total_expected_collection']:,.2f}",
                        0,  # Would need to calculate
                        0,  # Would need to calculate  
                        0   # Would need to calculate
                    ]
                }
                
                if restart_projections:
                    summary_data['Restart Scenario'] = [
                        restart_projections['parameters']['total_customers'],
                        f"${restart_projections['portfolio_summary']['summary']['average_monthly']:,.2f}",
                        f"${restart_projections['portfolio_summary']['summary']['total_expected_collection']:,.2f}",
                        0,  # Would need to calculate
                        0,  # Would need to calculate
                        0   # Would need to calculate
                    ]
                
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Projection Summary', index=False)
                
                # Sheet 2: Customer Projections (Current)
                customer_data = []
                for customer in current_projections['customer_projections']:
                    customer_data.append({
                        'Customer': customer['customer_name'],
                        'Monthly Payment': customer['total_monthly_payment'],
                        'Total Owed': customer['total_owed'],
                        'Plans': customer['plan_count'],
                        'Completion Month': customer['completion_month'],
                        'Total Projected': sum(month['monthly_payment'] for month in customer['timeline'])
                    })
                
                pd.DataFrame(customer_data).to_excel(writer, sheet_name='Customer Projections', index=False)
                
                # Sheet 3: Monthly Schedule (Current)
                monthly_data = []
                for month in current_projections['portfolio_summary']['monthly_projections']:
                    monthly_data.append({
                        'Month': month['month'],
                        'Date': month['date'][:10],
                        'Expected Payment': month['expected_payment'],
                        'Active Customers': month['active_customers'],
                        'Completing Customers': month['completing_customers'],
                        'Cumulative Total': month['cumulative_total']
                    })
                
                pd.DataFrame(monthly_data).to_excel(writer, sheet_name='Monthly Schedule', index=False)
                
                # Sheet 4: Detailed Customer Timeline (Top 10 customers)
                detailed_timeline = []
                top_customers = sorted(current_projections['customer_projections'], 
                                     key=lambda x: x['total_monthly_payment'], reverse=True)[:10]
                
                for customer in top_customers:
                    for month in customer['timeline']:
                        if month['monthly_payment'] > 0:  # Only include payment months
                            detailed_timeline.append({
                                'Customer': customer['customer_name'],
                                'Month': month['month'],
                                'Date': month['date'][:10],
                                'Payment Amount': month['monthly_payment'],
                                'Active Plans': month['active_plans'],
                                'Plan Details': '; '.join([
                                    f"{detail['plan_id']}: ${detail['payment_amount']} (Payment {detail['payment_number']}/{detail['total_payments']})"
                                    for detail in month['plan_details']
                                ])
                            })
                
                pd.DataFrame(detailed_timeline).to_excel(writer, sheet_name='Detailed Timeline', index=False)
            
            print(f"\n📊 Payment projections exported: {output_path}")
            print(f"   📋 Includes {current_projections['parameters']['total_customers']} customers")
            print(f"   💰 Total projected 12-month collection: ${current_projections['portfolio_summary']['summary']['total_expected_collection']:,.2f}")
            
            if restart_projections:
                improvement = restart_projections['portfolio_summary']['summary']['total_expected_collection'] - current_projections['portfolio_summary']['summary']['total_expected_collection']
                print(f"   📈 Potential improvement with restart: ${improvement:,.2f}")
            
        except Exception as e:
            print(f"❌ Error exporting projections: {str(e)}")

    # Update the _print_enhanced_summary method to include projections info
    def _print_enhanced_summary_with_projections(self, quality_report: Dict, dashboard_data: Dict, portfolio_metrics: Dict):
        """Enhanced summary that includes projections preview"""
        
        # Call the original summary
        self._print_enhanced_summary(quality_report, dashboard_data, portfolio_metrics)
        
        # Add projections preview
        print(f"\n💫 PAYMENT PROJECTIONS PREVIEW:")
        try:
            sample_projections = self.get_payment_projections(6, 'current')  # 6 months sample
            if sample_projections:
                total_6_month = sample_projections['portfolio_summary']['summary']['total_expected_collection']
                avg_monthly = sample_projections['portfolio_summary']['summary']['average_monthly']
                customer_count = sample_projections['parameters']['total_customers']
                
                print(f"  Next 6 Months Projected: ${total_6_month:,.2f}")
                print(f"  Average Monthly Expected: ${avg_monthly:,.2f}")
                print(f"  Customers with Projections: {customer_count}")
                print(f"  📊 Full projections available via /projections page or Python API")
            else:
                print("  ⚠️  Could not generate projection preview")
        except Exception as e:
            print(f"  ⚠️  Projection preview error: {str(e)}")

    # Example usage for command line
    def show_projections_cli(system, class_filter=None):
        """Command line interface for projections"""
        print("\n" + "="*60)
        print("PAYMENT PROJECTIONS ANALYSIS")
        print("="*60)
        
        # Get 12-month projections
        projections = system.get_payment_projections(12, 'current', class_filter)
        
        if not projections:
            print("❌ Could not generate projections")
            return
        
        portfolio = projections['portfolio_summary']
        customers = projections['customer_projections']
        
        print(f"\n📊 PORTFOLIO SUMMARY:")
        print(f"  Total Customers: {len(customers)}")
        print(f"  12-Month Expected: ${portfolio['summary']['total_expected_collection']:,.2f}")
        print(f"  Average Monthly: ${portfolio['summary']['average_monthly']:,.2f}")
        
        print(f"\n🏆 TOP 5 CUSTOMERS (by monthly payment):")
        top_5 = sorted(customers, key=lambda x: x['total_monthly_payment'], reverse=True)[:5]
        for i, customer in enumerate(top_5, 1):
            print(f"  {i}. {customer['customer_name']}: ${customer['total_monthly_payment']:,.2f}/month")
            print(f"     Total owed: ${customer['total_owed']:,.2f}, Completes: Month {customer['completion_month']}")
        
        # Show next 6 months schedule
        print(f"\n📅 NEXT 6 MONTHS SCHEDULE:")
        for month in portfolio['monthly_projections'][:6]:
            month_date = month['date'][:7]  # YYYY-MM
            print(f"  {month_date}: ${month['expected_payment']:,.2f} ({month['active_customers']} customers)")
        
        # Ask if user wants detailed customer view
        response = input("\n🔍 Show detailed customer projection? Enter customer name (or press enter to skip): ")
        if response.strip():
            details = system.get_customer_projection_details(response.strip())
            if details:
                print(f"\n📋 DETAILED PROJECTION FOR {details['customer_name']}:")
                print(f"  Monthly Payment: ${details['total_monthly_payment']:,.2f}")
                print(f"  Total Owed: ${details['total_owed']:,.2f}")
                print(f"  Completion: Month {details['completion_month']}")
                print(f"  Payment Months: {details['payment_months'][:10]}")  # First 10 payment months
            else:
                print(f"❌ Could not find projections for '{response.strip()}'")
                
# Command line interface
def main():
    """Enhanced main function for command line usage"""
    if len(sys.argv) < 2:
        print("Usage: python enhanced_main.py <csv_file_path> [output_directory] [class_filter]")
        print("Example: python enhanced_main.py 'payment_plans.csv' './reports' 'BR'")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else './reports'
    class_filter = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Create and run enhanced analysis
    system = EnhancedPaymentPlanAnalysisSystem(output_dir)
    results = system.analyze_file(csv_path, class_filter)
    
    if results:
        # Optionally export to Excel
        response = input("\n📊 Export to Excel? (y/n): ")
        if response.lower() == 'y':
            system.export_for_excel()
        
        # Show collection priorities
        response = input("\n📋 Show collection priorities? (y/n): ")
        if response.lower() == 'y':
            priorities = system.get_collection_priorities(class_filter)
            if priorities:
                print(f"\n🎯 TOP COLLECTION PRIORITIES:")
                for i, priority in enumerate(priorities[:10], 1):
                    print(f"  {i}. {priority['customer_name']} ({priority['plan_id']})")
                    print(f"     {priority['months_behind']:.1f} months behind, ${priority['total_owed']:,.2f}")

if __name__ == "__main__":
    main()