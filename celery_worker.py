import os
import sys
from celery import current_task
from celery_app import app

# Ensure current directory is in Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

@app.task(bind=True)
def run_crew_task(self, query: str, file_path: str):
    """
    Celery task to run the financial analysis crew with enhanced progress tracking
    """
    try:
        # Update task state to PROGRESS
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': 'Initializing analysis...'})
        
        print(f"Starting Celery task: {self.request.id}")
        print(f"Query: {query}")
        print(f"File: {file_path}")
        
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if not file_path or not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
        
        # Update progress - validation complete
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Validation complete, loading analysis tools...'})
        
        # Import and setup the crew
        try:
            from worker_task import run_crew
        except ImportError as e:
            raise ImportError(f"Failed to import crew modules: {str(e)}")
        
        # Update progress - modules loaded
        self.update_state(state='PROGRESS', meta={'progress': 20, 'status': 'Analysis modules loaded, starting document verification...'})
        
        # Check if document is readable
        try:
            from tools import FinancialDocumentTool
            test_read = FinancialDocumentTool.read_data_tool(file_path)
            if test_read.startswith("Error:"):
                raise ValueError(f"Document reading error: {test_read}")
        except Exception as doc_error:
            raise ValueError(f"Document validation failed: {str(doc_error)}")
        
        # Update progress - document verified
        self.update_state(state='PROGRESS', meta={'progress': 30, 'status': 'Document verified, initializing AI agents...'})
        
        # Update progress - starting analysis
        self.update_state(state='PROGRESS', meta={'progress': 40, 'status': 'AI agents initialized, beginning financial analysis...'})
        
        # Run the actual analysis with progress updates
        try:
            # Update progress during analysis
            self.update_state(state='PROGRESS', meta={'progress': 50, 'status': 'Running document verification phase...'})
            
            # Run the crew analysis
            result = run_crew(query=query, file_path=file_path, job_id=self.request.id)
            
            if not result:
                raise ValueError("Analysis completed but returned no results")
                
        except Exception as analysis_error:
            raise RuntimeError(f"Analysis failed: {str(analysis_error)}")
        
        # Update progress - analysis complete
        self.update_state(state='PROGRESS', meta={'progress': 80, 'status': 'Analysis complete, generating final report...'})
        
        # Convert result to string and validate
        result_str = str(result)
        if not result_str or result_str.strip() == "":
            raise ValueError("Analysis completed but generated empty results")
        
        # Update progress - finalizing
        self.update_state(state='PROGRESS', meta={'progress': 90, 'status': 'Finalizing results and cleaning up...'})
        
        print(f"Celery task {self.request.id} completed successfully")
        
        # Clean up the file after processing
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Cleaned up file: {file_path}")
            except Exception as e:
                print(f"Warning: Could not clean up file {file_path}: {e}")
        
        # Final success state
        return {
            'status': 'SUCCESS',
            'result': result_str,
            'progress': 100,
            'message': 'Financial analysis completed successfully',
            'summary': {
                'query': query,
                'file_processed': os.path.basename(file_path),
                'analysis_length': len(result_str),
                'task_id': self.request.id
            }
        }
        
    except ValueError as ve:
        error_msg = f"Validation error: {str(ve)}"
        print(f"Celery task {self.request.id} validation failed: {error_msg}")
        
        # Clean up file on validation error
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Cleaned up file after validation error: {file_path}")
            except Exception:
                pass
        
        self.update_state(
            state='FAILURE',
            meta={
                'progress': 0,
                'status': 'Task failed due to validation error',
                'error': error_msg,
                'error_type': 'ValidationError'
            }
        )
        raise ve
        
    except ImportError as ie:
        error_msg = f"Import error: {str(ie)}"
        print(f"Celery task {self.request.id} import failed: {error_msg}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'progress': 0,
                'status': 'Task failed due to missing dependencies',
                'error': error_msg,
                'error_type': 'ImportError'
            }
        )
        raise ie
        
    except RuntimeError as re:
        error_msg = f"Runtime error: {str(re)}"
        print(f"Celery task {self.request.id} runtime failed: {error_msg}")
        
        # Clean up file on runtime error
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Cleaned up file after runtime error: {file_path}")
            except Exception:
                pass
        
        self.update_state(
            state='FAILURE',
            meta={
                'progress': 0,
                'status': 'Task failed during analysis execution',
                'error': error_msg,
                'error_type': 'RuntimeError'
            }
        )
        raise re
        
    except Exception as exc:
        error_msg = f"Unexpected error: {str(exc)}"
        print(f"Celery task {self.request.id} failed unexpectedly: {error_msg}")
        
        # Clean up the file even if processing fails
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Cleaned up file after unexpected error: {file_path}")
            except Exception:
                pass
        
        # Update task state to FAILURE
        self.update_state(
            state='FAILURE',
            meta={
                'progress': 0,
                'status': 'Task failed due to unexpected error',
                'error': error_msg,
                'error_type': type(exc).__name__
            }
        )
        raise exc