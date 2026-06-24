from langchain.agents import create_agent
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import web_search, scrape_url
from dotenv import load_dotenv

load_dotenv()

# model setup
llm = ChatMistralAI(model="mistral-medium-3-5", temperature=0)

# search agent 
def build_search_agent():
    return create_agent(
        model = llm,
        tools = [web_search],
    )

# reader agent 
def build_reader_agent():
    return create_agent(
        model = llm,
        tools = [scrape_url],
    )