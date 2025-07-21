import os
from typing import Annotated, Literal, TypedDict, Union
from langgraph.graph import StateGraph, add_messages, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

from agents.trip_agent import app as trip_agent_app
from agents.finance_agent import app as finance_agent_app
from agents.normal_agent import agent as normal_agent_llm
from agents.data_entry_agent import sql_chain

# Define the conversation state with additional context tracking
class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    current_agent: str  # Track which agent is currently handling the conversation
    agent_context: dict  # Store agent-specific context

# Initialize LLM-based router model
#llm_router = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
llm_router = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Enhanced routing node using LLM with conversation history
SYSTEM_ROUTER_PROMPT = """
You are an intelligent routing assistant that decides which specialized agent should handle a user's input in a multi-turn conversation. Your task is to read the user input along with the conversation history and respond with the name of the most appropriate agent from a list of four.

IMPORTANT: Consider the conversation context and current agent when making routing decisions. If the user is continuing a conversation with the same agent and their new message is related to the previous topic, you should generally route to the same agent to maintain continuity.

However, if the user clearly switches topics or asks for a completely different type of assistance, route to the appropriate new agent.

Only respond with the agent's name mentioned in the brackets as defined below — do not add explanations or extra text.

There are four agents, each with a specific role:

---

1. **Trip Advisor Agent** (trip) 
- Use this agent when the user asks for help planning a trip or vacation.  
- Relevant inputs may include destinations, itineraries, flights, hotels, best times to visit, local attractions, or travel advice.

**Examples:**  
- "Plan a 3-day trip to Tokyo."  
- "What are the best places to visit in Italy?"  
- "Help me book a beach vacation in July."

---

2. **Financial Advisor Agent** (finance)
- Use this agent for financial advice, stock market news, investment trends, budgeting help, or anything related to general finance or economics available online.  
- It does **not** interact with the user's personal data or transactions.

**Examples:**  
- "What's the latest news on Tesla stock?"  
- "How do I start investing in mutual funds?"  
- "Give me a summary of current market trends."

---

3. **Database Query Agent** (query)
- Use this agent when the user wants to **retrieve information from their personal database**.  
- These inputs typically start with **how much**, **what did I**, **show me**, **list**, or **did I spend**.  
- It queries the user's historical data (e.g., spending, habits, logs).

**Examples:**  
- "How much money did I spend on food last month?"  
- "What were my top 5 expenses in June?"  
- "Show me all transactions from last week."

---

4. **Data Insertion Agent** (insertion)
- Use this agent when the user wants to **add a new entry or transaction** to their personal database.  
- Look for language like **add**, **record**, **log**, **save**, or **insert** — typically includes a value, category, and sometimes a payment method.

**Examples:**  
- "Add $45.99 for groceries today paid by debit card."  
- "Log 12 dollars spent on Uber."  
- "Record 20.50 lunch with description coffee, paid by card."

---

### RULES:
- **Only return one of the following four strings** exactly:  
  `trip`, `finance`, `query`, or `insertion`.
- **Do not explain** your choice.
- If the input is ambiguous, choose the most likely intent based on the context.
- Consider conversation continuity: if the user is asking follow-up questions or providing clarifications to the same agent, route to that agent.
"""

def llm_route_decision(state: GraphState) -> Literal["trip", "finance", "query", "insertion"]:
    # Get the full conversation history for context
    conversation_history = state['messages']
    current_agent = state.get('current_agent', 'none')
    
    # Prepare the context for the router
    context_messages = []
    
    # Add system prompt
    context_messages.append(SystemMessage(content=SYSTEM_ROUTER_PROMPT))
    
    # Add conversation history context if available
    if len(conversation_history) > 1:
        history_context = f"Previous conversation context:\nCurrent agent handling conversation: {current_agent}\n"
        history_context += "Recent messages:\n"
        
        # Include last few messages for context (limit to avoid token overflow)
        recent_messages = conversation_history[-3:]  # Last 3 messages
        for msg in recent_messages[:-1]:  # Exclude the current message
            if isinstance(msg, HumanMessage):
                history_context += f"User: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                history_context += f"Assistant: {msg.content}\n"
        
        context_messages.append(HumanMessage(content=history_context))
    
    # Add the current user input
    current_input = f"Current user input: {conversation_history[-1].content}"
    context_messages.append(HumanMessage(content=current_input))
    
    response = llm_router.invoke(context_messages)
    route = response.content.strip().lower()
    
    if route in ["trip", "finance", "query", "insertion"]:
        return route
    else:
        return "query"
    
