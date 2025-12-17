import os
from pathlib import Path

AGENT_TEMPLATE = """---
name: {name}
description: "[SHORT DESCRIPTION]"
default_model: auto
---

# Invocation Rules
**Когда вызывать:**
[WHEN TO CALL THIS AGENT]

**Входные данные (`context`):**
[WHAT INPUTS DOES THIS AGENT NEED]

**Ожидаемый результат:**
[WHAT IS THE OUTPUT]

**Следующие шаги:**
[WHICH AGENT TO CALL NEXT]

**Максимум итераций:** N

# Prompt
Ты — {name}. Твоя задача — [MAIN GOAL].

## ТВОЯ РОЛЬ
[DETAILED ROLE DESCRIPTION]

## ВХОДНЫЕ ДАННЫЕ
[INPUT DATA DETAILS]

## ТВОЯ ЗАДАЧА
[DETAILED TASK DESCRIPTION]

## ИНСТРУМЕНТЫ
У тебя есть доступ к инструментам:
[LIST RELEVANT TOOLS]

## ПРАВИЛА
[RULES AND GUIDELINES]

## ПРИМЕР ОТВЕТА
[EXAMPLE]

## ФОРМАТ ВЫХОДНЫХ ДАННЫХ
[OUTPUT FORMAT]
"""

def create_agent_scaffold(path: str, name: str = "New Agent") -> str:
    """Creates a scaffold for a new agent definition file.

    Args:
        path: The path where the agent definition file should be created.
        name: The display name of the agent.

    Returns:
        A prompt string instructing the LLM on next steps.
    """
    file_path = Path(path)
    
    # If path is a directory, append a filename based on name
    if file_path.is_dir() or (not file_path.suffix and not str(file_path).endswith('.md')):
        if file_path.is_dir():
             filename = name.lower().replace(" ", "_") + ".md"
             file_path = file_path / filename
        else:
             # It's a path without extension that doesn't exist as a dir, treat as file
             file_path = file_path.with_suffix(".md")

    # Ensure parent directories exist
    file_path.parent.mkdir(parents=True, exist_ok=True)

    content = AGENT_TEMPLATE.format(name=name)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return (
        f"I have created a scaffold for the new agent at `{file_path}`.\n"
        f"Please read this file to understand the structure.\n"
        f"Then, ask the user for the specific details of this new agent (role, responsibilities, inputs, outputs, workflow).\n"
        f"Once you have the details, please fill in the placeholders in `{file_path}` with the appropriate content."
    )

