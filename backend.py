import os
import time
import socket
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

app = FastAPI()

# Safe Redis initialization with local/cloud fallback
try:
    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    redis_client = None
    REDIS_AVAILABLE = False

# Initialize Groq LLM orchestrator
llm = ChatGroq(
    model="openai/gpt-oss-20b",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.7
)

# Bilingual A1 Spanish Tutor Prompt
template = """
You are an expert A1-level Spanish tutor helping an English-speaking beginner. 
Always respond in a helpful, bilingual format:
1. Provide the Spanish response or phrase first.
2. Immediately provide the English translation right below or next to it.
3. Include a brief explanation in English if grammar or vocabulary concepts need clarification.

Student: {student_input}
Tutor:
"""

prompt_template = PromptTemplate(
    input_variables=["student_input"], 
    template=template
)

chain = prompt_template | llm

class ChatRequest(BaseModel):
    prompt: str
@app.get("/")
def read_root():
    return {
        "service": "A1 Spanish Tutor API",
        "status": "Online",
        "endpoints": ["/health", "/chat"]
    }

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
        # Check Redis Cache
        if REDIS_AVAILABLE:
            try:
                cached_response = redis_client.get(cache_key)
                if cached_response:
                    latency = round(time.time() - start_time, 4)
                    return {
                        "response": cached_response.decode("utf-8"),
                        "cache_status": "Hit",
                        "latency": latency,
                        "compute_node_id": socket.gethostname()
                    }
            except Exception:
                pass
        
        # Invoke LLM Orchestrator
        ai_response = chain.invoke({"student_input": request.prompt})
        final_text = ai_response.content
        
        # Save to Redis Cache
        if REDIS_AVAILABLE:
            try:
                redis_client.setex(cache_key, 3600, final_text)
            except Exception:
                pass
        
        latency = round(time.time() - start_time, 4)
        return {
            "response": final_text,
            "cache_status": "Miss",
            "latency": latency,
            "compute_node_id": socket.gethostname()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))