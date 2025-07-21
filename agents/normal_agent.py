import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain.agents import create_sql_agent

load_dotenv()

engine = create_engine("sqlite:///utils/expense_tracker.db", connect_args={"check_same_thread": False})
db = SQLDatabase(engine)

#os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_2")
#llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

agent = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=False,
    handle_tool_error=True
)