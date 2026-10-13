import os
import time
import socket
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

app = FastAPI()

# Initialize Redis connection from environment variable
try:
    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    redis_client = None
    REDIS_AVAILABLE = False
# Initialize Groq LLM orchestrator
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.7
)

# Define the Prompt Template for the A1 Spanish Tutor
template = """
You are an expert A1-level Spanish tutor. 
Help the student learn Spanish by providing clear, encouraging, and accurate answers.
    
Student: {student_input}
Tutor:
"""
prompt_template = PromptTemplate(
    input_variables=["student_input"], 
    template=template
)

# Create the LangChain chain
chain = prompt_template | llm

class ChatRequest(BaseModel):
    prompt: str
    model: str = "llama-3.3-70b-versatile"

@app.get("/health")
def health_check():
    return {
        "status": "Healthy",
        "compute_node_id": socket.gethostname()
    }

@app.post("/chat")
def process_chat(request: ChatRequest):
    start_time = time.time()
    cache_key = request.prompt.strip().lower()
    
    try:
        # 1. Check Redis Cache
        cached_response = redis_client.get(cache_key)
        if cached_response:
            latency = round(time.time() - start_time, 4)
            return {
                "response": cached_response.decode("utf-8"),
                "cache_status": "Hit",
                "latency": latency,
                "compute_node_id": socket.gethostname()
            }
        
        # 2. Invoke Groq Orchestrator
        ai_response = chain.invoke({"student_input": request.prompt})
        final_text = ai_response.content
        
        # 3. Save to Redis Cache (expires in 1 hour)
        redis_client.setex(cache_key, 3600, final_text)
        
        latency = round(time.time() - start_time, 4)
        return {
            "response": final_text,
            "cache_status": "Miss",
            "latency": latency,
            "compute_node_id": socket.gethostname()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))