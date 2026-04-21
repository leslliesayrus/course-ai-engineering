import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_groq import ChatGroq

from prompts import DEFAULT_SYSTEM_PROMPT
from tools import execute_sql, read_database_metadata

# Load env variables from backend/.env
dotenv_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY nao encontrado em backend/.env")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.2,
    api_key=groq_api_key,
)

agent = create_agent(llm, tools=[read_database_metadata, execute_sql])


def ask_agent(user_message: str, system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> str:
    result = agent.invoke(
        {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
        }
    )

    messages = result.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and isinstance(msg.content, str) and msg.content != "":
            return msg.content

    return ""
