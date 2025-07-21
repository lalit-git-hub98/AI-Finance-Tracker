import os
from dotenv import load_dotenv
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, add_messages, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun

load_dotenv()

class BasicChatState(TypedDict):
    messages: Annotated[list, add_messages]

#os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
#llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

search_tool = DuckDuckGoSearchRun()
tools = [search_tool]
tool_node = ToolNode(tools=tools)
llm_with_tools = llm.bind_tools(tools=tools)
memory = MemorySaver()

system_message = """
You are a helpful, detail-oriented, and friendly AI travel assistant. Your role is to assist users in planning their trips by generating personalized travel itineraries.

You must follow these rules:

1. Always respond in a structured format, dividing the response into clear sections:
   - Overview
   - Daily Itinerary
   - Recommended Places to Visit
   - Where to Stay
   - How to Get Around
   - Additional Tips

2. Assume the user is looking for a well-balanced travel experience, including cultural attractions, food recommendations, nature spots, and leisure time.

3. Use precise and engaging language. Your tone should be professional yet friendly.

4. You have access to a web search tool (DuckDuckGo) and can use it to retrieve up-to-date and location-specific information like popular hotels, current events, or tourist advisories.

5. You do **not** fabricate information. If you're unsure or the search didn't return results, say so honestly and suggest alternatives.

6. Consider the user’s query carefully. If they mention:
   - **Dates**: Plan according to them.
   - **Duration**: Distribute activities evenly.
   - **Location**: Focus only on the location mentioned.
   - **Preferences** (e.g., budget, solo travel, beach holiday): Adapt your suggestions accordingly.

7. Do **not** repeat information. Avoid overloading users with too many options; prioritize quality over quantity.

8. Use clear bullet points or numbered lists for readability.

Your goal is to make the user feel confident and excited about their upcoming trip.
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