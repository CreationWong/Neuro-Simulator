# agent/api.py
"""Unified API endpoints for agent management"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import asyncio

from ..config import config_manager

# Dynamically import the appropriate agent based on config
agent_type = config_manager.settings.agent_type

if agent_type == "builtin":
    # We'll import the module, not the variable, to avoid import-time issues
    import neuro_simulator.builtin_agent as builtin_agent_module
else:
    from ..letta import letta_client, config_manager

router = APIRouter(prefix="/api/agent", tags=["Agent Management"])

# Security dependency
async def get_api_token(request: Request):
    """检查API token是否有效"""
    password = config_manager.settings.server.panel_password
    if not password:
        # No password set, allow access
        return True

    # 检查header中的token
    header_token = request.headers.get("X-API-Token")
    if header_token and header_token == password:
        return True
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API token",
        headers={"WWW-Authenticate": "Bearer"},
    )

class MessageItem(BaseModel):
    username: str
    text: str
    role: str = "user"

class ToolExecutionRequest(BaseModel):
    tool_name: str
    params: Dict[str, Any]

class MemoryUpdateRequest(BaseModel):
    block_id: str
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

# Agent message APIs
@router.get("/messages", dependencies=[Depends(get_api_token)])
async def get_agent_messages():
    """Get agent's detailed message processing history"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        # Return temp memory which contains the message history with processing details
        all_messages = builtin_agent_module.local_agent.memory_manager.temp_memory
        # Filter to only include messages with processing details (marked by having 'processing_details' key)
        detailed_messages = [msg for msg in all_messages if 'processing_details' in msg]
        return detailed_messages
    else:
        # For Letta agent, we need to get messages from the Letta API
        if letta_client is None:
            # Try to initialize letta client
            try:
                from ..letta import initialize_letta_client
                initialize_letta_client()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize Letta client: {str(e)}")
                
        if letta_client is None:
            raise HTTPException(status_code=500, detail="Letta client not initialized")
        
        try:
            agent_id = config_manager.settings.api_keys.neuro_agent_id
            if not agent_id:
                raise HTTPException(status_code=500, detail="Letta agent ID not configured")
            
            messages = letta_client.agents.messages.list(agent_id=agent_id)
            return messages
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting messages: {str(e)}")

@router.get("/context", dependencies=[Depends(get_api_token)])
async def get_agent_context():
    """Get agent's conversation context"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        # Return conversation context
        context_messages = await builtin_agent_module.local_agent.memory_manager.get_recent_context()
        return context_messages
    else:
        # For Letta agent, we need to get messages from the Letta API
        if letta_client is None:
            # Try to initialize letta client
            try:
                from ..letta import initialize_letta_client
                initialize_letta_client()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize Letta client: {str(e)}")
                
        if letta_client is None:
            raise HTTPException(status_code=500, detail="Letta client not initialized")
        
        try:
            agent_id = config_manager.settings.api_keys.neuro_agent_id
            if not agent_id:
                raise HTTPException(status_code=500, detail="Letta agent ID not configured")
            
            messages = letta_client.agents.messages.list(agent_id=agent_id)
            return messages
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting messages: {str(e)}")

@router.delete("/messages", dependencies=[Depends(get_api_token)])
async def clear_agent_messages():
    """Clear agent's message history"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        # For builtin agent, we need to filter out messages with processing details
        manager = builtin_agent_module.local_agent.memory_manager
        manager.temp_memory = [msg for msg in manager.temp_memory if 'processing_details' not in msg]
        await manager._save_temp_memory()
        return {"status": "success", "message": "Messages cleared successfully"}
    else:
        # For Letta agent, we need to reset messages via the Letta API
        if letta_client is None:
            # Try to initialize letta client
            try:
                from ..letta import initialize_letta_client
                initialize_letta_client()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize Letta client: {str(e)}")
                
        if letta_client is None:
            raise HTTPException(status_code=500, detail="Letta client not initialized")
        
        try:
            agent_id = config_manager.settings.api_keys.neuro_agent_id
            if not agent_id:
                raise HTTPException(status_code=500, detail="Letta agent ID not configured")
            
            # Reset messages
            letta_client.agents.messages.reset(agent_id=agent_id)
            return {"status": "success", "message": "Messages cleared successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error clearing messages: {str(e)}")

