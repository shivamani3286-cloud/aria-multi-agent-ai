"""
Sub-Agents: Specialized agents for each domain.
Auto API key rotation on 429 quota errors.
"""
import json
import os
import google.generativeai as genai
from mcp_tools import TOOL_REGISTRY, MCP_TOOL_DEFINITIONS
from database import DB_PATH
import aiosqlite

# ─── API Key Rotation ─────────────────────────────────────────────────────────

API_KEYS = [
    os.getenv("GOOGLE_API_KEY_1", ""),
    os.getenv("GOOGLE_API_KEY_2", ""),
    os.getenv("GOOGLE_API_KEY_3", ""),
]
API_KEYS = [k for k in API_KEYS if k]
_current_key_index = 0

def _get_current_key():
    return API_KEYS[_current_key_index]

def _rotate_key():
    global _current_key_index
    _current_key_index = (_current_key_index + 1) % len(API_KEYS)
    print(f"[ARIA] Switched to API key #{_current_key_index + 1}")
    genai.configure(api_key=_get_current_key())

def _configure_genai():
    genai.configure(api_key=_get_current_key())

_configure_genai()


# ─── Tool Converter ───────────────────────────────────────────────────────────

def _convert_tools_for_gemini(tool_definitions):
    gemini_tools = []
    for tool in tool_definitions:
        func_decl = genai.protos.FunctionDeclaration(
            name=tool["name"],
            description=tool["description"],
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    k: genai.protos.Schema(
                        type=genai.protos.Type.STRING if v.get("type") == "string"
                        else genai.protos.Type.INTEGER if v.get("type") == "integer"
                        else genai.protos.Type.STRING,
                        description=v.get("description", "")
                    )
                    for k, v in tool["input_schema"].get("properties", {}).items()
                },
                required=tool["input_schema"].get("required", [])
            )
        )
        gemini_tools.append(func_decl)
    return [genai.protos.Tool(function_declarations=gemini_tools)]


# ─── Agentic Loop with Auto Key Rotation ─────────────────────────────────────

async def _run_agentic_loop(system, user_message, tool_registry, tool_definitions, max_iterations=10):
    gemini_tools = _convert_tools_for_gemini(tool_definitions)
    actions_taken = []

    # Initial call with rotation
    chat = None
    response = None
    for attempt in range(len(API_KEYS)):
        try:
            _configure_genai()
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=system,
                tools=gemini_tools
            )
            chat = model.start_chat()
            response = chat.send_message(user_message)
            break
        except Exception as e:
            if "429" in str(e) and attempt < len(API_KEYS) - 1:
                _rotate_key()
            else:
                return f"Error: {str(e)}", []

    for _ in range(max_iterations):
        fn_calls = [p.function_call for p in response.parts if hasattr(p, 'function_call') and p.function_call.name]

        if not fn_calls:
            return (response.text if hasattr(response, 'text') else "Done."), actions_taken

        fn_responses = []
        for fn_call in fn_calls:
            tool_name = fn_call.name
            tool_input = dict(fn_call.args)
            tool_fn = tool_registry.get(tool_name)
            try:
                result = await tool_fn(**tool_input) if tool_fn else {"success": False, "error": f"Unknown tool: {tool_name}"}
            except Exception as e:
                result = {"success": False, "error": str(e)}

            actions_taken.append({"tool": tool_name, "input": tool_input, "result": result})
            fn_responses.append(genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=tool_name,
                    response={"result": json.dumps(result)}
                )
            ))

        for attempt in range(len(API_KEYS)):
            try:
                response = chat.send_message(fn_responses)
                break
            except Exception as e:
                if "429" in str(e) and attempt < len(API_KEYS) - 1:
                    _rotate_key()
                else:
                    return f"Error: {str(e)}", actions_taken

    return "Max iterations reached.", actions_taken


# ─── Task Agent ───────────────────────────────────────────────────────────────

async def run_task_agent(user_message):
    system = "You are the Task Management Agent for ARIA. Create, list, update, delete tasks. Confirm with task ID."
    tools = [t for t in MCP_TOOL_DEFINITIONS if "task" in t["name"]]
    registry = {k: v for k, v in TOOL_REGISTRY.items() if "task" in k}
    return await _run_agentic_loop(system, user_message, registry, tools)


# ─── Calendar Agent ───────────────────────────────────────────────────────────

async def run_calendar_agent(user_message):
    system = "You are the Calendar Agent for ARIA. Schedule events using ISO 8601 format (2026-04-06T10:00:00)."
    tools = [t for t in MCP_TOOL_DEFINITIONS if "event" in t["name"]]
    registry = {k: v for k, v in TOOL_REGISTRY.items() if "event" in k}
    return await _run_agentic_loop(system, user_message, registry, tools)


# ─── Notes Agent ──────────────────────────────────────────────────────────────

async def run_notes_agent(user_message):
    system = "You are the Notes Agent for ARIA. Create, list, search, delete notes. Suggest relevant tags."
    tools = [t for t in MCP_TOOL_DEFINITIONS if "note" in t["name"]]
    registry = {k: v for k, v in TOOL_REGISTRY.items() if "note" in k}
    return await _run_agentic_loop(system, user_message, registry, tools)


# ─── Search Agent ─────────────────────────────────────────────────────────────

async def run_search_agent(user_message):
    for attempt in range(len(API_KEYS)):
        try:
            _configure_genai()
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction="You are the Web Search Agent for ARIA. Search and summarize results clearly.",
                tools=[{"google_search": {}}]
            )
            response = model.start_chat().send_message(user_message)
            text = response.text if hasattr(response, 'text') else "No results found."
            return text, [{"tool": "google_search", "input": {"query": user_message}, "result": "done"}]
        except Exception as e:
            if "429" in str(e) and attempt < len(API_KEYS) - 1:
                _rotate_key()
            else:
                return f"Search error: {str(e)}", []


# ─── Image Agent ──────────────────────────────────────────────────────────────

async def run_image_agent(image_base64, mime_type="image/jpeg", user_message="Analyze this image and extract tasks."):
    for attempt in range(len(API_KEYS)):
        try:
            _configure_genai()
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction="You are the Image Agent for ARIA. Extract text, tasks, deadlines from images."
            )
            image_part = {"inline_data": {"mime_type": mime_type, "data": image_base64}}
            response = model.generate_content([image_part, user_message])
            text = response.text if hasattr(response, 'text') else "Could not analyze image."
            return text, [{"tool": "image_analysis", "input": {}, "result": "done"}]
        except Exception as e:
            if "429" in str(e) and attempt < len(API_KEYS) - 1:
                _rotate_key()
            else:
                return f"Image error: {str(e)}", []


# ─── Alarm / Reminder Agent ───────────────────────────────────────────────────

async def run_alarm_agent(user_message):
    system = "You are the Reminder Agent for ARIA. Use create_reminder. Format time as YYYY-MM-DD HH:MM. Confirm with emoji ⏰."
    tools = [t for t in MCP_TOOL_DEFINITIONS if "reminder" in t["name"]]
    registry = {k: v for k, v in TOOL_REGISTRY.items() if "reminder" in k}
    return await _run_agentic_loop(system, user_message, registry, tools)


# ─── Agent Log ────────────────────────────────────────────────────────────────

async def log_agent_action(session_id, agent_name, action, input_text, output_text):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO agent_logs (session_id, agent_name, action, input, output) VALUES (?, ?, ?, ?, ?)",
            (session_id, agent_name, action, input_text, output_text)
        )
        await db.commit()