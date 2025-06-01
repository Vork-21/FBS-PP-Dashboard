"""FastAPI Web Application for Payment Plan Analysis - FIXED VERSION"""

from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Query, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import json
import tempfile
import shutil
from datetime import datetime
from typing import Optional, List, Dict
import asyncio
from pathlib import Path
from payment_projections import PaymentProjectionCalculator


# Import our enhanced analysis system
from enhanced_main import EnhancedPaymentPlanAnalysisSystem

# Initialize FastAPI app
app = FastAPI(
    title="Payment Plan Analysis System",
    description="Enhanced payment plan analysis with comprehensive error tracking and multi-plan support",
    version="2.5.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup directories
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads"
REPORTS_DIR = BASE_DIR / "reports"

# Create directories if they don't exist
for directory in [TEMPLATES_DIR, STATIC_DIR, UPLOADS_DIR, REPORTS_DIR]:
    directory.mkdir(exist_ok=True)

# Setup templates and static files
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Global analysis system instance
analysis_system = None
current_results = None

def has_analysis_results() -> bool:
    """Check if we have analysis results"""
    return current_results is not None

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Payment Plan Analysis Dashboard",
        "has_results": has_analysis_results()
    })

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Handle file upload and analysis"""
    global analysis_system, current_results
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Save uploaded file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"upload_{timestamp}_{file.filename}"
    file_path = UPLOADS_DIR / filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Initialize analysis system
        analysis_system = EnhancedPaymentPlanAnalysisSystem(str(REPORTS_DIR))
        
        # Run analysis
        results = analysis_system.analyze_file(str(file_path))
        
        if results:
            current_results = results
            return JSONResponse({
                "success": True,
                "message": "File uploaded and analyzed successfully",
                "filename": filename,
                "summary": {
                    "total_customers": results['quality_report']['summary']['total_customers'],
                    "clean_customers": results['quality_report']['summary']['clean_customers'],
                    "problematic_customers": results['quality_report']['summary']['problematic_customers'],
                    "total_outstanding": results['quality_report']['summary']['total_outstanding'],
                    "data_quality_score": results['quality_report']['summary']['data_quality_score']
                }
            })
        else:
            raise HTTPException(status_code=500, detail="Analysis failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    finally:
        # Clean up uploaded file
        if file_path.exists():
            file_path.unlink()

@app.get("/api/results/summary")
async def get_results_summary():
    """Get analysis results summary"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    return JSONResponse(current_results['quality_report']['summary'])

@app.get("/api/results/dashboard")
async def get_dashboard_data(class_filter: Optional[str] = Query(None)):
    """Get dashboard data with optional class filtering"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    dashboard_data = current_results['dashboard_data']
    
    # Apply class filter if specified
    if class_filter:
        # Filter customer summaries
        filtered_customers = []
        for customer in dashboard_data['customer_summaries']:
            customer_plans = [plan for plan in customer['plan_details'] 
                            if plan.get('class_field') == class_filter]
            if customer_plans:
                filtered_customer = customer.copy()
                filtered_customer['plan_details'] = customer_plans
                filtered_customers.append(filtered_customer)
        
        dashboard_data = dashboard_data.copy()
        dashboard_data['customer_summaries'] = filtered_customers
        
        # Filter payment plan details
        dashboard_data['payment_plan_details'] = [
            plan for plan in dashboard_data['payment_plan_details']
            if plan.get('class_field') == class_filter
        ]
    
    return JSONResponse(dashboard_data)

@app.get("/api/results/quality")
async def get_quality_report():
    """Get detailed quality report - FIXED"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    return JSONResponse(current_results['quality_report'])

@app.get("/api/customer/{customer_name}")
async def get_customer_details(customer_name: str):
    """Get detailed information for a specific customer"""
    if not analysis_system:
        raise HTTPException(status_code=404, detail="No analysis system available")
    
    details = analysis_system.get_customer_details(customer_name)
    if not details:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_name}' not found")
    
    return JSONResponse(details)