def router_node(state: GraphState) -> GraphState:
    # Pass through the state without modification
    return state

# Enhanced agent wrappers that maintain conversation context

def trip_node(state: GraphState):
    # Pass the full conversation state to the trip agent
    result = trip_agent_app.invoke(state)
    
    # Update the current agent and return the result
    updated_state = {
        "messages": [result["messages"][-1]],
        "current_agent": "trip",
        "agent_context": state.get("agent_context", {})
    }
    
    return updated_state

def finance_node(state: GraphState):
    # Pass the full conversation state to the finance agent
    result = finance_agent_app.invoke(state)
    
    # Update the current agent and return the result
    updated_state = {
        "messages": [result["messages"][-1]],
        "current_agent": "finance", 
        "agent_context": state.get("agent_context", {})
    }
    
    return updated_state

def normal_node(state: GraphState):
    # For the normal agent, we need to handle conversation history manually
    # since it might not be designed for multi-turn conversations
    
    # Get conversation history
    conversation_history = state["messages"]
    
    # Prepare context for the normal agent
    context = "Previous conversation:\n"
    for msg in conversation_history[:-1]:  # Exclude current message
        if isinstance(msg, HumanMessage):
            context += f"User: {msg.content}\n"
        elif isinstance(msg, AIMessage):
            context += f"Assistant: {msg.content}\n"
    
    # Current user message
    current_msg = conversation_history[-1].content
    
    # Combine context with current message
    enhanced_input = f"{context}\nCurrent user input: {current_msg}"
    
    # Run the normal agent with enhanced context
    result = normal_agent_llm.run(enhanced_input)
    
    updated_state = {
        "messages": [AIMessage(content=result)],
        "current_agent": "query",
        "agent_context": state.get("agent_context", {})
    }
    
    return updated_state

def data_node(state: GraphState):
    # For data insertion, we might need conversation context to understand references
    conversation_history = state["messages"]
    
    # Prepare context for the data agent
    context = "Previous conversation context:\n"
    for msg in conversation_history[:-1]:
        if isinstance(msg, HumanMessage):
            context += f"User: {msg.content}\n"
        elif isinstance(msg, AIMessage):
            context += f"Assistant: {msg.content}\n"
    
    current_msg = conversation_history[-1].content
    enhanced_input = f"{context}\nCurrent user input: {current_msg}"
    
    # Run the SQL chain with enhanced context
    sql_query = sql_chain.run(enhanced_input)
    
    updated_state = {
        "messages": [AIMessage(content=f"Here is the SQL statement:\n{sql_query}")],
        "current_agent": "insertion",
        "agent_context": state.get("agent_context", {})
    }
    
    return updated_state

# Memory to track turns
memory = MemorySaver()

# Build the LangGraph with enhanced state handling
workflow = StateGraph(GraphState)
workflow.add_node("trip", trip_node)
workflow.add_node("finance", finance_node)
workflow.add_node("query", normal_node)
workflow.add_node("insertion", data_node)
workflow.add_node("router", router_node)
workflow.set_entry_point("router")

# Edges for routing
workflow.add_conditional_edges("router", llm_route_decision)
workflow.add_edge("trip", END)
workflow.add_edge("finance", END)
workflow.add_edge("query", END)
workflow.add_edge("insertion", END)

# Compile final app
app = workflow.compile(checkpointer=memory)

# Enhanced chatbot loop with better state initialization
# if __name__ == "__main__":
#     config = {"configurable": {"thread_id": "multi-agent-thread-1"}}

#     print("\n💬 Multi-Agent Chatbot (Multi-Turn Support) Ready! Type 'exit' to quit.\n")
    
#     while True:
#         user_input = input("User: ")
#         if user_input.lower() in ("exit", "quit"):
#             print("👋 Exiting...")
#             break

#         # Initialize state with proper structure if it's the first message
#         initial_state = {
#             "messages": [HumanMessage(content=user_input)],
#             "current_agent": "none",
#             "agent_context": {}
#         }
        
#         result = app.invoke(initial_state, config=config)
#         print("Bot:", result["messages"][-1].content)
        
#         # Optional: Display current agent for debugging
#         current_agent = result.get("current_agent", "unknown")
#         print(f"🤖 (Handled by: {current_agent} agent)\n")