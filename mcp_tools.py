"""
MCP (Model Context Protocol) Tool Definitions
Each tool wraps a real database operation that agents can call.
"""
import aiosqlite
from database import DB_PATH
from datetime import datetime

# ─── Task Tools ───────────────────────────────────────────────────────────────

async def tool_create_task(title: str, description: str = "", priority: str = "medium", due_date: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tasks (title, description, priority, due_date) VALUES (?, ?, ?, ?)",
            (title, description, priority, due_date or None)
        )
        await db.commit()
        task_id = cursor.lastrowid
    return {"success": True, "task_id": task_id, "message": f"Task '{title}' created with ID {task_id}"}

async def tool_list_tasks(status: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            rows = await db.execute_fetchall("SELECT * FROM tasks WHERE status=? ORDER BY priority DESC", (status,))
        else:
            rows = await db.execute_fetchall("SELECT * FROM tasks ORDER BY created_at DESC")
    tasks = [dict(r) for r in rows]
    return {"success": True, "tasks": tasks, "count": len(tasks)}

async def tool_update_task(task_id: int, status: str = "", priority: str = "") -> dict:
    fields, values = [], []
    if status:
        fields.append("status=?"); values.append(status)
    if priority:
        fields.append("priority=?"); values.append(priority)
    if not fields:
        return {"success": False, "message": "No fields to update"}
    fields.append("updated_at=datetime('now')")
    values.append(task_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id=?", values)
        await db.commit()
    return {"success": True, "message": f"Task {task_id} updated"}

async def tool_delete_task(task_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        await db.commit()
    return {"success": True, "message": f"Task {task_id} deleted"}

# ─── Calendar Tools ───────────────────────────────────────────────────────────

async def tool_create_event(title: str, start_time: str, end_time: str, description: str = "", location: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO calendar_events (title, description, start_time, end_time, location) VALUES (?, ?, ?, ?, ?)",
            (title, description, start_time, end_time, location or None)
        )
        await db.commit()
        event_id = cursor.lastrowid
    return {"success": True, "event_id": event_id, "message": f"Event '{title}' scheduled"}

async def tool_list_events(date_filter: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if date_filter:
            rows = await db.execute_fetchall(
                "SELECT * FROM calendar_events WHERE start_time LIKE ? ORDER BY start_time ASC",
                (f"{date_filter}%",)
            )
        else:
            rows = await db.execute_fetchall("SELECT * FROM calendar_events ORDER BY start_time ASC")
    events = [dict(r) for r in rows]
    return {"success": True, "events": events, "count": len(events)}

async def tool_delete_event(event_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM calendar_events WHERE id=?", (event_id,))
        await db.commit()
    return {"success": True, "message": f"Event {event_id} deleted"}

# ─── Notes Tools ──────────────────────────────────────────────────────────────

async def tool_create_note(title: str, content: str, tags: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
            (title, content, tags or None)
        )
        await db.commit()
        note_id = cursor.lastrowid
    return {"success": True, "note_id": note_id, "message": f"Note '{title}' saved"}

async def tool_list_notes(tag_filter: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if tag_filter:
            rows = await db.execute_fetchall(
                "SELECT * FROM notes WHERE tags LIKE ? ORDER BY created_at DESC",
                (f"%{tag_filter}%",)
            )
        else:
            rows = await db.execute_fetchall("SELECT * FROM notes ORDER BY created_at DESC")
    notes = [dict(r) for r in rows]
    return {"success": True, "notes": notes, "count": len(notes)}

async def tool_search_notes(query: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? ORDER BY created_at DESC",
            (f"%{query}%", f"%{query}%")
        )
    notes = [dict(r) for r in rows]
    return {"success": True, "notes": notes, "count": len(notes)}

async def tool_delete_note(note_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM notes WHERE id=?", (note_id,))
        await db.commit()
    return {"success": True, "message": f"Note {note_id} deleted"}

# ─── Reminder Tools ───────────────────────────────────────────────────────────

async def tool_create_reminder(title: str, reminder_time: str, message: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO reminders (title, reminder_time, message) VALUES (?, ?, ?)",
            (title, reminder_time, message or None)
        )
        await db.commit()
        reminder_id = cursor.lastrowid
    return {"success": True, "reminder_id": reminder_id, "message": f"Reminder '{title}' set for {reminder_time}"}

async def tool_list_reminders() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall("SELECT * FROM reminders ORDER BY reminder_time ASC")
    reminders = [dict(r) for r in rows]
    return {"success": True, "reminders": reminders, "count": len(reminders)}

async def tool_delete_reminder(reminder_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
        await db.commit()
    return {"success": True, "message": f"Reminder {reminder_id} deleted"}

# ─── Tool Registry ────────────────────────────────────────────────────────────

TOOL_REGISTRY = {
    "create_task": tool_create_task,
    "list_tasks": tool_list_tasks,
    "update_task": tool_update_task,
    "delete_task": tool_delete_task,
    "create_event": tool_create_event,
    "list_events": tool_list_events,
    "delete_event": tool_delete_event,
    "create_note": tool_create_note,
    "list_notes": tool_list_notes,
    "search_notes": tool_search_notes,
    "delete_note": tool_delete_note,
    "create_reminder": tool_create_reminder,
    "list_reminders": tool_list_reminders,
    "delete_reminder": tool_delete_reminder,
}

MCP_TOOL_DEFINITIONS = [
    {
        "name": "create_task",
        "description": "Create a new task with title, description, priority (low/medium/high), and optional due date",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title"},
                "description": {"type": "string", "description": "Task details"},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "list_tasks",
        "description": "List all tasks, optionally filtered by status",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status"}
            }
        }
    },
    {
        "name": "update_task",
        "description": "Update a task status or priority by task ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"]},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "delete_task",
        "description": "Delete a task by ID",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"]
        }
    },
    {
        "name": "create_event",
        "description": "Schedule a calendar event",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "start_time": {"type": "string"},
                "end_time": {"type": "string"},
                "description": {"type": "string"},
                "location": {"type": "string"}
            },
            "required": ["title", "start_time", "end_time"]
        }
    },
    {
        "name": "list_events",
        "description": "List calendar events",
        "input_schema": {
            "type": "object",
            "properties": {
                "date_filter": {"type": "string"}
            }
        }
    },
    {
        "name": "delete_event",
        "description": "Delete a calendar event by ID",
        "input_schema": {
            "type": "object",
            "properties": {"event_id": {"type": "integer"}},
            "required": ["event_id"]
        }
    },
    {
        "name": "create_note",
        "description": "Save a note with title, content, and optional tags",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "string"}
            },
            "required": ["title", "content"]
        }
    },
    {
        "name": "list_notes",
        "description": "List all notes",
        "input_schema": {
            "type": "object",
            "properties": {"tag_filter": {"type": "string"}}
        }
    },
    {
        "name": "search_notes",
        "description": "Search notes by keyword",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    },
    {
        "name": "delete_note",
        "description": "Delete a note by ID",
        "input_schema": {
            "type": "object",
            "properties": {"note_id": {"type": "integer"}},
            "required": ["note_id"]
        }
    },
    {
        "name": "create_reminder",
        "description": "Set a reminder with title and time",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "reminder_time": {"type": "string", "description": "Time in YYYY-MM-DD HH:MM format"},
                "message": {"type": "string"}
            },
            "required": ["title", "reminder_time"]
        }
    },
    {
        "name": "list_reminders",
        "description": "List all reminders",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "delete_reminder",
        "description": "Delete a reminder by ID",
        "input_schema": {
            "type": "object",
            "properties": {"reminder_id": {"type": "integer"}},
            "required": ["reminder_id"]
        }
    }
]