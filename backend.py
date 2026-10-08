import os
import socket
import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

# Initialize Google GenAI client
client = genai.Client()

# Initialize FastAPI App
app = FastAPI(
    title="Cloud-Native AI Tutor Microservice",
    description="Stateless backend microservice with health checks, exponential retries, model fallbacks, and shared state tracking."
)

# Initialize Redis Client (Connects over internal Docker bridge network)
REDIS_HOST = os.getenv("REDIS_HOST", "redis_cache")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

try:
    cache = redis.Redis(
        host=REDIS_HOST, 
        port=REDIS_PORT, 
        db=0, 
        decode_responses=True, 
        socket_connect_timeout=2
    )
except Exception:
    cache = None


class TutorRequest(BaseModel):
    prompt: str


# Cloud Resilience Pattern: Exponential Backoff Retry Strategy
# Retries up to 3 times, waiting 2s, 4s, and 8s before failing
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=8), reraise=True)
def call_gemini(contents: str, model_name: str):
    return client.models.generate_content(
        model=model_name,
        contents=contents,
    )


# Cloud Pattern: Active Health Check Probe Endpoint for Nginx/Load Balancer
@app.get("/health")
def health_check():
    server_node = socket.gethostname()
    redis_status = "unreachable"
    
    if cache:
        try:
            if cache.ping():
                redis_status = "connected"
        except Exception:
            redis_status = "disconnected"

    return {
        "status": "healthy",
        "node": server_node,
        "redis_cache": redis_status
    }


# Main API Endpoint for Load-Balanced AI Processing
@app.post("/chat")
def chat_with_tutor(request: TutorRequest):
    server_node = socket.gethostname()
    
    # Track total request count for this node in the distributed Redis cache
    node_total_served = 0
    if cache:
        try:
            node_total_served = cache.incr(f"node_requests:{server_node}")
        except Exception:
            node_total_served = 0

    system_instruction = (
        "You are an expert, friendly Spanish language immersion tutor. "
        "Explain grammar rules in English and keep immersion phrases in Spanish."
    )
    
    contents = f"{system_instruction}\n\nUser: {request.prompt}"
    
    try:
        # Attempt 1: Call Primary High-Performance Model
        response = call_gemini(contents, "gemini-3.5-flash")
        used_model = "gemini-3.5-flash"
    except Exception:
        # Cloud Resilience Pattern: Graceful Degradation / Model Fallback Strategy
        try:
            response = call_gemini(contents, "gemini-3.1-flash-lite")
            used_model = "gemini-3.1-flash-lite (Fallback)"
        except Exception:
            raise HTTPException(
                status_code=503, 
                detail="All upstream cloud AI models are currently experiencing high capacity spikes. Please retry in a few seconds."
            )
        
    # Construct diagnostic string for presentation verification
    diagnostics_info = f"{server_node} | Model: {used_model}"
    if node_total_served > 0:
        diagnostics_info += f" | Node Total Served: {node_total_served}"

    return {
        "response": response.text,
        "processed_by_cloud_node": diagnostics_info
    }