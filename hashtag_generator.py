from dotenv import load_dotenv
import os
import ast
import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables from .env
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize the ChatGroq model
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.7,
    max_tokens=200,
    groq_api_key=GROQ_API_KEY,
)

# Prompt template for generating hashtags
prompt = ChatPromptTemplate.from_messages([
    ("system", 
     "You are a social media expert. Given a topic or niche, generate a list of 20 creative, trending, and relevant Instagram hashtags. "
     "Return only the hashtags as a Python list, nothing else."),
    ("human", "{input}"),
])

def generate_hashtags_with_llm(topic):
    chain = prompt | llm
    response = chain.invoke({"input": topic})
    hashtags_text = response.content.strip()
    try:
        hashtags = ast.literal_eval(hashtags_text)
    except Exception:
        print("Could not parse hashtags:", hashtags_text)
        hashtags = []
    return hashtags

if __name__ == "__main__":
    topic = input("Describe your topic or niche: ")
    hashtags = generate_hashtags_with_llm(topic)
    print("Generated Hashtags:", hashtags)

    # Remove '#' and save intermediate list
    parsed_hashtags = [tag.strip("#") for tag in hashtags]
    print("Parsed hashtags for Apify:", parsed_hashtags)
    with open("parsed_hashtags.json", "w", encoding="utf-8") as f:
        json.dump(parsed_hashtags, f)
    print("Parsed hashtags saved to parsed_hashtags.json")

    # Remove spaces and save final cleaned list
    final_parsed_hashtags = [tag.replace(" ", "") for tag in parsed_hashtags]
    print("Final cleaned hashtags:", final_parsed_hashtags)
    with open("final_parsed_hashtags.json", "w", encoding="utf-8") as f:
        json.dump(final_parsed_hashtags, f)
    print("Final cleaned hashtags saved to final_parsed_hashtags.json")