@router.delete("/messages/{message_id}", dependencies=[Depends(get_api_token)])
async def delete_agent_message(message_id: str):
    """Delete a specific message from agent's history"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        # For builtin agent, we don't have a direct way to delete a specific message
        # We'll return a not supported error
        raise HTTPException(status_code=400, detail="Deleting specific messages not supported for builtin agent")
    else:
        # For Letta agent, we need to delete a specific message via the Letta API
        if letta_client is None:
            # Try to initialize letta client
            try:
                from ..letta import initialize_letta_client
                initialize_letta_client()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize Letta client: {str(e)}")
                
        if letta_client is None:
            raise HTTPException(status_code=500, detail="Letta client not initialized")
        
        try:
            agent_id = config_manager.settings.api_keys.neuro_agent_id
            if not agent_id:
                raise HTTPException(status_code=500, detail="Letta agent ID not configured")
            
            # Delete specific message
            letta_client.agents.messages.delete(agent_id=agent_id, message_id=message_id)
            return {"status": "success", "message": f"Message {message_id} deleted successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting message: {str(e)}")

@router.post("/messages", dependencies=[Depends(get_api_token)])
async def send_message_to_agent(message: MessageItem):
    """Send a message to the agent"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        response = await builtin_agent_module.local_agent.process_messages([message.dict()])
        return {"response": response}
    else:
        # For Letta agent, we need to send the message via the Letta API
        if letta_client is None:
            # Try to initialize letta client
            try:
                from ..letta import initialize_letta_client
                initialize_letta_client()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize Letta client: {str(e)}")
                
        if letta_client is None:
            raise HTTPException(status_code=500, detail="Letta client not initialized")
        
        try:
            agent_id = config_manager.settings.api_keys.neuro_agent_id
            if not agent_id:
                raise HTTPException(status_code=500, detail="Letta agent ID not configured")
            
            from letta_client import MessageCreate
            response = letta_client.agents.messages.create(
                agent_id=agent_id,
                messages=[MessageCreate(role=message.role, content=f"{message.username}: {message.text}")]
            )
            
            # Extract the response text
            ai_response_text = ""
            if response and response.messages:
                last_message = response.messages[-1]
                if hasattr(last_message, 'content'):
                    if isinstance(last_message.content, str):
                        ai_response_text = last_message.content
                    elif isinstance(last_message.content, list) and last_message.content:
                        first_part = last_message.content[0]
                        if hasattr(first_part, 'text'):
                            ai_response_text = first_part.text
            
            return {"response": ai_response_text}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")

# Agent memory APIs
@router.get("/memory/init", dependencies=[Depends(get_api_token)])
async def get_init_memory():
    """Get initialization memory content"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        # Return init memory
        return builtin_agent_module.local_agent.memory_manager.init_memory
    else:
        # For Letta agent, init memory concept doesn't directly apply
        raise HTTPException(status_code=400, detail="Getting init memory not supported for Letta agent")

@router.put("/memory/init", dependencies=[Depends(get_api_token)])
async def update_init_memory(request: InitMemoryUpdateRequest):
    """Update initialization memory content"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        # Update init memory
        manager = builtin_agent_module.local_agent.memory_manager
        manager.init_memory.update(request.memory)
        await manager._save_init_memory()
        
        return {"status": "success", "message": "Initialization memory updated"}
    else:
        # For Letta agent, init memory concept doesn't directly apply
        raise HTTPException(status_code=400, detail="Updating init memory not supported for Letta agent")

