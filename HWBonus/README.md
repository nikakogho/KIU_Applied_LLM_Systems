# HR SQLite Agent (OpenAI Tool-Calling Demo)

This project implements a small **AI agent** that manages a **SQLite employee database** using **natural-language commands**.

You talk to it like an HR manager:

> “We just hired John Doe. He’s an Engineer making 80k.”

The agent uses the OpenAI API with **function calling (tools)** to:

1. Interpret what you said.
2. Decide which Python function to call (`add_employee`, `search_employees`, etc.).
3. Run real SQL against a persistent `company.db` SQLite file.
4. Respond in clear English with what it did and what it found.

---

## Features

* ✅ Persistent **SQLite** database (`company.db`).
* ✅ Employee records with: `id`, `name`, `role`, `department`, `salary`.
* ✅ OpenAI **tool-calling** for safe operations (LLM never writes raw SQL).
* ✅ Tools for:

  * Initializing the DB (`initialize_database`)
  * Adding employees (`add_employee`)
  * Updating employee name/department/salary (`update_employee`)
  * Deleting employees (`delete_employee`)
  * Searching employees (`search_employees`)
* ✅ Conversation memory: last **10 user–agent pairs** kept as context.
* ✅ Safety guidance in the system prompt:

  * Prefer updates/deletes by **ID**.
  * Ask for clarification if an operation is ambiguous.

---

## Requirements

* **Python** 3.9+ (recommended)
* Python packages:

  * `openai`
  * `sqlite3` (built into Python standard library)
* Environment variables:

  * `OPENAI_API_KEY` – your OpenAI API key.
  * Optional: `OPENAI_MODEL` – override the default model.

By default, the script uses:

```python
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
```

So if `OPENAI_MODEL` is not set, it uses `gpt-4.1-mini`.

---

## Installation & Setup

1. **Create & activate a virtual environment** (optional but recommended):

   ```bash
   python -m venv venv
   # On PowerShell
   .\venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**:

   ```bash
   pip install openai
   ```

3. **Set your OpenAI API key** (PowerShell example):

   ```powershell
   $env:OPENAI_API_KEY = "sk-..."   # paste your real key here
   ```

   Or on Linux/macOS:

   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

4. (Optional) **Choose a different model**:

   ```powershell
   $env:OPENAI_MODEL = "gpt-4.1"
   ```

5. Make sure the script file (e.g. `db-agent.py`) is in your working directory.

---

## Running the Agent

From the folder containing the script:

```bash
python db-agent.py
```

You should see something like:

```text
=== HR Agent connected to SQLite (company.db) ===
Type natural language commands, e.g.:
  - 'We just hired John Doe. He's an Engineer making 80000.'
  - 'Mary got promoted to Head of IT. Increase her salary to 300K.'
  - 'Show me all Engineers.'
  - 'How many people named 'Alice' do we have?'
  - 'Fire John Doe.'
Type 'exit' or 'quit' to stop.
```

Then you can start typing natural-language commands.

Type `exit` or `quit` to terminate.

---

## High-Level Architecture

The script has three main layers:

1. **Database layer** (SQLite helpers)
2. **Tool definitions** (JSON schemas for the LLM)
3. **Agent loop** (OpenAI function-calling logic + conversation memory)

### 1. Database Layer

All DB operations are implemented in Python and use parameterized SQL (no raw SQL from the LLM).

**Database file**

* `DB_PATH = "company.db"`
* Table: `employees`

Schema:

```sql
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT,
    department TEXT,
    salary REAL
);
```

Helper:

```python
def get_connection():
    return sqlite3.connect(DB_PATH)