@app.get("/api/collections/priorities")
async def get_collection_priorities(class_filter: Optional[str] = Query(None)):
    """Get prioritized collection list"""
    if not analysis_system:
        raise HTTPException(status_code=404, detail="No analysis system available")
    
    priorities = analysis_system.get_collection_priorities(class_filter)
    return JSONResponse(priorities)

@app.get("/api/classes")
async def get_available_classes():
    """Get list of available classes for filtering"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    classes = current_results['quality_report']['data_processing']['classes_found']
    return JSONResponse({"classes": classes})

@app.get("/api/customers/by-class/{class_name}")
async def get_customers_by_class(class_name: str):
    """Get customers filtered by class"""
    if not analysis_system:
        raise HTTPException(status_code=404, detail="No analysis system available")
    
    customers = analysis_system.get_customers_by_class(class_name)
    return JSONResponse(customers)

@app.get("/api/download/excel")
async def download_excel():
    """Download comprehensive Excel report"""
    if not analysis_system or not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    # Generate Excel file
    timestamp = current_results['timestamp']
    excel_filename = f"enhanced_payment_analysis_{timestamp}.xlsx"
    excel_path = REPORTS_DIR / excel_filename
    
    try:
        analysis_system.export_for_excel(str(excel_path))
        
        if excel_path.exists():
            return FileResponse(
                path=str(excel_path),
                filename=excel_filename,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate Excel file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Excel: {str(e)}")

@app.get("/api/download/error-excel")
async def download_error_excel():
    """Download error-highlighted Excel file"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    timestamp = current_results['timestamp']
    error_filename = f"payment_plan_errors_{timestamp}.xlsx"
    error_path = REPORTS_DIR / error_filename
    
    if error_path.exists():
        return FileResponse(
            path=str(error_path),
            filename=error_filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        raise HTTPException(status_code=404, detail="Error Excel file not found")

@app.get("/api/download/json/{report_type}")
async def download_json(report_type: str):
    """Download JSON reports (quality, dashboard, etc.)"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    timestamp = current_results['timestamp']
    
    if report_type == "quality":
        filename = f"enhanced_quality_report_{timestamp}.json"
        data = current_results['quality_report']
    elif report_type == "dashboard":
        filename = f"enhanced_dashboard_data_{timestamp}.json"
        data = current_results['dashboard_data']
    else:
        raise HTTPException(status_code=400, detail="Invalid report type")
    
    json_path = REPORTS_DIR / filename
    
    try:
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return FileResponse(
            path=str(json_path),
            filename=filename,
            media_type='application/json'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating JSON: {str(e)}")

@app.post("/api/clear")
async def clear_results():
    """Clear current analysis results"""
    global analysis_system, current_results
    
    analysis_system = None
    current_results = None
    
    return JSONResponse({"success": True, "message": "Results cleared"})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Dashboard page with results"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Payment Plan Analysis Dashboard",
        "has_results": has_analysis_results()
    })

@app.get("/quality", response_class=HTMLResponse)
async def quality_page(request: Request):
    """Data quality analysis page"""
    if not has_analysis_results():
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Upload File - Payment Plan Analysis",
            "has_results": False,
            "error": "No analysis results available. Please upload a file first."
        })
    
    return templates.TemplateResponse("quality.html", {
        "request": request,
        "title": "Data Quality Report",
        "has_results": True
    })

@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request, class_filter: Optional[str] = Query(None)):
    """Customer details page"""
    if not has_analysis_results():
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Upload File - Payment Plan Analysis",
            "has_results": False,
            "error": "No analysis results available. Please upload a file first."
        })
    
    return templates.TemplateResponse("customers.html", {
        "request": request,
        "title": "Customer Payment Tracking",
        "has_results": True,
        "class_filter": class_filter
    })

@app.get("/collections", response_class=HTMLResponse)
async def collections_page(request: Request):
    """Collections priority page"""
    if not has_analysis_results():
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Upload File - Payment Plan Analysis",
            "has_results": False,
            "error": "No analysis results available. Please upload a file first."
        })
    
    return templates.TemplateResponse("collections.html", {
        "request": request,
        "title": "Collection Priorities",
        "has_results": True
    })

@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    """Reports and downloads page"""
    if not has_analysis_results():
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Upload File - Payment Plan Analysis",
            "has_results": False,
            "error": "No analysis results available. Please upload a file first."
        })
    
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "title": "Reports & Downloads",
        "has_results": True
    })

@app.get("/projections", response_class=HTMLResponse)
async def projections_page(request: Request):
    """Payment projections page - FIXED"""
    if not has_analysis_results():
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Upload File - Payment Plan Analysis",
            "has_results": False,
            "error": "No analysis results available. Please upload a file first."
        })
    
    return templates.TemplateResponse("projections.html", {
        "request": request,
        "title": "Payment Projections",
        "has_results": True
    })

@app.get("/api/projections/customers")
async def get_customer_projections(
    months: int = Query(12, ge=1, le=60),
    scenario: str = Query('current', regex='^(current|restart)$'),
    class_filter: Optional[str] = Query(None)
):
    """Get payment projections for all customers"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    try:
        calculator = PaymentProjectionCalculator()
        
        # Get customer data
        customers_data = current_results['all_customers']
        
        # Apply class filter if specified
        if class_filter:
            filtered_customers = {}
            for name, customer in customers_data.items():
                if class_filter in customer.all_classes:
                    filtered_customers[name] = customer
            customers_data = filtered_customers
        
        # Calculate projections
        projections = calculator.calculate_customer_projections(
            customers_data, months, scenario
        )
        
        # Convert to JSON-serializable format
        result = []
        for proj in projections:
            result.append({
                'customer_name': proj.customer_name,
                'total_monthly_payment': proj.total_monthly_payment,
                'total_owed': proj.total_owed,
                'completion_month': proj.completion_month,
                'plan_count': proj.plan_count,
                'timeline': proj.timeline
            })
        
        return JSONResponse(result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating projections: {str(e)}")

@app.get("/api/projections/portfolio")
async def get_portfolio_projections(
    months: int = Query(12, ge=1, le=60),
    scenario: str = Query('current', regex='^(current|restart)$'),
    class_filter: Optional[str] = Query(None)
):
    """Get portfolio-wide payment projections summary"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    try:
        calculator = PaymentProjectionCalculator()
        
        # Get customer data
        customers_data = current_results['all_customers']
        
        # Apply class filter if specified
        if class_filter:
            filtered_customers = {}
            for name, customer in customers_data.items():
                if class_filter in customer.all_classes:
                    filtered_customers[name] = customer
            customers_data = filtered_customers
        
        # Calculate projections
        projections = calculator.calculate_customer_projections(
            customers_data, months, scenario
        )
        
        # Generate portfolio summary
        portfolio_summary = calculator.generate_portfolio_summary(projections, months)
        
        return JSONResponse(portfolio_summary)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating portfolio projections: {str(e)}")

@app.get("/api/projections/customer/{customer_name}")
async def get_single_customer_projection(
    customer_name: str,
    months: int = Query(12, ge=1, le=60),
    scenario: str = Query('current', regex='^(current|restart)$')
):
    """Get detailed projection for a specific customer"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    try:
        calculator = PaymentProjectionCalculator()
        
        # Get customer data
        customers_data = current_results['all_customers']
        
        if customer_name not in customers_data:
            raise HTTPException(status_code=404, detail=f"Customer '{customer_name}' not found")
        
        # Calculate projections for this customer only
        single_customer_data = {customer_name: customers_data[customer_name]}
        projections = calculator.calculate_customer_projections(
            single_customer_data, months, scenario
        )
        
        if not projections:
            raise HTTPException(status_code=404, detail=f"No valid projections for customer '{customer_name}'")
        
        # Get detailed info
        customer_details = calculator.get_customer_details(customer_name, projections)
        
        if not customer_details:
            raise HTTPException(status_code=404, detail=f"Could not generate projection details for '{customer_name}'")
        
        return JSONResponse(customer_details)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating customer projection: {str(e)}")

@app.get("/api/projections/summary")
async def get_projections_summary(
    months: int = Query(12, ge=1, le=60),
    scenario: str = Query('current', regex='^(current|restart)$')
):
    """Get high-level projections summary for dashboard cards"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    try:
        calculator = PaymentProjectionCalculator()
        
        # Get customer data
        customers_data = current_results['all_customers']
        
        # Calculate projections
        projections = calculator.calculate_customer_projections(
            customers_data, months, scenario
        )
        
        # Calculate summary metrics
        total_customers = len(projections)
        total_monthly_expected = sum(p.total_monthly_payment for p in projections)
        
        # Count customers by status
        on_track_customers = 0
        behind_customers = 0
        
        for proj in projections:
            # Check if customer has any payments in first 3 months (simple "on track" check)
            early_payments = sum(month['monthly_payment'] for month in proj.timeline[:3])
            if early_payments > 0:
                on_track_customers += 1
            else:
                behind_customers += 1
        
        # Calculate average completion time
        completion_months = [p.completion_month for p in projections if p.completion_month > 0]
        avg_completion = sum(completion_months) / len(completion_months) if completion_months else 0
        
        summary = {
            'total_customers_tracked': total_customers,
            'total_expected_monthly': round(total_monthly_expected, 2),
            'on_track_customers': on_track_customers,
            'behind_customers': behind_customers,
            'average_completion_months': round(avg_completion, 1),
            'scenario': scenario,
            'projection_months': months
        }
        
        return JSONResponse(summary)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating projections summary: {str(e)}")

@app.get("/api/projections/export/{customer_name}")
async def export_customer_projection(
    customer_name: str,
    months: int = Query(12, ge=1, le=60),
    scenario: str = Query('current', regex='^(current|restart)$')
):
    """Export customer projection as CSV"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    try:
        calculator = PaymentProjectionCalculator()
        
        # Get customer data
        customers_data = current_results['all_customers']
        
        if customer_name not in customers_data:
            raise HTTPException(status_code=404, detail=f"Customer '{customer_name}' not found")
        
        # Calculate projections
        single_customer_data = {customer_name: customers_data[customer_name]}
        projections = calculator.calculate_customer_projections(
            single_customer_data, months, scenario
        )
        
        if not projections:
            raise HTTPException(status_code=404, detail=f"No valid projections for customer '{customer_name}'")
        
        # Generate CSV content
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Month', 'Date', 'Payment Amount', 'Active Plans', 'Plan Details'])
        
        # Write data
        projection = projections[0]
        for month_data in projection.timeline:
            plan_details = []
            for detail in month_data.get('plan_details', []):
                plan_detail_str = f"{detail['plan_id']}: ${detail['payment_amount']} (Payment {detail['payment_number']}/{detail['total_payments']})"
                plan_details.append(plan_detail_str)
            
            writer.writerow([
                f"Month {month_data['month']}",
                month_data['date'][:10],  # Just date part
                month_data['monthly_payment'],
                month_data['active_plans'],
                '; '.join(plan_details)
            ])
        
        # Create response
        from fastapi.responses import Response
        
        csv_content = output.getvalue()
        output.close()
        
        filename = f"{customer_name.replace(' ', '_')}_projection_{scenario}.csv"
        
        return Response(
            content=csv_content,
            media_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting customer projection: {str(e)}")

    
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("404.html", {
        "request": request,
        "title": "Page Not Found"
    }, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return templates.TemplateResponse("500.html", {
        "request": request,
        "title": "Server Error",
        "error": str(exc)
    }, status_code=500)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    print("🚀 Payment Plan Analysis System Starting...")
    print(f"📁 Reports directory: {REPORTS_DIR}")
    print(f"📁 Uploads directory: {UPLOADS_DIR}")
    print("✅ FastAPI application ready!")

if __name__ == "__main__":
    uvicorn.run(
        "fastapi_webapp:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
