"""
Primary Agent: Orchestrator that routes requests to specialized sub-agents.
Auto API key rotation on 429 quota errors.
"""
import json
import os
import google.generativeai as genai
from sub_agents import (
    run_task_agent, run_calendar_agent, run_notes_agent,
    run_search_agent, run_image_agent, run_alarm_agent,
    log_agent_action, API_KEYS, _configure_genai, _rotate_key
)

ORCHESTRATOR_SYSTEM = """You are ARIA - a Multi-Agent AI System orchestrator.
You coordinate six specialized agents:
  1. task_agent      - todo items, task tracking
  2. calendar_agent  - scheduling, events, appointments
  3. notes_agent     - information capture and retrieval
  4. search_agent    - web search, current information
  5. image_agent     - photo/image analysis
  6. alarm_agent     - alarms, reminders, countdowns

Route to correct agent(s). For complex requests, use multiple agents.
- search/find/look up → search_agent
- remind/alarm/wake me → alarm_agent
- photo/image/camera → image_agent

Respond ONLY with valid JSON:
{
  "intent": "brief description",
  "agents": ["agent_name"],
  "sub_messages": {
    "agent_name": "specific instruction"
  }
}

If no agent needed:
{
  "intent": "general_query",
  "agents": [],
  "direct_response": "your response here"
}"""


async def _classify_intent(user_message: str) -> dict:
    for attempt in range(len(API_KEYS)):
        try:
            _configure_genai()
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=ORCHESTRATOR_SYSTEM
            )
            response = model.generate_content(user_message)
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except Exception as e:
            if "429" in str(e) and attempt < len(API_KEYS) - 1:
                _rotate_key()
            else:
                raise e


async def run_primary_agent(
    user_message: str,
    session_id: str = "default",
    image_base64: str = None,
    image_mime: str = "image/jpeg"
) -> dict:

    try:
        # Image uploaded → go directly to image agent
        if image_base64:
            response_text, actions = await run_image_agent(
                image_base64=image_base64,
                mime_type=image_mime,
                user_message=user_message or "Analyze this image and extract tasks."
            )
            await log_agent_action(session_id, "image_agent", "image_analysis", user_message or "image", response_text)
            return {
                "session_id": session_id,
                "response": response_text,
                "actions_taken": actions,
                "agent_used": "image_agent"
            }

        classification = await _classify_intent(user_message)

    except Exception as e:
        return {
            "session_id": session_id,
            "response": f"Sorry, I couldn't understand your request. Error: {str(e)}",
            "actions_taken": [],
            "agent_used": "primary_agent"
        }

    # Direct response
    if not classification.get("agents"):
        direct = classification.get("direct_response", "I can help with tasks, calendar, notes, search, images, and alarms!")
        await log_agent_action(session_id, "primary_agent", "direct_response", user_message, direct)
        return {
            "session_id": session_id,
            "response": direct,
            "actions_taken": [],
            "agent_used": "primary_agent"
        }

    agents_used = classification.get("agents", [])
    sub_messages = classification.get("sub_messages", {})
    all_actions = []
    sub_responses = {}

    agent_map = {
        "task_agent": run_task_agent,
        "calendar_agent": run_calendar_agent,
        "notes_agent": run_notes_agent,
        "search_agent": run_search_agent,
        "alarm_agent": run_alarm_agent,
    }

    for agent_name in agents_used:
        if agent_name == "image_agent":
            sub_responses[agent_name] = "Please upload an image for me to analyze."
            continue

        agent_fn = agent_map.get(agent_name)
        if not agent_fn:
            continue

        sub_msg = sub_messages.get(agent_name, user_message)
        try:
            response_text, actions = await agent_fn(sub_msg)
            sub_responses[agent_name] = response_text
            all_actions.extend(actions)
            await log_agent_action(session_id, agent_name, "delegated_task", sub_msg, response_text)
        except Exception as e:
            sub_responses[agent_name] = f"Error in {agent_name}: {str(e)}"

    final_response = list(sub_responses.values())[0] if len(sub_responses) == 1 else \
        "\n\n".join([f"**{k.replace('_', ' ').title()}**: {v}" for k, v in sub_responses.items()])

    await log_agent_action(session_id, "primary_agent", "orchestration_complete", user_message, final_response)

    return {
        "session_id": session_id,
        "response": final_response,
        "actions_taken": all_actions,
        "agent_used": ", ".join(agents_used)
    }