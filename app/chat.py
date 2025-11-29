# app/chat_analytics.py
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from typing import List, Dict, Any

from .config import settings
from .database import engine # <-- Import our project's database engine

def get_db():
    """Initializes a connection to our existing PostgreSQL database."""
    # We pass our SQLAlchemy engine directly to LangChain
    return SQLDatabase(engine)

def get_sql_chain(db: SQLDatabase):
    """Creates the chain that writes the SQL query."""
    template = """
    You are a data analyst. You are interacting with a user asking questions about the recruitment database.
    Based on the table schema below, write a SQL query that would answer the user's question. Take the conversation history into account.
    
    <SCHEMA>{schema}</SCHEMA>
    
    Conversation History: {chat_history}
    
    Write only the SQL query and nothing else. Do not wrap the SQL query in any other text, not even backticks.
    
    Your turn:
    
    Question: {question}
    SQL Query:
    """
    
    prompt = ChatPromptTemplate.from_template(template)
    
    llm = ChatOpenAI(
        model="gpt-3.5-turbo", 
        api_key=settings.OPENAI_API_KEY.get_secret_value()
    )
    
    def get_schema(_):
        return db.get_table_info()
    
    return (
        RunnablePassthrough.assign(schema=get_schema)
        | prompt
        | llm
        | StrOutputParser()
    )
        
def get_response_chain(db: SQLDatabase):
    """Creates the final chain that generates a natural language response."""
    
    sql_chain = get_sql_chain(db)
    
    template = """
    You are a data analyst. Based on the table schema, question, sql query, and sql response, write a natural language response.
    <SCHEMA>{schema}</SCHEMA>

    Conversation History: {chat_history}
    SQL Query: <SQL>{query}</SQL>
    User question: {question}
    SQL Response: {response}
    """
    
    prompt = ChatPromptTemplate.from_template(template)
    
    llm = ChatOpenAI(
        model="gpt-4o", 
        api_key=settings.OPENAI_API_KEY.get_secret_value()
    )
    
    chain = (
        RunnablePassthrough.assign(query=sql_chain).assign(
          schema=lambda _: db.get_table_info(),
          response=lambda vars: db.run(vars["query"]),
        )
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return chain

# --- Main function to run the chat ---
def run_chat_analytics(question: str, chat_history_dicts: List[Dict[str, str]]) -> str:
    """
    Takes a question and chat history, returns a natural language answer.
    """
    db = get_db()
    
    # Convert dict history to LangChain message objects
    chat_history = []
    for msg in chat_history_dicts:
        if msg.get('role') == 'human':
            chat_history.append(HumanMessage(content=msg.get('content')))
        elif msg.get('role') == 'ai':
            chat_history.append(AIMessage(content=msg.get('content')))

    response_chain = get_response_chain(db)
    
    response = response_chain.invoke({
        "question": question,
        "chat_history": chat_history,
    })
    
    return response