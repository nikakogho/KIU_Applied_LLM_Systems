import os
import json
import sqlite3
from typing import Any, Dict, List, Optional

from openai import OpenAI

# ==============================
# CONFIG
# ==============================

DB_PATH = "company.db"

# Default model: cheap but solid for tools, can override via env
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

client = OpenAI()

SYSTEM_INSTRUCTIONS = """
You are an HR database assistant for a small company.

You have access to tools that operate on a SQLite database. The database stores employees
with: id, name, role, department, and salary.

Typical departments are: Engineering, HR, Sales, Marketing, Support, Security, Legal,
so if asked for similar sounding role just look up those departments, like if asked for guards look up Security and so on.

Your job:
- Read the manager's natural language requests.
- Decide which tools to call and with what arguments.
- Do NOT write or output raw SQL. Only use the tools.
- After tools run, explain clearly in natural language what you did or found.
- If a request is ambiguous (e.g. multiple employees with same name), ask a clarification
  in your final answer instead of guessing destructively.

For updates and deletes ALWAYS first get ids of the employees in question and confirm with user and then update/delete by id.
NEVER update/delete by name directly if multiple rows may match.
When user asks about employee, include id for clarity.
Examples:
1) user: 'We just hired John Doe. He's an Engineer making 80000.'
    agent: calls add_employee with name='John Doe', role='Engineer', salary=80000
    agent: 'Added new employee John Doe (ID: 3) as an Engineer with a salary of 80000.'

2) user: 'Show me all engineers.'
    agent: calls search_employees with role='Engineer'
    agent: 'Found 5 engineers: [list of employees with their ids, names, roles, departments, salaries].'

3) user: 'Joe just got promoted to Senior Engineer in Engineering and his new salary is 95000.'
    agent: calls update_employee with name='Joe', new_role='Senior Engineer', new_salary=95000
    agent: 'Updated Joe (ID: 2) to Senior Engineer with a new salary of 95000.'

"""

# ==============================
# DB HELPERS
# ==============================

def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_database() -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT,
            department TEXT,
            salary REAL
        )
        """
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Database initialized and employees table ready."}


def add_employee(
    name: str,
    role: Optional[str] = None,
    department: Optional[str] = None,
    salary: Optional[float] = None,
) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO employees (name, role, department, salary)
        VALUES (?, ?, ?, ?)
        """,
        (name, role, department, float(salary) if salary is not None else None),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {
        "status": "success",
        "employee_id": new_id,
        "name": name,
        "role": role,
        "department": department,
        "salary": salary,
    }