```

#### `initialize_database()`

* Creates the `employees` table if it doesn’t exist.
* Returns: JSON like

  ```python
  {
      "status": "success",
      "message": "Database initialized and employees table ready."
  }
  ```

The script calls this **once at startup** and it’s also exposed as a tool (`initialize_database`) when the user explicitly asks.

#### `add_employee(name, role=None, department=None, salary=None)`

Inserts a new row:

```sql
INSERT INTO employees (name, role, department, salary)
VALUES (?, ?, ?, ?)
```

Returns:

```python
{
    "status": "success",
    "employee_id": <new_id>,
    "name": name,
    "role": role,
    "department": department,
    "salary": salary,
}
```

#### `update_employee(employee_id=None, name=None, new_name=None, new_department=None, new_salary=None)`

Updates an employee’s **name**, **department**, or **salary**.

* Identification:

  * Prefer `employee_id` if given and > 0.
  * Otherwise falls back to exact `name` matches (may update multiple rows).
* Only fields with non-empty values are updated:

  * `new_name` is ignored if empty string.
  * `new_department` is ignored if empty string.
  * `new_salary` is ignored if `None` or `0`.

Builds a dynamic query like:

```sql
UPDATE employees
SET name = ?, department = ?, salary = ?
WHERE id = ?  -- or WHERE name = ?
```

Returns:

* If no matching rows:

  ```python
  {
      "status": "not_found",
      "updated": 0,
      "message": "No matching employee found to update.",
  }
  ```

* If success:

  ```python
  {
      "status": "success",
      "updated": <n>,
      "message": "Updated <n> employee(s).",
  }
  ```

> **Note:** The system instructions tell the LLM to:
>
> * First **search** (get IDs),
> * Confirm with the user,
> * Then update by ID.
>   This policy is encoded in the system prompt rather than enforced by extra code.

#### `delete_employee(employee_id=None, name=None)`

Deletes one or more employees.

* If `employee_id` is provided and > 0:

  ```sql
  DELETE FROM employees WHERE id = ?
  ```

* Otherwise:

  ```sql
  DELETE FROM employees WHERE name = ?
  ```

Returns:

* If no match:

  ```python
  {
      "status": "not_found",
      "deleted": 0,
      "message": "No matching employee found to delete.",
  }
  ```

* On success:

  ```python
  {
      "status": "success",
      "deleted": <n>,
      "message": "Deleted <n> employee(s).",
  }
  ```

Again, the **system prompt** encourages the LLM to look up IDs first via `search_employees` and only call `delete_employee` by ID in ambiguous cases.

#### `search_employees(name=None, role=None, department=None, min_salary=None, max_salary=None)`

Flexible filtering:

* All filters are **optional**.
* Partial matches for `name`, `role`, `department` using `LIKE`.
* Range filtering for `salary`.

Example query built:

```sql
SELECT id, name, role, department, salary
FROM employees
WHERE 1=1
  AND name LIKE ?
  AND role LIKE ?
  AND department LIKE ?
  AND salary >= ?
  AND salary <= ?
