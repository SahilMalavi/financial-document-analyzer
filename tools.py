## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv()

from crewai_tools import SerperDevTool
from crewai.tools import tool
from pypdf import PdfReader
import io

## Creating search tool with error handling
try:
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    if SERPER_API_KEY:
        search_tool = SerperDevTool(api_key=SERPER_API_KEY)
    else:
        print("Warning: SERPER_API_KEY not found. Search functionality will be limited.")
        # Create a dummy search tool that returns a message about missing API key
        @tool("Search Tool (Disabled)")
        def search_tool(query: str) -> str:
            """Search tool is disabled due to missing SERPER_API_KEY"""
            return "Search functionality is currently unavailable due to missing API configuration."
except Exception as e:
    print(f"Error initializing search tool: {e}")
    @tool("Search Tool (Error)")
    def search_tool(query: str) -> str:
        """Search tool encountered an error during initialization"""
        return f"Search functionality is currently unavailable due to initialization error: {str(e)}"

## Creating custom pdf reader tool with enhanced error handling
class FinancialDocumentTool:
    @staticmethod
    @tool("Read Financial Document")
    def read_data_tool(file_path: str = 'data/sample.pdf') -> str:
        """
        Tool to read data from a PDF file with comprehensive error handling
        
        Args:
            file_path (str): Path of the PDF file. Defaults to 'data/sample.pdf'.
            
        Returns:
            str: Full Financial Document content
        """
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return f"Error: File not found at path '{file_path}'. Please ensure the file exists and the path is correct."
            
            # Check if file is readable
            if not os.access(file_path, os.R_OK):
                return f"Error: No read permission for file at path '{file_path}'"
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return f"Error: File at path '{file_path}' is empty"
            
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                return f"Error: File at path '{file_path}' is too large ({file_size} bytes). Maximum supported size is 50MB."
            
            full_report = ""
            
            with open(file_path, 'rb') as file:
                try:
                    pdf_reader = PdfReader(file)
                    
                    # Check if PDF is encrypted
                    if pdf_reader.is_encrypted:
                        return f"Error: PDF file at '{file_path}' is encrypted and cannot be read"
                    
                    # Check if PDF has pages
                    if len(pdf_reader.pages) == 0:
                        return f"Error: PDF file at '{file_path}' contains no pages"
                    
                    for page_num, page in enumerate(pdf_reader.pages):
                        try:
                            content = page.extract_text()
                            
                            # Clean and format the financial document data
                            if content and content.strip():
                                # Remove extra whitespaces and format properly
                                content = content.replace('\n\n', '\n').strip()
                                full_report += f"Page {page_num + 1}:\n{content}\n\n"
                            else:
                                full_report += f"Page {page_num + 1}: [No extractable text found]\n\n"
                                
                        except Exception as page_error:
                            full_report += f"Page {page_num + 1}: [Error extracting text: {str(page_error)}]\n\n"
                            continue
                
                except Exception as pdf_error:
                    return f"Error reading PDF structure: {str(pdf_error)}. The file may be corrupted or in an unsupported format."
            
            if not full_report.strip():
                return "Error: No readable content found in the PDF file. The file may be image-based or corrupted."
            
            # Check if the content seems to be financial data
            financial_keywords = ['revenue', 'profit', 'loss', 'financial', 'balance', 'cash', 'income', 'statement']
            content_lower = full_report.lower()
            if not any(keyword in content_lower for keyword in financial_keywords):
                full_report = "Warning: This document may not contain typical financial content.\n\n" + full_report
                
            return full_report
            
        except FileNotFoundError:
            return f"Error: File not found at path '{file_path}'"
        except PermissionError:
            return f"Error: Permission denied when accessing file '{file_path}'"
        except MemoryError:
            return f"Error: Insufficient memory to process file '{file_path}'. The file may be too large."
        except Exception as e:
            return f"Unexpected error reading PDF file '{file_path}': {str(e)}"

