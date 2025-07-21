import os
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

prompt = PromptTemplate(
    input_variables=["user_input"],
    template="""
You are a helpful assistant that converts natural language expense entries into valid SQL INSERT statements
for a SQLite database called `expense_tracker.db`.

The `expenses` table has the following columns:
- expense_id (INTEGER, PRIMARY KEY)
- user_id (INTEGER)
- amount (REAL)
- category (TEXT)
- date (TEXT)
- description (TEXT)
- recurring (BOOLEAN)
- location (TEXT)
- payment_method (TEXT)

Assume user_id is 1. Today's date is CURRENT_DATE.
Every time you must start your response with: "Here is the SQL statement:"

Input: {user_input}
Output: SQL INSERT statement:
"""
)

sql_chain = LLMChain(llm=llm, prompt=prompt)