```

Returns:

```python
{
    "status": "success",
    "count": <number_of_employees>,
    "employees": [
        {
            "id": ...,
            "name": ...,
            "role": ...,
            "department": ...,
            "salary": ...
        },
        ...
    ],
}
```

---

### 2. Tool Definitions (for the LLM)

The `TOOLS` list defines how the model can interact with the DB via function calling (tools):

```python
TOOLS = [
    { "type": "function", "name": "search_employees", ... },
    { "type": "function", "name": "add_employee", ... },
    { "type": "function", "name": "update_employee", ... },
    { "type": "function", "name": "delete_employee", ... },
    { "type": "function", "name": "initialize_database", ... },
]
```

Each tool includes:

* `name` – maps to the Python function.
* `description` – instructs the LLM when to use it.
* `parameters` – JSON schema object with fields and types.

Example (simplified):

```python
{
    "type": "function",
    "name": "add_employee",
    "description": "Add a new employee to the database. We must add the employee as soon as we hire one.",
    "parameters": {
        "type": "object",
        "properties": {
            "name":        {"type": "string"},
            "role":        {"type": "string"},
            "department":  {"type": "string"},
            "salary":      {"type": "number"},
        },
        "required": ["name"],
    },
}
```

The **system instructions** also tell the LLM:

* Typical departments: Engineering, HR, Sales, Marketing, Support, Security, Legal.
* Map fuzzy language like “guards” to “Security”.
* Never output raw SQL; only use tools.
* For updates/deletes:

  * Search first, show IDs to the user.
  * Then update/delete by ID.

---

### 3. Tool Call Dispatch

`handle_tool_call(tool_call)` is the bridge between the LLM’s tool call and actual Python functions.

* Reads `tool_call.name` (e.g. `"add_employee"`).
* Parses JSON arguments.
* Calls the corresponding Python function.
* Wraps the result as a `function_call_output` object:

```python
return {
    "type": "function_call_output",
    "call_id": tool_call.call_id,
    "output": json.dumps(result),
}
```

These tool outputs are then fed back into the model on the second call so it can explain the result in natural language.

---

### 4. Agent Loop & Conversation Memory

The `main()` function implements the interaction loop:

1. **Startup**

   * Prints usage hints.
   * Calls `initialize_database()` to ensure `company.db` exists.
   * Initializes `history: List[Dict[str, str]] = []`.

2. **Per turn**

   * Reads user input from the terminal.

   * Builds `recent_history` with the last **20 messages** (10 user–assistant pairs).

   * Constructs `input_items`:

     ```python
     recent_history = history[-20:]
     input_items = recent_history + [
         {"role": "user", "content": user_input}
     ]
     ```

   * Calls:

     ```python
     response = client.responses.create(
         model=MODEL,
         tools=TOOLS,
         input=input_items,
         instructions=SYSTEM_INSTRUCTIONS,
     )
     ```

   * Appends `response.output` to `input_items`.

   * Extracts any `function_call` items.

   * If there are tool calls:

     * Executes each via `handle_tool_call`.
     * Appends the tool outputs to `input_items`.
     * Makes a **second** `client.responses.create(...)` call to generate a final natural-language answer.

   * If there are no tool calls:

     * Uses `response.output_text` directly.

   * Prints:

     ```python
     print("Agent:", agent_text)
     ```

   * Updates conversation memory:

     ```python
     history.append({"role": "user", "content": user_input})
     history.append({"role": "assistant", "content": agent_text})
     ```

This means the agent maintains **short-term memory** over the last 10 exchanges, which helps with follow-ups like “Actually, give him a raise” or “Fire the new guy we just hired”.

---

## Example Prompts & Expected Behaviors

Below are some example prompts you can try after running `python db-agent.py`.

> **Note:** Actual wording of the agent’s response will vary, but it should:
>
> * Call the appropriate tools.
> * Report IDs, names, roles, departments, and salaries in a human-readable way.
> * Follow the safety instructions in the system prompt.

### 1. Initialize / Check the Database

```text
You: Initialize the database.
```

The agent will call `initialize_database` (even though startup already did it) and confirm that the `employees` table is ready.

### 2. Hire an Employee

```text
You: We just hired John Doe. He's an Engineer in Engineering making 80000.
```

LLM behavior:

* Decide to call `add_employee` with:

  * `name="John Doe"`
  * `role="Engineer"`
  * `department="Engineering"`
  * `salary=80000`
* Agent response (example):

  > Added new employee John Doe (ID: 3) as an Engineer in Engineering with a salary of 80000.

### 3. List All Engineers

```text
You: Show me all engineers.
```

LLM behavior:

* Call `search_employees(role="Engineer")`.
* Get back a list of rows.
* Respond with something like:

  > Found 5 engineers:
  >
  > * ID 1: Alice Smith – Engineer – Engineering – 90000
  > * ID 3: John Doe – Engineer – Engineering – 80000
  >   ...

### 4. Give a Raise / Move Department

```text
You: John Doe should now earn 95000 and move to HR.
```

Expected pattern:

1. LLM first calls `search_employees(name="John Doe")` to get IDs and confirm which John Doe you mean.
2. After confirming with you (if needed), it calls `update_employee` by `employee_id`.

Backend: `update_employee(employee_id=<id_of_john>, new_department="HR", new_salary=95000)`

### 5. Count People in a Department

```text
You: How many people do we have in HR?
```

Likely behavior:

* `search_employees(department="HR")`
* Count the number of employees and tell you:

  > There are 4 people in HR. Here they are:
  >
  > * ID 2: Mary Johnson – HR Manager – HR – 110000
  > * ...

### 6. Fire an Employee

```text
You: Fire John Doe.
```

Expected pattern:

1. LLM calls `search_employees(name="John Doe")` to see how many matches there are.
2. If there’s exactly one, it can proceed with `delete_employee(employee_id=<id>)`.
3. If there are multiple John Does, it should ask:

   > I found 2 people named John Doe (IDs 3 and 7). Which one should I remove?

After you specify the ID:

```text
You: Delete the one with ID 3.
```

The LLM calls `delete_employee(employee_id=3)`.

---

## Inspecting the Database Manually (Optional)

If you want to see what’s in `company.db` outside of the agent:

```bash
python
```

```python
import sqlite3
conn = sqlite3.connect("company.db")
cur = conn.cursor()
cur.execute("SELECT * FROM employees")
rows = cur.fetchall()
for row in rows:
    print(row)
conn.close()
```

You should see tuples:

```text
(1, 'Alice Smith', 'Engineer', 'Engineering', 90000.0)
(2, 'Mary Johnson', 'HR Manager', 'HR', 110000.0)
...
```

---

## Design Notes & Possible Extensions

* **Safety via tools**:

  * The LLM never writes SQL directly.
  * All changes go through controlled Python functions.
* **Ambiguity handling**:

  * The system prompt tells the model to avoid destructive actions when multiple rows may match a name and to ask for clarification instead.
* **Departments**:

  * The system prompt hints about typical departments and how to map fuzzy terms like “guards” → “Security”.

### Extensions you could add

* Support **updating roles** (extend `update_employee` with `new_role`).
* Add more fields (hire date, manager ID, performance score, etc.).
* Add support for bulk operations (e.g. “Give all Engineers a 5% raise”).
* Wrap this in a web UI or chat UI instead of terminal.

---

## Summary

This script is a complete working example of:

* Turning **natural language** into **structured database operations**.
* Using the OpenAI **Responses API** and **tool calling** to keep the model away from raw SQL.
* Maintaining **short-term conversational memory** so the agent can handle follow-ups like “Actually, give him a raise” or “Fire the last person we hired”.

Run `db-agent.py`, talk to it like an HR manager, and it will keep your `company.db` in sync.