def update_employee(
    employee_id: Optional[int] = None,
    name: Optional[str] = None,
    new_name: Optional[str] = None,
    new_department: Optional[str] = None,
    new_salary: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Update an employee's name, department, or salary.

    You must provide either employee_id or name to identify the employee.
    If multiple rows share the same name, all of them will be updated.
    """
    if employee_id is None and name is None:
        return {
            "status": "error",
            "message": "You must provide either employee_id or name to update.",
        }

    # Collect fields to update
    set_clauses = []
    params: List[Any] = []

    if new_name is not None and new_name.strip() != "":
        set_clauses.append("name = ?")
        params.append(new_name)
    if new_department is not None and new_department.strip() != "":
        set_clauses.append("department = ?")
        params.append(new_department)
    if new_salary is not None and new_salary != 0:
        set_clauses.append("salary = ?")
        params.append(float(new_salary))

    if not set_clauses:
        return {
            "status": "error",
            "message": "No new values provided to update.",
        }

    # Build WHERE clause
    if employee_id is not None and employee_id > 0:
        where_clause = "id = ?"
        params.append(employee_id)
    else:
        where_clause = "name = ?"
        params.append(name)

    query = f"UPDATE employees SET {', '.join(set_clauses)} WHERE {where_clause}"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    updated = cur.rowcount
    conn.commit()
    conn.close()

    if updated == 0:
        return {
            "status": "not_found",
            "updated": 0,
            "message": "No matching employee found to update.",
        }
    else:
        return {
            "status": "success",
            "updated": updated,
            "message": f"Updated {updated} employee(s).",
        }

def delete_employee(
    employee_id: Optional[int] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    if employee_id is None and name is None:
        return {
            "status": "error",
            "message": "You must provide either employee_id or name.",
        }

    conn = get_connection()
    cur = conn.cursor()

    if employee_id is not None and employee_id > 0:
        cur.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
    else:
        # Delete by exact name. (LLM is instructed to ask for clarification if needed.)
        cur.execute("DELETE FROM employees WHERE name = ?", (name,))

    deleted = cur.rowcount
    conn.commit()
    conn.close()

    if deleted == 0:
        return {
            "status": "not_found",
            "deleted": 0,
            "message": "No matching employee found to delete.",
        }
    else:
        return {
            "status": "success",
            "deleted": deleted,
            "message": f"Deleted {deleted} employee(s).",
        }

def search_employees(
    name: Optional[str] = None,
    role: Optional[str] = None,
    department: Optional[str] = None,
    min_salary: Optional[float] = None,
    max_salary: Optional[float] = None,
) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT id, name, role, department, salary
        FROM employees
        WHERE 1=1
    """
    params: List[Any] = []

    if name is not None:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    if role is not None:
        query += " AND role LIKE ?"
        params.append(f"%{role}%")
    if department is not None:
        query += " AND department LIKE ?"
        params.append(f"%{department}%")
    if min_salary is not None:
        query += " AND salary >= ?"
        params.append(float(min_salary))
    if max_salary is not None:
        query += " AND salary <= ?"
        params.append(float(max_salary))

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    employees = [
        {
            "id": row[0],
            "name": row[1],
            "role": row[2],
            "department": row[3],
            "salary": row[4],
        }
        for row in rows
    ]

    return {
        "status": "success",
        "count": len(employees),
        "employees": employees,
    }


# ==============================
# TOOL DEFINITIONS (for the LLM)
# ==============================

TOOLS = [
    {
        "type": "function",
        "name": "search_employees",
        "description": "Look up all employees or by name, role, department, salary range. Gives the employees (id, name, role, department, salary) that match the description and their count",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Filter by name (partial match allowed).",
                },
                "role": {
                    "type": "string",
                    "description": "Filter by role (partial match allowed).",
                },
                "department": {
                    "type": "string",
                    "description": "Filter by department (partial match allowed).",
                },
                "min_salary": {
                    "type": "number",
                    "description": "Minimum salary.",
                },
                "max_salary": {
                    "type": "number",
                    "description": "Maximum salary.",
                },
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "add_employee",
        "description": "Add a new employee to the database. We must add the employee as soon as we hire one.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Full name of the employee.",
                },
                "role": {
                    "type": "string",
                    "description": "Job title or role, e.g., 'Engineer', 'Manager'.",
                },
                "department": {
                    "type": "string",
                    "description": "Department name, e.g., 'HR', 'Engineering'.",
                },
                "salary": {
                    "type": "number",
                    "description": "Yearly salary in USD (or your currency).",
                },
            },
            "required": ["name"],
        },
    },
        {
        "type": "function",
        "name": "update_employee",
        "description": "Update an existing employee's name, department, or salary.",
        "parameters": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "integer",
                    "description": "The numeric ID of the employee to update.",
                },
                "name": {
                    "type": "string",
                    "description": "Exact name of the employee to update if ID is unknown.",
                },
                "new_name": {
                    "type": "string",
                    "description": "New name for the employee.",
                },
                "new_department": {
                    "type": "string",
                    "description": "New department for the employee.",
                },
                "new_salary": {
                    "type": "number",
                    "description": "New yearly salary for the employee.",
                },
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "delete_employee",
        "description": "Remove an employee from the database by id or by exact name.",
        "parameters": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "integer",
                    "description": "The numeric ID of the employee.",
                },
                "name": {
                    "type": "string",
                    "description": "Exact name of the employee, if ID is unknown.",
                },
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "initialize_database",
        "description": "ONLY used when explicitly asked to initialize db. NOT a solution when we actually need to add data or select smth. Creates an empty employees table in the SQLite database if it does not exist.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# ==============================
