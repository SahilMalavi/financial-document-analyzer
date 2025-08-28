## Importing libraries and files
from crewai import Task

from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from tools import search_tool, FinancialDocumentTool

## Creating a task to analyze financial documents
analyze_financial_document = Task(
    description="""
    Analyze the financial document thoroughly based on the user's query: {query}
    
    Perform the following analysis:
    1. Extract key financial metrics and ratios
    2. Identify trends in revenue, profitability, and cash flow
    3. Assess the company's financial health and stability
    4. Compare performance against industry benchmarks where possible
    5. Provide insights based on the specific query requirements
    
    Use the financial document at path: {file_path}
    Ensure all analysis is based on factual data from the document.
    """,

    expected_output="""
    A comprehensive financial analysis report including:
    - Executive summary of key findings
    - Detailed financial metrics analysis
    - Trend analysis with supporting data
    - Risk factors identified
    - Strengths and weaknesses assessment
    - Specific answers to the user's query
    - Data-driven insights and observations
    """,

    agent=financial_analyst,
    tools=[FinancialDocumentTool.read_data_tool, search_tool],
    async_execution=False,
)

## Creating an investment analysis task
investment_analysis = Task(
    description="""
    Based on the financial analysis, provide investment recommendations for the query: {query}
    
    Consider the following factors:
    1. Company's financial health and performance trends
    2. Market position and competitive advantages
    3. Growth prospects and future outlook
    4. Valuation metrics and fair value assessment
    5. Risk-return profile for potential investors
    
    Provide balanced, evidence-based investment guidance.
    """,

    expected_output="""
    Professional investment analysis including:
    - Investment thesis with supporting rationale
    - Risk assessment and mitigation strategies
    - Price targets or valuation ranges (if applicable)
    - Recommended investment timeline and strategy
    - Potential catalysts and risk factors
    - Comparative analysis with peers (if relevant)
    - Clear investment recommendation with justification
    """,

    agent=investment_advisor,
    tools=[FinancialDocumentTool.read_data_tool, search_tool],
    async_execution=False,
)

## Creating a risk assessment task
risk_assessment = Task(
    description="""
    Conduct comprehensive risk analysis based on the financial document and query: {query}
    
    Evaluate the following risk categories:
    1. Financial risks (liquidity, credit, market)
    2. Operational risks
    3. Strategic and competitive risks
    4. Regulatory and compliance risks
    5. Market and economic risks
    
    Provide actionable risk management recommendations.
    """,

    expected_output="""
    Detailed risk assessment report containing:
    - Risk matrix with probability and impact analysis
    - Key risk factors prioritized by severity
    - Risk mitigation strategies and recommendations
    - Stress testing scenarios (where applicable)
    - Risk monitoring indicators and thresholds
    - Recommended risk management framework
    - Contingency planning suggestions
    """,

    agent=risk_assessor,
    tools=[FinancialDocumentTool.read_data_tool, search_tool],
    async_execution=False,
)

    
verification = Task(
    description="""
    Verify the financial document's authenticity, completeness, and compliance.
    
    Check for:
    1. Document structure and required sections
    2. Data consistency and accuracy
    3. Compliance with financial reporting standards
    4. Presence of required disclosures
    5. Any red flags or inconsistencies
    
    File path: {file_path}
    """,

    expected_output="""
    Document verification report including:
    - Verification status (passed/failed/conditional)
    - Document completeness assessment
    - Compliance checklist results
    - Any identified issues or concerns
    - Data quality assessment
    - Recommendations for further verification if needed
    """,

    agent=verifier,
    tools=[FinancialDocumentTool.read_data_tool],
    async_execution=False
)