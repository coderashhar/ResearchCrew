import os
import streamlit as st
from langchain.agents import create_agent
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import web_search, scrape_url
from dotenv import load_dotenv

load_dotenv()

# Fallback: load from Streamlit secrets if env vars are not set (Streamlit Cloud)
for key in ("MISTRAL_API_KEY", "TAVILY_API_KEY"):
    if not os.environ.get(key):
        try:
            os.environ[key] = st.secrets[key]
        except (KeyError, FileNotFoundError):
            pass

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

# writer chain
writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Write clear, structured and insightful reports."),
    ("human", """Write a detailed research report on the topic below.
                Topic: {topic}

                Research Gathered:{research}

                Structure the report as:
                - Introduction
                - Key Findings (minimum 3 well-explained points)
                - Conclusion
                - Sources (list all URLs found in the research)

                Be detailed, factual and professional."""),
])
writer_chain = writer_prompt | llm | StrOutputParser()

# critic chain 
critic_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp and constructive research critic. Be honest and specific."),
    ("human", """Review the research report below and evaluate it strictly.
                Report:
                {report}

                Respond in this exact format:

                Score: X/10

                Strengths:
                - ...
                - ...

                Areas to Improve:
                - ...
                - ...

                One line verdict:
                ..."""),
])
critic_chain = critic_prompt | llm | StrOutputParser()