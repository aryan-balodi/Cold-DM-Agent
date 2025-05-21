from dotenv import load_dotenv
import os
import ast
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables from .env
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# Initialize the ChatGroq model
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.7,
    max_tokens=100,
    groq_api_key=GROQ_API_KEY,
    
)

#Prompt template for generating hashtags
prompt = ChatPromptTemplate.from_messages([
    ("system", 
     "You are a social media expert. Given a topic or niche, generate a list of 10 creative, trending, and relevant Instagram hashtags. "
     "Return only the hashtags as a Python list, nothing else."),
    ("human", "{input}"),
])

def generate_hashtags_with_llm(topic):
    chain = prompt | llm
    response = chain.invoke({"input":topic})
    hashtags_text = response.content.strip()
    try:
        hashtags = ast.literal_eval(hashtags_text)
    except Exception:
        print("Could not parse hashtags:", hashtags_text)
        hashtags = []
    return hashtags

if __name__ == "__main__":
    topic = input("Describe your or niche: ")
    hashtags = generate_hashtags_with_llm(topic)
    print("Generated Hashtags:", hashtags)