## Creating Investment Analysis Tool
class InvestmentTool:
    @staticmethod
    @tool("Analyze Investment Opportunity")
    def analyze_investment_tool(financial_data: str) -> str:
        """
        Analyze investment opportunities from financial data
        
        Args:
            financial_data (str): Financial document content
            
        Returns:
            str: Investment analysis results
        """
        
        if not financial_data or financial_data.strip() == "":
            return "Error: No financial data provided for analysis"
        
        # Check for error messages from document reading
        if financial_data.startswith("Error:") or "error" in financial_data.lower():
            return f"Cannot perform investment analysis due to document reading issues: {financial_data[:200]}..."
        
        # Basic analysis framework
        analysis_points = []
        
        # Check for key financial terms
        key_metrics = ['revenue', 'profit', 'cash flow', 'debt', 'assets', 'equity', 'earnings']
        found_metrics = [metric for metric in key_metrics if metric.lower() in financial_data.lower()]
        
        if found_metrics:
            analysis_points.append(f"Key financial metrics identified: {', '.join(found_metrics)}")
        else:
            analysis_points.append("Warning: Limited financial metrics found in the document")
        
        # Word count and complexity analysis
        word_count = len(financial_data.split())
        analysis_points.append(f"Document contains {word_count} words of financial data")
        
        if word_count > 2000:
            analysis_points.append("Comprehensive financial document suitable for detailed analysis")
        elif word_count > 1000:
            analysis_points.append("Substantial financial document with good analysis potential")
        elif word_count > 500:
            analysis_points.append("Moderate-sized financial document with basic analysis possible")
        else:
            analysis_points.append("Limited financial data - may require additional information for thorough analysis")
        
        return "Investment Analysis Results:\n" + "\n".join(f"- {point}" for point in analysis_points)

## Creating Risk Assessment Tool
class RiskTool:
    @staticmethod
    @tool("Assess Financial Risk")
    def assess_risk_tool(financial_data: str) -> str:
        """
        Assess financial risks from document data
        
        Args:
            financial_data (str): Financial document content
            
        Returns:
            str: Risk assessment results
        """
        
        if not financial_data or financial_data.strip() == "":
            return "Error: No financial data provided for risk assessment"
        
        # Check for error messages from document reading
        if financial_data.startswith("Error:") or "error" in financial_data.lower():
            return f"Cannot perform risk assessment due to document reading issues: {financial_data[:200]}..."
        
        risk_indicators = []
        
        # Check for risk-related keywords
        high_risk_keywords = ['loss', 'decline', 'bankruptcy', 'lawsuit', 'investigation', 'default']
        medium_risk_keywords = ['risk', 'uncertainty', 'volatility', 'debt', 'litigation', 'compliance']
        
        found_high_risks = [keyword for keyword in high_risk_keywords if keyword.lower() in financial_data.lower()]
        found_medium_risks = [keyword for keyword in medium_risk_keywords if keyword.lower() in financial_data.lower()]
        
        if found_high_risks:
            risk_indicators.append(f"High-priority risk factors identified: {', '.join(found_high_risks)}")
        
        if found_medium_risks:
            risk_indicators.append(f"Medium-priority risk factors mentioned: {', '.join(found_medium_risks)}")
        
        if not found_high_risks and not found_medium_risks:
            risk_indicators.append("Limited risk indicators found in the document")
        
        # Assess data completeness for risk analysis
        word_count = len(financial_data.split())
        if word_count > 2000:
            risk_indicators.append("Sufficient data available for comprehensive risk assessment")
        elif word_count > 1000:
            risk_indicators.append("Adequate data available for moderate risk assessment")
        else:
            risk_indicators.append("Limited data - risk assessment may be preliminary")
        
        return "Risk Assessment Results:\n" + "\n".join(f"- {indicator}" for indicator in risk_indicators)