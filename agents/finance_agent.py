import os
from dotenv import load_dotenv
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, add_messages, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun, YahooFinanceNewsTool
from langchain_fmp_data import FMPDataTool
from langchain.tools import tool

load_dotenv()

class BasicChatState(TypedDict):
    messages: Annotated[list, add_messages]

os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_2")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["FMP_API_KEY"] = os.getenv("FMP_API_KEY")
#llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
memory = MemorySaver()

@tool
def web_search(query: str) -> str:
    """
    Search the web for general information, market analysis, economic news, and financial insights.
    
    Use this tool when you need to:
    - Search for general financial information or market trends
    - Find economic news and analysis from various sources
    - Get broad market insights and commentary
    - Search for information about companies, sectors, or economic events
    - Find educational content about financial concepts
    
    Args:
        query: The search query describing what information you're looking for
    
    Returns:
        String containing search results with relevant information
    """
    return DuckDuckGoSearchRun().run(query)

@tool
def get_stock_data(symbol_or_query: str) -> str:
    """
    Get real-time financial market data, stock prices, company financials, and market metrics.
    
    Use this tool when you need:
    - Current stock prices and trading data
    - Company financial statements (income, balance sheet, cash flow)
    - Market capitalization and valuation metrics
    - Historical price data and performance
    - Earnings data and financial ratios
    - Dividend information
    - Market indices data
    
    Args:
        symbol_or_query: Stock symbol (e.g., 'AAPL') or specific financial data query
    
    Returns:
        String containing structured financial data and metrics
    """
    return FMPDataTool().run(symbol_or_query)

@tool
def get_finance_news(company_or_topic: str) -> str:
    """
    Get the latest financial news and market updates from Yahoo Finance.
    
    Use this tool when you need:
    - Breaking financial news and market updates
    - Company-specific news and announcements
    - Earnings reports and analyst coverage
    - Market sentiment and trending financial stories
    - Recent developments affecting specific stocks or sectors
    - Real-time market commentary and analysis
    
    Args:
        company_or_topic: Company name, stock symbol, or financial topic to get news about
    
    Returns:
        String containing recent financial news articles and updates
    """
    return YahooFinanceNewsTool().run(company_or_topic)

tools = [web_search, get_stock_data, get_finance_news]
tool_node = ToolNode(tools=tools)
llm_with_tools = llm.bind_tools(tools=tools)

system_message = """
You are a helpful and intelligent financial assistant with access to real-time financial data tools. 

IMPORTANT: You MUST use your available tools to get current information. Never say you cannot access real-time data.

YOUR AVAILABLE TOOLS:
1. get_stock_data - Gets current stock prices, financial data, and company metrics
2. get_finance_news - Gets latest financial news and market updates  
3. web_search - Searches for general financial information and analysis

MANDATORY TOOL USAGE RULES:
- For ANY stock price question: ALWAYS use get_stock_data first
- For ANY financial news question: ALWAYS use get_finance_news first
- For market analysis or general finance questions: Use web_search first
- NEVER respond without using tools when current data is requested
- ALWAYS mention that you retrieved live/current data from your tools

WORKFLOW FOR STOCK PRICE QUERIES:
1. Use get_stock_data with the stock symbol
2. If needed, use get_finance_news for recent developments
3. Present the current price and relevant context

EXAMPLE RESPONSES:
- "Let me get the current Apple stock price for you..." (then use get_stock_data)
- "I'll check the latest financial news about Tesla..." (then use get_finance_news)
- "Let me search for current market analysis..." (then use web_search)

Your job is to:
- Answer financial market questions using your real-time data tools
- Provide insights on stock performance and economic indicators
- Give general investing suggestions (but not personalized financial advice)
- Always cite your data sources clearly

Be analytical, factual, and ALWAYS use your tools for current information.
"""

def chatbot(state: BasicChatState):
    messages = state["messages"]
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=system_message)] + messages
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def tools_router(state: BasicChatState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        return "tool_node"
    else:
        return END

graph = StateGraph(BasicChatState)
graph.add_node("chatbot", chatbot)
graph.add_node("tool_node", tool_node)
graph.set_entry_point("chatbot")
graph.add_conditional_edges("chatbot", tools_router)
graph.add_edge("tool_node", "chatbot")
app = graph.compile(checkpointer=memory)