# TOOL CALL DISPATCH
# ==============================

def handle_tool_call(tool_call) -> Dict[str, Any]:
    """
    Map a tool_call from the model to the actual Python function,
    and wrap the result into a function_call_output object.
    """
    name = tool_call.name
    args_raw = tool_call.arguments or "{}"
    try:
        args = json.loads(args_raw)
    except json.JSONDecodeError:
        args = {}

    if name == "initialize_database":
        result = initialize_database()
    elif name == "add_employee":
        result = add_employee(
            name=args.get("name"),
            role=args.get("role"),
            department=args.get("department"),
            salary=args.get("salary"),
        )
    elif name == "update_employee":
        result = update_employee(
            employee_id=args.get("employee_id"),
            name=args.get("name"),
            new_name=args.get("new_name"),
            new_department=args.get("new_department"),
            new_salary=args.get("new_salary"),
        )
    elif name == "delete_employee":
        result = delete_employee(
            employee_id=args.get("employee_id"),
            name=args.get("name"),
        )
    elif name == "search_employees":
        result = search_employees(
            name=args.get("name"),
            role=args.get("role"),
            department=args.get("department"),
            min_salary=args.get("min_salary"),
            max_salary=args.get("max_salary"),
        )
    else:
        result = {
            "status": "error",
            "message": f"Unknown tool name: {name}",
        }

    return {
        "type": "function_call_output",
        "call_id": tool_call.call_id,
        "output": json.dumps(result),
    }


# ==============================
# MAIN AGENT LOOP
# ==============================

def main():
    print("=== HR Agent connected to SQLite (company.db) ===")
    print("Type natural language commands, e.g.:")
    print("  - 'We just hired John Doe. He's an Engineer making 80000.'")
    print("  - 'Mary got promoted to Head of IT. Increase her salary to 300K.'")
    print("  - 'Show me all Engineers.'")
    print("  - 'How many people named 'Alice' do we have?'")
    print("  - 'Fire John Doe.'")
    print("Type 'exit' or 'quit' to stop.")
    print()

    # Ensure DB exists from the start
    initialize_database()

    # Keep last 10 user–agent pairs as context
    history: List[Dict[str, str]] = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        if not user_input:
            continue

        # 1. Build the input list for this turn
        recent_history = history[-20:]  # up to 10 (user, assistant) pairs
        input_items: List[Any] = recent_history + [
            {"role": "user", "content": user_input}
        ]

        # 2. First call: let the model decide tools to call
        response = client.responses.create(
            model=MODEL,
            tools=TOOLS,
            input=input_items,
            instructions=SYSTEM_INSTRUCTIONS,
        )

        # Save the output to the running list
        input_items += response.output

        # 3. Execute any requested tools
        tool_calls = [item for item in response.output if item.type == "function_call"]

        if tool_calls:
            tool_outputs = [handle_tool_call(tc) for tc in tool_calls]

            # 4. Add tool outputs to the input for the second call
            input_items.extend(tool_outputs)

            # 5. Second call: get natural language confirmation / explanation
            final_response = client.responses.create(
                model=MODEL,
                tools=TOOLS,
                input=input_items,
                instructions=SYSTEM_INSTRUCTIONS,
            )

            agent_text = final_response.output_text
        else:
            # No tools needed; just answer directly
            agent_text = response.output_text

        print("Agent:", agent_text)

        # Update conversation history (keep all; we slice when sending)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": agent_text})


if __name__ == "__main__":
    main()
