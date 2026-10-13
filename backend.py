import os
import time
import socket
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
from google import genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
app = FastAPI()

try:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "redis_cache"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True
    )
    genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
except Exception as e:
    print(f"Startup Connection Error: {e}")

class ChatRequest(BaseModel):
    prompt: str
    model: str = "gemini-3.8-flash"

@app.get("/")
def root():
    return {"status": "Online", "service": "Spanish AI Tutor Backend"}

@app.get("/health")
def health_check():
    return {
        "status": "Healthy",
        "compute_node_id": socket.gethostname(),
        "timestamp": time.time()
    }
# Initialize the LangChain orchestrator
llm = ChatGoogleGenerativeAI(
    model="gemini-3.8-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7,
    max_tries=3,
    request_timeout=30
)

# Define the template
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

# Link them together into a chain
chain = prompt_template | llm

@app.post("/chat")
def process_chat(request: ChatRequest):
    start_time = time.time()
    
    # 1. Check Redis Cache
    try:
        cached_response = redis_client.get(request.prompt)
        if cached_response:
            latency = time.time() - start_time
            return {"response": cached_response, "cache_status": "hit", "latency": latency}
    except Exception:
        pass 
    
    # 2. Generate Content (Fail-Fast, No Retries)
    try:
        response = genai_client.models.generate_content(
            model=request.model,
            contents=request.prompt,
        )
        ai_response = chain.invoke({"student_input": request.prompt})
        final_text = ai_response.content
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            ai_response = "⚠️ (Demo Mode Notice: API quota limit reached. Mock fallback active: ¡Hola! Vamos a aprender mucho español hoy.)"
        else:
            raise HTTPException(status_code=500, detail=f"Gemini Connection Error: {error_str}")
    
    # 3. Store in Cache
    try:
        redis_client.set(request.prompt, final_text, ex=3600)
    except Exception:
        pass
    
    latency = time.time() - start_time
    return {"response": final_text, "cache_status": "miss", "latency": latency}