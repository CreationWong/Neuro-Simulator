# Neuro-Simulator WebSocket API (`/ws/admin`)

This document outlines the message-based API protocol for the `/ws/admin` endpoint, used by the dashboard for real-time monitoring and interaction with the agent.

## 1. Connection & Authentication

- **URL**: `ws://<server_address>/ws/admin`
- **Authentication**: The panel password (if set in `config.yaml`) should be sent as a message immediately after connection. (This part is not yet implemented, the connection is currently open).

## 2. Message Structure

All messages are sent as JSON strings.

### Client-to-Server (Requests)

```json
{
  "action": "string",
  "payload": {},
  "request_id": "string"
}
```
- `action`: **Required.** The name of the action to perform.
- `payload`: **Optional.** A JSON object containing the data required for the action.
- `request_id`: **Required.** A unique identifier for the request. The server will include this in its response.

### Server-to-Client (Responses & Events)

```json
{
  "type": "string",
  "request_id": "string",
  "payload": {}
}
```
- `type`: **Required.** The type of the message. Can be `response` (for a direct reply to a request) or an event type (e.g., `core_memory_updated`).
- `request_id`: **Optional.** If the message is a direct response to a client request, this will contain the `request_id` of the original request.
- `payload`: **Optional.** A JSON object containing the data for the response or event.

---

## 3. Initial Server-Pushed Events

Upon a successful WebSocket connection, the server immediately pushes the following events to the newly connected client:

- **type**: `server_log`
  - **payload**: A string containing a single log entry from the server's historical log queue. This is sent for every log entry in the queue.
- **type**: `agent_log`
  - **payload**: A string containing a single log entry from the agent's historical log queue. This is sent for every log entry in the queue.
- **type**: `agent_context`
  - **payload**: An object containing the agent's current message history.
    ```json
    {
      "action": "update",
      "messages": [ ... ] // Array of message objects
    }
    ```
- **type**: `stream_status`
  - **payload**: The current status of the live stream process.
    ```json
    {
      "is_running": boolean,
      "backend_status": "running" | "stopped"
    }
    ```

---

## 4. Core Memory Actions

This section details the actions related to the agent's Core Memory.

### Get All Blocks

- **action**: `get_core_memory_blocks`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: An array of memory block objects.

### Create Block

- **action**: `create_core_memory_block`
- **payload**: 
  ```json
  {
    "title": "string",
    "description": "string",
    "content": ["string", ...]
  }
  ```
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success", "block_id": "string"}`

### Update Block

- **action**: `update_core_memory_block`
- **payload**: 
  ```json
  {
    "block_id": "string",
    "title": "string",
    "description": "string",
    "content": ["string", ...]
  }
  ```
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success"}`

### Delete Block

- **action**: `delete_core_memory_block`
- **payload**: 
  ```json
  {
    "block_id": "string"
  }
  ```
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success"}`

### Server-Pushed Update Event

- **type**: `core_memory_updated`
- **payload**: The full, updated list of all core memory blocks.

---

## 5. Temp Memory Actions

This section details the actions related to the agent's Temp Memory.

### Get All Temp Memory

- **action**: `get_temp_memory`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: An array of temp memory objects.

### Add Temp Memory Item

- **action**: `add_temp_memory`
- **payload**: 
  ```json
  {
    "role": "string",
    "content": "string"
  }
  ```
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success"}`

### Clear All Temp Memory

- **action**: `clear_temp_memory`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success"}`

### Server-Pushed Update Event

- **type**: `temp_memory_updated`
- **payload**: The full, updated list of all temp memory items.

---

## 6. Init Memory Actions

This section details the actions related to the agent's Init Memory.

### Get Init Memory

- **action**: `get_init_memory`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: The init memory object.

### Update Init Memory

- **action**: `update_init_memory`
- **payload**: 
  ```json
  {
    "memory": { ... } // The full, updated init memory object
  }
  ```
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success"}`

### Server-Pushed Update Event

- **type**: `init_memory_updated`
- **payload**: The full, updated init memory object.

---

## 7. Tool Actions

This section details the actions related to the agent's Tools.

### Get All Available Tools

- **action**: `get_all_tools`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"tools": [ ...tool_schemas ]}`

### Get Agent Tool Allocations

- **action**: `get_agent_tool_allocations`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"allocations": {"neuro_agent": [...], "memory_agent": [...]}}`

### Set Agent Tool Allocations

- **action**: `set_agent_tool_allocations`
- **payload**: 
  ```json
  {
    "allocations": {
      "neuro_agent": ["tool_name", ...],
      "memory_agent": ["tool_name", ...]
    }
  }
  ```
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success"}`

### Reload Tools

- **action**: `reload_tools`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success"}`

### Execute Tool

- **action**: `execute_tool`
- **payload**: 
  ```json
  {
    "tool_name": "string",
    "params": { ... }
  }
  ```
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"result": "..."}`

### Server-Pushed Update Events

- **type**: `agent_tool_allocations_updated`
- **type**: `available_tools_updated`

---

## 8. General Agent Actions

### Get Agent Context

- **action**: `get_agent_context`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: The full list of agent context messages.
- **Note**: A similar event `{"type": "agent_context", "action": "update", ...}` is pushed by the server on initial connection and after every agent response cycle.

### Get Last Prompt

- **action**: `get_last_prompt`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"prompt": "string"}`
  - `payload` (error case): `{"status": "error", "message": "string"}`
- **Note**: This is primarily for the `builtin` agent. Other agents (like `letta`) may not support prompt introspection and will return a specific message.

### Reset Agent Memory

- **action**: `reset_agent_memory`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success"}`
- **Server-Pushed Events**: This action triggers `core_memory_updated`, `temp_memory_updated`, `init_memory_updated`, and `agent_context` events.

---

## 9. Stream Control Actions

This section details actions for controlling the live stream simulation.

### Get Stream Status

- **action**: `get_stream_status`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"is_running": boolean, "backend_status": "running" | "stopped"}`

### Start Stream

- **action**: `start_stream`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success", "message": "Stream started"}`
- **Server-Pushed Event**: Triggers a `stream_status` update to all clients.

### Stop Stream

- **action**: `stop_stream`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success", "message": "Stream stopped"}`
- **Server-Pushed Event**: Triggers a `stream_status` update to all clients.

### Restart Stream

- **action**: `restart_stream`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success", "message": "Stream restarted"}`
- **Server-Pushed Event**: Triggers a `stream_status` update to all clients.

---

## 10. Config Management Actions

### Get Configs

- **action**: `get_configs`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: The filtered config object (sensitive keys removed).

### Update Configs

- **action**: `update_configs`
- **payload**: The config object with the fields to update.
- **Server Response (`type: "response"`)**: 
  - `payload`: The full, updated, and filtered config object.
- **Server-Pushed Event**: Triggers a `config_updated` event to all clients.

### Reload Configs

- **action**: `reload_configs`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success"}`
- **Server-Pushed Event**: Triggers a `config_updated` event to all clients.