@router.get("/memory/temp", dependencies=[Depends(get_api_token)])
async def get_temp_memory():
    """Get all temporary memory content"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        # Return all temp memory
        return builtin_agent_module.local_agent.memory_manager.temp_memory
    else:
        # For Letta agent, temp memory concept doesn't directly apply
        raise HTTPException(status_code=400, detail="Getting temp memory not supported for Letta agent")

@router.get("/memory/blocks", dependencies=[Depends(get_api_token)])
async def get_memory_blocks():
    """Get all memory blocks"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        blocks = await builtin_agent_module.local_agent.memory_manager.get_core_memory_blocks()
        return blocks
    else:
        # For Letta agent, we need to get memory blocks from the Letta API
        if letta_client is None:
            # Try to initialize letta client
            try:
                from ..letta import initialize_letta_client
                initialize_letta_client()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize Letta client: {str(e)}")
                
        if letta_client is None:
            raise HTTPException(status_code=500, detail="Letta client not initialized")
        
        try:
            agent_id = config_manager.settings.api_keys.neuro_agent_id
            if not agent_id:
                raise HTTPException(status_code=500, detail="Letta agent ID not configured")
            
            blocks = letta_client.agents.blocks.list(agent_id=agent_id)
            return blocks
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting memory blocks: {str(e)}")

