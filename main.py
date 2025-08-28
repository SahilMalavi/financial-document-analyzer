from fastapi import FastAPI, File, UploadFile, Form, HTTPException
import os
import uuid
import traceback

# Import Celery components
try:
    from celery_worker import run_crew_task
    from celery.result import AsyncResult
    from celery_app import app as celery_app
    _has_celery = True
    print("Celery available for async processing")
except ImportError as e:
    _has_celery = False
    print(f"Celery not available: {e}")

try:
    from db import init_db, save_new, update_result, get_by_job
    _has_db = True
    print("Database available")
except Exception as e:
    _has_db = False
    print(f"Database not available: {e}")

# Check for required environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY not set - AI analysis will fail")
        _has_ai = False
    else:
        print("GEMINI_API_KEY configured")
        _has_ai = True
        
    if not SERPER_API_KEY:
        print("Warning: SERPER_API_KEY not set - search functionality limited")
    else:
        print("SERPER_API_KEY configured")
        
except Exception as e:
    print(f"Error loading environment: {e}")
    _has_ai = False

app = FastAPI(title="Financial Document Analyzer")

# Initialize DB if available
if _has_db:
    @app.on_event("startup")
    def on_startup():
        try:
            init_db()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Database initialization failed: {e}")

@app.get("/")
async def root():
    """Health check endpoint"""
    status = {
        "message": "Financial Document Analyzer API is running",
        "celery_available": _has_celery,
        "database_available": _has_db,
        "ai_available": _has_ai,
        "environment": {
            "gemini_api_key": "configured" if GEMINI_API_KEY else "missing",
            "serper_api_key": "configured" if SERPER_API_KEY else "missing"
        }
    }
    return status

