# neuro_simulator/api/agent.py
"""Unified API endpoints for agent management, decoupled from implementation."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

# Imports for the new structure
from ..core.config import config_manager
from ..core.agent_factory import create_agent
from ..core.agent_interface import BaseAgent

router = APIRouter(prefix="/api/agent", tags=["Agent Management"])

# Security dependency (remains the same)
async def get_api_token(request: Request):
    password = config_manager.settings.server.panel_password
    if not password:
        return True
    header_token = request.headers.get("X-API-Token")
    if header_token and header_token == password:
        return True
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API token",
        headers={"WWW-Authenticate": "Bearer"},
    )

# Pydantic models (remains the same)
class MessageItem(BaseModel):
    username: str
    text: str
    role: str = "user"

class ToolExecutionRequest(BaseModel):
    tool_name: str
    params: Dict[str, Any]

class MemoryUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[List[str]] = None

class MemoryCreateRequest(BaseModel):
    title: str
    description: str
    content: List[str]

class InitMemoryUpdateRequest(BaseModel):
    memory: Dict[str, Any]

class TempMemoryItem(BaseModel):
    content: str
    role: str = "system"

# Dependency to get the agent instance, making endpoints cleaner
async def get_agent() -> BaseAgent:
    return await create_agent()

# A single dependency for both auth and agent instance
class AgentDeps:
    def __init__(self, token: bool = Depends(get_api_token), agent: BaseAgent = Depends(get_agent)):
        self.agent = agent

# --- Refactored Agent Endpoints ---

@router.get("/messages", response_model=List[Dict[str, Any]])
async def get_agent_messages(deps: AgentDeps = Depends()):
    """Get agent's detailed message processing history."""
    return await deps.agent.get_message_history()

@router.get("/context", response_model=List[Dict[str, Any]])
async def get_agent_context(deps: AgentDeps = Depends()):
    """Get agent's recent conversation context (last 20 entries)."""
    return await deps.agent.get_message_history(limit=20)

@router.delete("/messages")
async def clear_agent_messages(deps: AgentDeps = Depends()):
    """Clear agent's message history."""
    await deps.agent.reset_memory()
    return {"status": "success", "message": "Agent memory reset successfully"}

@router.post("/messages")
async def send_message_to_agent(message: MessageItem, deps: AgentDeps = Depends()):
    """Send a message to the agent."""
    response = await deps.agent.process_messages([message.dict()])
    return {"response": response}

@router.get("/memory/init", response_model=Dict[str, Any])
async def get_init_memory(deps: AgentDeps = Depends()):
    """Get initialization memory content."""
    return await deps.agent.get_init_memory()

@router.put("/memory/init")
async def update_init_memory(request: InitMemoryUpdateRequest, deps: AgentDeps = Depends()):
    """Update initialization memory content."""
    await deps.agent.update_init_memory(request.memory)
    return {"status": "success", "message": "Initialization memory updated"}

@router.get("/memory/temp", response_model=List[Dict[str, Any]])
async def get_temp_memory(deps: AgentDeps = Depends()):
    """Get all temporary memory content."""
    return await deps.agent.get_temp_memory()

@router.post("/memory/temp")
async def add_temp_memory_item(request: TempMemoryItem, deps: AgentDeps = Depends()):
    """Add an item to temporary memory."""
    await deps.agent.add_temp_memory(request.content, request.role)
    return {"status": "success", "message": "Item added to temporary memory"}

@router.delete("/memory/temp")
async def clear_temp_memory(deps: AgentDeps = Depends()):
    """Clear temporary memory."""
    await deps.agent.clear_temp_memory()
    return {"status": "success", "message": "Temporary memory cleared"}

@router.get("/memory/blocks", response_model=List[Dict[str, Any]])
async def get_memory_blocks(deps: AgentDeps = Depends()):
    """Get all memory blocks."""
    return await deps.agent.get_memory_blocks()

@router.get("/memory/blocks/{block_id}", response_model=Dict[str, Any])
async def get_memory_block(block_id: str, deps: AgentDeps = Depends()):
    """Get a specific memory block."""
    block = await deps.agent.get_memory_block(block_id)
    if block is None:
        raise HTTPException(status_code=404, detail="Memory block not found")
    return block

@router.post("/memory/blocks", response_model=Dict[str, str])
async def create_memory_block(request: MemoryCreateRequest, deps: AgentDeps = Depends()):
    """Create a new memory block."""
    return await deps.agent.create_memory_block(request.title, request.description, request.content)

@router.put("/memory/blocks/{block_id}")
async def update_memory_block(block_id: str, request: MemoryUpdateRequest, deps: AgentDeps = Depends()):
    """Update a memory block."""
    await deps.agent.update_memory_block(block_id, request.title, request.description, request.content)
    return {"status": "success"}

@router.delete("/memory/blocks/{block_id}")
async def delete_memory_block(block_id: str, deps: AgentDeps = Depends()):
    """Delete a memory block."""
    await deps.agent.delete_memory_block(block_id)
    return {"status": "success"}

@router.post("/reset_memory")
async def reset_agent_memory(deps: AgentDeps = Depends()):
    """Reset all agent memory types."""
    await deps.agent.reset_memory()
    return {"status": "success", "message": "Agent memory reset successfully"}

@router.get("/tools")
async def get_available_tools(deps: AgentDeps = Depends()):
    """Get list of available tools."""
    # Return in the format expected by the frontend
    return {"tools": await deps.agent.get_available_tools()}

@router.post("/tools/execute")
async def execute_tool(request: ToolExecutionRequest, deps: AgentDeps = Depends()):
    """Execute a tool with given parameters."""
    result = await deps.agent.execute_tool(request.tool_name, request.params)
    return {"result": result}