@router.get("/memory/blocks/{block_id}", dependencies=[Depends(get_api_token)])
async def get_memory_block(block_id: str):
    """Get a specific memory block"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        block = await builtin_agent_module.local_agent.memory_manager.get_core_memory_block(block_id)
        if block is None:
            raise HTTPException(status_code=404, detail="Memory block not found")
        return block
    else:
        # For Letta agent
        if letta_client is None:
            # Try to initialize letta client
            try:
                from ..letta import initialize_letta_client
                initialize_letta_client()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize Letta client: {str(e)}")
                
        if letta_client is None:
            raise HTTPException(status_code=500, detail="Letta client not initialized")
        
        try:
            agent_id = config_manager.settings.api_keys.neuro_agent_id
            if not agent_id:
                raise HTTPException(status_code=500, detail="Letta agent ID not configured")
            
            block = letta_client.agents.blocks.retrieve(agent_id=agent_id, block_id=block_id)
            return block
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting memory block: {str(e)}")

@router.post("/memory/blocks", dependencies=[Depends(get_api_token)])
async def create_memory_block(request: MemoryCreateRequest):
    """Create a new memory block"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        block_id = await builtin_agent_module.local_agent.memory_manager.create_core_memory_block(
            title=request.title,
            description=request.description,
            content=request.content
        )
        return {"block_id": block_id}
    else:
        # For Letta agent
        if letta_client is None:
            # Try to initialize letta client
            try:
                from ..letta import initialize_letta_client
                initialize_letta_client()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize Letta client: {str(e)}")
                
        if letta_client is None:
            raise HTTPException(status_code=500, detail="Letta client not initialized")
        
        try:
            agent_id = config_manager.settings.api_keys.neuro_agent_id
            if not agent_id:
                raise HTTPException(status_code=500, detail="Letta agent ID not configured")
            
            block = letta_client.agents.blocks.create(
                agent_id=agent_id,
                name=request.title,  # Using title as name for Letta
                content="\n".join(request.content),  # Join content as a single string
                limit=1000  # Default limit
            )
            
            return {"block_id": block.id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creating memory block: {str(e)}")

@router.put("/memory/blocks/{block_id}", dependencies=[Depends(get_api_token)])
async def update_memory_block(block_id: str, request: MemoryUpdateRequest):
    """Update a memory block"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        try:
            await builtin_agent_module.local_agent.memory_manager.update_core_memory_block(
                block_id=block_id,
                title=request.title,
                description=request.description,
                content=request.content
            )
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error updating memory block: {str(e)}")
    else:
        # For Letta agent
        if letta_client is None:
            # Try to initialize letta client
            try:
                from ..letta import initialize_letta_client
                initialize_letta_client()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize Letta client: {str(e)}")
                
        if letta_client is None:
            raise HTTPException(status_code=500, detail="Letta client not initialized")
        
        try:
            agent_id = config_manager.settings.api_keys.neuro_agent_id
            if not agent_id:
                raise HTTPException(status_code=500, detail="Letta agent ID not configured")
            
            # Prepare update parameters
            update_params = {}
            if request.title:
                update_params["name"] = request.title
            if request.content:
                update_params["content"] = "\n".join(request.content)
            if request.description:
                update_params["description"] = request.description
                
            letta_client.agents.blocks.modify(
                agent_id=agent_id,
                block_id=block_id,
                **update_params
            )
            
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error updating memory block: {str(e)}")

@router.delete("/memory/blocks/{block_id}", dependencies=[Depends(get_api_token)])
async def delete_memory_block(block_id: str):
    """Delete a memory block"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        try:
            await builtin_agent_module.local_agent.memory_manager.delete_core_memory_block(block_id)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting memory block: {str(e)}")
    else:
        # For Letta agent
        if letta_client is None:
            # Try to initialize letta client
            try:
                from ..letta import initialize_letta_client
                initialize_letta_client()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize Letta client: {str(e)}")
                
        if letta_client is None:
            raise HTTPException(status_code=500, detail="Letta client not initialized")
        
        try:
            agent_id = config_manager.settings.api_keys.neuro_agent_id
            if not agent_id:
                raise HTTPException(status_code=500, detail="Letta agent ID not configured")
            
            letta_client.agents.blocks.delete(agent_id=agent_id, block_id=block_id)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting memory block: {str(e)}")

@router.post("/memory/temp", dependencies=[Depends(get_api_token)])
async def add_temp_memory_item(request: TempMemoryItem):
    """Add an item to temporary memory"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        # Add item to temp memory
        await builtin_agent_module.local_agent.memory_manager.add_temp_memory(request.content, request.role)
        
        return {"status": "success", "message": "Item added to temporary memory"}
    else:
        # For Letta agent, we don't have a direct way to add temp memory items
        raise HTTPException(status_code=400, detail="Adding items to temporary memory not supported for Letta agent")

@router.delete("/memory/temp", dependencies=[Depends(get_api_token)])
async def clear_temp_memory():
    """Clear temporary memory"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        # Reset only temp memory
        await builtin_agent_module.local_agent.memory_manager.reset_temp_memory()
        return {"status": "success", "message": "Temporary memory cleared"}
    else:
        # For Letta agent, we don't have a direct way to clear temp memory
        raise HTTPException(status_code=400, detail="Clearing temporary memory not supported for Letta agent")

@router.post("/reset_memory", dependencies=[Depends(get_api_token)])
async def reset_agent_memory():
    """Reset all agent memory types"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        try:
            await builtin_agent_module.reset_builtin_agent_memory()
            return {"status": "success", "message": "All agent memory reset successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error resetting agent memory: {str(e)}")
    else:
        # For Letta agent, we need to handle memory reset differently
        if letta_client is None:
            # Try to initialize letta client
            try:
                from ..letta import initialize_letta_client
                initialize_letta_client()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize Letta client: {str(e)}")
                
        if letta_client is None:
            raise HTTPException(status_code=500, detail="Letta client not initialized")
        
        try:
            agent_id = config_manager.settings.api_keys.neuro_agent_id
            if not agent_id:
                raise HTTPException(status_code=500, detail="Letta agent ID not configured")
            
            # For Letta, we might need to recreate the agent or reset its state
            # This is a simplified implementation - you might need to adjust based on Letta's API
            return {"status": "success", "message": "Letta agent memory reset functionality to be implemented"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error resetting Letta agent memory: {str(e)}")

# Agent tool APIs
@router.get("/tools", dependencies=[Depends(get_api_token)])
async def get_available_tools():
    """Get list of available tools"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        # Get tool descriptions from the tool manager
        tool_descriptions = builtin_agent_module.local_agent.tool_manager.get_tool_descriptions()
        return {"tools": tool_descriptions}
    else:
        # For Letta agent, tools are managed differently
        # Returning a generic response for now
        return {"tools": "Letta agent tools are managed through the Letta platform"}

@router.post("/tools/execute", dependencies=[Depends(get_api_token)])
async def execute_tool(request: ToolExecutionRequest):
    """Execute a tool with given parameters"""
    if agent_type == "builtin":
        # Check if local_agent is initialized
        if builtin_agent_module.local_agent is None:
            # Try to initialize it
            try:
                await builtin_agent_module.initialize_builtin_agent()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize builtin agent: {str(e)}")
        
        if builtin_agent_module.local_agent is None:
            raise HTTPException(status_code=500, detail="Builtin agent not initialized")
        
        try:
            result = await builtin_agent_module.local_agent.execute_tool(request.tool_name, request.params)
            return {"result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error executing tool: {str(e)}")
    else:
        # For Letta agent, tool execution is handled internally
        raise HTTPException(status_code=400, detail="Tool execution not supported for Letta agent through this API")

