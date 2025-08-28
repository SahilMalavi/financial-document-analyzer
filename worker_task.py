from crewai import Crew, Process
from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from task import analyze_financial_document, investment_analysis, risk_assessment, verification

def run_crew(query: str, file_path: str = "data/sample.pdf", job_id: str = None):
    """Run the financial analysis crew"""
    
    # Get job_id from RQ context if running in worker
    try:
        from rq import get_current_job
        current_job = get_current_job()
        if current_job:
            job_id = current_job.get_id()
    except ImportError:
        pass  # Not running in RQ context
    
    financial_crew = Crew(
        agents=[verifier, financial_analyst, investment_advisor, risk_assessor],
        tasks=[verification, analyze_financial_document, investment_analysis, risk_assessment],
        process=Process.sequential,
        verbose=True
    )
    
    result = financial_crew.kickoff(inputs={'query': query, 'file_path': file_path})

    # Persist result to DB if job_id is available and db module exists
    if job_id:
        try:
            from db import update_result
            update_result(job_id, str(result), status="finished")
        except ImportError:
            pass  # DB module not available

    return result