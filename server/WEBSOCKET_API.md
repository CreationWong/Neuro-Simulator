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

## 3. Core Memory Actions

This section details the actions related to the agent's Core Memory.

### Get All Blocks

- **action**: `get_core_memory_blocks`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: An array of memory block objects.
    ```json
    [
      {
        "id": "string",
        "title": "string",
        "description": "string",
        "content": ["string", ...]
      },
      ...
    ]
    ```

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

After any successful create, update, or delete operation, the server will broadcast a message to all connected admin clients.

- **type**: `core_memory_updated`
- **payload**: The full, updated list of all core memory blocks (same format as the response to `get_core_memory_blocks`).

---

## 4. Temp Memory Actions

This section details the actions related to the agent's Temp Memory.

### Get All Temp Memory

- **action**: `get_temp_memory`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: An array of temp memory objects.
    ```json
    [
      {
        "id": "string",
        "role": "string",
        "content": "string",
        "timestamp": "string"
      },
      ...
    ]
    ```

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

After any successful add or clear operation, the server will broadcast a message to all connected admin clients.

- **type**: `temp_memory_updated`
- **payload**: The full, updated list of all temp memory items (same format as the response to `get_temp_memory`).

---

## 5. Init Memory Actions

This section details the actions related to the agent's Init Memory.

### Get Init Memory

- **action**: `get_init_memory`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: The init memory object.
    ```json
    {
      "key1": "value1",
      "key2": ["value2", "value3"],
      ...
    }
    ```

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

After any successful update operation, the server will broadcast a message to all connected admin clients.

- **type**: `init_memory_updated`
- **payload**: The full, updated init memory object (same format as the response to `get_init_memory`).

---

## 6. Tool Actions

This section details the actions related to the agent's Tools.

### Get All Available Tools

- **action**: `get_all_tools`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: An object containing a list of all available tool schemas.
    ```json
    {
      "tools": [
        {
          "name": "string",
          "description": "string",
          "parameters": [
            {
              "name": "string",
              "type": "string",
              "description": "string",
              "required": "boolean"
            },
            ...
          ]
        },
        ...
      ]
    }
    ```

### Get Agent Tool Allocations

- **action**: `get_agent_tool_allocations`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: An object containing the agent-to-tool-name allocation dictionary.
    ```json
    {
      "allocations": {
        "neuro_agent": ["string", ...], // List of tool names
        "memory_agent": ["string", ...]
      }
    }
    ```

### Set Agent Tool Allocations

- **action**: `set_agent_tool_allocations`
- **payload**: 
  ```json
  {
    "allocations": {
      "neuro_agent": ["string", ...], // List of tool names
      "memory_agent": ["string", ...]
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
    "params": { ... } // An object with the parameters for the tool
  }
  ```
- **Server Response (`type: "response"`)**: 
  - `payload`: An object containing the result of the tool execution.
    ```json
    {
      "result": "..." // The result can be of any type
    }
    ```

### Server-Pushed Update Events

#### Allocations Updated
After a successful `set_agent_tool_allocations` action, the server will broadcast this event.

- **type**: `agent_tool_allocations_updated`
- **payload**: The full, updated allocations object (same format as the response to `get_agent_tool_allocations`).

#### Available Tools Updated
After a successful `reload_tools` action, the server will broadcast this event.

- **type**: `available_tools_updated`
- **payload**: The full, updated list of all available tool schemas (same format as the response to `get_all_tools`).

---

## 7. General Agent Actions

### Get Agent Context

- **action**: `get_agent_context`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: The full list of agent context messages.

### Get Last Prompt

- **action**: `get_last_prompt`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: An object containing the dynamically built prompt.
    ```json
    {
      "prompt": "string" // The full prompt text
    }
    ```
  - `payload` (error case): 
    ```json
    {
      "status": "error",
      "message": "string" // Error description
    }
    ```

### Reset Agent Memory

- **action**: `reset_agent_memory`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success"}`
- **Server-Pushed Events**: This action will trigger `core_memory_updated`, `temp_memory_updated`, `init_memory_updated`, and `agent_context` events to all clients.

---

## 8. Stream Control Actions

...

---

## 9. Config Management Actions

### Get Configs

- **action**: `get_configs`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: The config object.

### Update Configs

- **action**: `update_configs`
- **payload**: The config object with the fields to update.
- **Server Response (`type: "response"`)**: 
  - `payload`: The full, updated config object.

### Reload Configs

- **action**: `reload_configs`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success"}`

### Server-Pushed Update Event

- **type**: `config_updated`
- **payload**: The full, updated config object.

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

### Stop Stream

- **action**: `stop_stream`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success", "message": "Stream stopped"}`

### Restart Stream

- **action**: `restart_stream`
- **payload**: (empty)
- **Server Response (`type: "response"`)**: 
  - `payload`: `{"status": "success", "message": "Stream restarted"}`