@app.post("/analyze-document")
async def analyze_document(
    file: UploadFile = File(...),
    query: str = Form(default="Analyze this financial document for investment insights")
):
    """Analyze financial document synchronously with enhanced error handling"""
    
    # Pre-flight checks
    if not _has_ai:
        raise HTTPException(
            status_code=503, 
            detail="AI analysis unavailable - GEMINI_API_KEY not configured. Please set the API key in your environment variables."
        )
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format '{file.filename}'. Only PDF files are supported."
        )

    # Validate file size
    try:
        contents = await file.read()
        file_size = len(contents)
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
            
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(
                status_code=400, 
                detail=f"File too large ({file_size} bytes). Maximum supported size is 50MB."
            )
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading uploaded file: {str(e)}")

    file_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{file_id}.pdf"

    try:
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)

        # Write file to disk
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Validate query
        if not query or query.strip() == "":
            query = "Analyze this financial document for investment insights"

        # Import and validate worker_task module
        try:
            from worker_task import run_crew
        except ImportError as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Analysis module import failed: {str(e)}. Please ensure all dependencies are installed."
            )

        # Run the analysis
        try:
            response = run_crew(query=query.strip(), file_path=file_path)
            
            if not response:
                raise HTTPException(
                    status_code=500, 
                    detail="Analysis completed but returned no results. Please try again or check your document."
                )
                
        except Exception as analysis_error:
            error_msg = str(analysis_error)
            print(f"Analysis error: {error_msg}")
            print(f"Traceback: {traceback.format_exc()}")
            
            # Handle specific error types
            if ("RateLimitError" in error_msg or 
                "RESOURCE_EXHAUSTED" in error_msg or 
                'code": 429' in error_msg or
                "rate limit" in error_msg.lower()):
                raise HTTPException(
                    status_code=429, 
                    detail="AI service rate limit exceeded. Please wait a moment and try again."
                )
            elif ("authentication" in error_msg.lower() or 
                  "api key" in error_msg.lower() or
                  "unauthorized" in error_msg.lower()):
                raise HTTPException(
                    status_code=503, 
                    detail="AI service authentication failed. Please check API key configuration."
                )
            elif "No readable content" in error_msg:
                raise HTTPException(
                    status_code=400, 
                    detail="Could not extract text from the PDF. The file may be image-based, corrupted, or encrypted."
                )
            else:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Analysis failed: {error_msg}"
                )

        return {
            "status": "success",
            "query": query,
            "analysis": str(response),
            "file_processed": file.filename,
            "file_size_bytes": file_size,
            "processing_mode": "synchronous"
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        error_msg = str(e)
        print(f"Unexpected error in synchronous analysis: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Unexpected error processing document: {error_msg}")

    finally:
        # Always clean up the temporary file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Cleaned up temporary file: {file_path}")
            except Exception as cleanup_error:
                print(f"Warning: Could not clean up file {file_path}: {cleanup_error}")

@app.post("/analyze-document-async")
async def analyze_document_async(
    file: UploadFile = File(...),
    query: str = Form(default="Analyze this financial document for investment insights")
):
    """Analyze financial document asynchronously using Celery"""
    if not _has_celery:
        raise HTTPException(
            status_code=503, 
            detail="Async processing unavailable. Celery worker not configured. Please install and start Celery or use the synchronous endpoint."
        )

    if not _has_ai:
        raise HTTPException(
            status_code=503, 
            detail="AI analysis unavailable - GEMINI_API_KEY not configured. Please set the API key in your environment variables."
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format '{file.filename}'. Only PDF files are supported."
        )

    # Validate file size
    try:
        contents = await file.read()
        file_size = len(contents)
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
            
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(
                status_code=400, 
                detail=f"File too large ({file_size} bytes). Maximum supported size is 50MB."
            )
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading uploaded file: {str(e)}")

    file_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{file_id}.pdf"
    
    try:
        os.makedirs("data", exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(contents)

        if not query or query.strip() == "":
            query = "Analyze this financial document for investment insights"

        # Submit task to Celery
        try:
            task = run_crew_task.delay(query=query.strip(), file_path=file_path)
            task_id = task.id
            
            if not task_id:
                raise Exception("Failed to generate task ID")
                
        except Exception as celery_error:
            # Clean up file if Celery submission fails
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            raise HTTPException(
                status_code=503, 
                detail=f"Failed to submit task to background processor: {str(celery_error)}"
            )

        # Save to database if available
        if _has_db:
            try:
                save_new(task_id, file.filename, query.strip(), file_path)
                print(f"Saved task {task_id} to database")
            except Exception as db_error:
                print(f"Warning: Failed to save job to DB: {db_error}")

        return {
            "status": "queued",
            "task_id": task_id,
            "file_processed": file.filename,
            "file_size_bytes": file_size,
            "message": "Task submitted successfully to background processor",
            "processing_mode": "asynchronous",
            "status_endpoint": f"/task-status/{task_id}"
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        # Clean up file if there's an error
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Error submitting async task: {str(e)}")

@app.get("/task-status/{task_id}")
def task_status(task_id: str):
    """Get Celery task status with enhanced information"""
    if not _has_celery:
        raise HTTPException(status_code=503, detail="Celery not available.")
    
    if not task_id or task_id.strip() == "":
        raise HTTPException(status_code=400, detail="Task ID is required")
    
    try:
        result = AsyncResult(task_id, app=celery_app)
        
        if result.state == 'PENDING':
            response = {
                'task_id': task_id,
                'state': result.state,
                'status': 'Task is waiting in queue to be processed',
                'progress': 0,
                'message': 'Your task is queued and will begin processing soon'
            }
        elif result.state == 'PROGRESS':
            info = result.info or {}
            response = {
                'task_id': task_id,
                'state': result.state,
                'progress': info.get('progress', 0),
                'status': info.get('status', 'Processing...'),
                'message': 'Task is currently being processed'
            }
        elif result.state == 'SUCCESS':
            result_data = result.result or {}
            response = {
                'task_id': task_id,
                'state': result.state,
                'progress': 100,
                'status': 'Task completed successfully',
                'result': result_data.get('result', 'No result data available'),
                'message': result_data.get('message', 'Analysis completed'),
                'summary': result_data.get('summary', {})
            }
        elif result.state == 'FAILURE':
            info = result.info or {}
            response = {
                'task_id': task_id,
                'state': result.state,
                'progress': 0,
                'status': info.get('status', 'Task failed'),
                'error': info.get('error', str(result.info)),
                'error_type': info.get('error_type', 'Unknown'),
                'message': 'Task failed to complete'
            }
        else:  # Other states (RETRY, REVOKED, etc.)
            response = {
                'task_id': task_id,
                'state': result.state,
                'progress': 0,
                'status': f'Task is in {result.state} state',
                'message': f'Task status: {result.state}'
            }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking task status: {str(e)}")

# Legacy endpoint for compatibility
@app.get("/job-status/{job_id}")
def job_status(job_id: str):
    """Legacy endpoint - redirects to task-status"""
    return task_status(job_id)

@app.get("/analysis/{job_id}")
def analysis_record(job_id: str):
    """Get analysis record from database"""
    if not _has_db:
        raise HTTPException(status_code=503, detail="Database not available.")
    
    if not job_id or job_id.strip() == "":
        raise HTTPException(status_code=400, detail="Job ID is required")
    
    try:
        rec = get_by_job(job_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Analysis record not found")
        
        return {
            "job_id": rec.job_id,
            "filename": rec.filename,
            "query": rec.query,
            "status": rec.status,
            "analysis": rec.analysis_text,
            "created_at": str(rec.created_at),
            "updated_at": str(rec.updated_at),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving analysis record: {str(e)}")

@app.get("/celery-status")
def celery_status():
    """Check Celery worker status"""
    if not _has_celery:
        return {"status": "Celery not available", "workers": 0}
    
    try:
        # Check if any workers are active
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        active = inspect.active()
        
        return {
            "status": "Celery available",
            "workers": stats,
            "active_tasks": active,
            "worker_count": len(stats) if stats else 0,
            "message": "Celery is configured and workers are available" if stats else "Celery is configured but no workers are running"
        }
    except Exception as e:
        return {
            "status": "Celery available but workers unavailable",
            "error": str(e),
            "worker_count": 0,
            "message": "Celery is installed but cannot connect to workers. Ensure Redis is running and start the Celery worker."
        }

@app.get("/health")
def health_check():
    """Comprehensive health check endpoint"""
    health_status = {
        "api": "healthy",
        "timestamp": str(os.times()),
        "components": {
            "celery": "available" if _has_celery else "unavailable",
            "database": "available" if _has_db else "unavailable", 
            "ai_service": "available" if _has_ai else "unavailable"
        },
        "environment": {
            "data_directory": "writable" if os.path.exists("data") or os.makedirs("data", exist_ok=True) else "not_writable",
            "gemini_api": "configured" if GEMINI_API_KEY else "missing",
            "serper_api": "configured" if SERPER_API_KEY else "missing"
        }
    }
    
    # Determine overall health
    critical_components = ["ai_service"]
    healthy = all(health_status["components"][comp] == "available" for comp in critical_components)
    health_status["overall"] = "healthy" if healthy else "degraded"
    
    return health_status

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*50)
    print("Starting Financial Document Analyzer")
    print("="*50)
    print(f"Celery: {'Available' if _has_celery else 'Not Available'}")
    print(f"Database: {'Available' if _has_db else 'Not Available'}")
    print(f"AI Service: {'Available' if _has_ai else 'Not Available'}")
    print("="*50 + "\n")
    

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
