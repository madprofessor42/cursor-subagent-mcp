# Cursor Subagent MCP Server

MCP-сервер для оркестрации мультиагентной разработки в Cursor. Позволяет основному агенту в UI Cursor вызывать специализированных субагентов через `cursor-agent` CLI.

## Зачем это нужно?

### 🧠 Контекст не разбухает

При работе над большой задачей контекст основного агента быстро переполняется. С мультиагентным подходом:
- Каждый субагент работает в **изолированном контексте**
- Основной агент хранит только **результаты** работы субагентов
- Можно выполнять задачи любой сложности без потери контекста

### 📝 Готовые промпты для каждой роли

Не нужно каждый раз придумывать как правильно поставить задачу:
- **9 специализированных агентов** с отточенными промптами
- Executor для простых задач, Аналитик, Архитектор, Планировщик, Разработчик и их ревьюеры
- Промпты оптимизированы для качественного результата

### 🔄 Отлаженный workflow

Процесс разработки структурирован и предсказуем:
- **Анализ → Архитектура → Планирование → Разработка**
- Каждый этап включает review с ограничением итераций
- Автоматическая остановка при критичных проблемах

### ⚡ Параллельная работа

Субагенты запускаются через отдельные процессы `cursor-agent`:
- Не блокируют основной агент
- Могут использовать разные модели для разных задач
- Результаты кэшируются и переиспользуются

### 🎯 Разделение ответственности

Каждый агент фокусируется на своей задаче:
- **Аналитик** — только ТЗ, не пишет код
- **Архитектор** — только архитектура, не реализация
- **Разработчик** — строго по плану, не рефакторит лишнее
- **Ревьюеры** — независимая проверка качества

## Архитектура

```mermaid
flowchart TB
    subgraph CursorUI ["Cursor UI"]
        User["👤 User<br/><i>Задача...</i>"]
        Orchestrator["🎯 Orchestrator Agent<br/><i>Claude в UI</i>"]
    end
    
    subgraph MCPServer ["cursor-subagent MCP Server"]
        GetGuide["get_orchestration_guide()"]
        InvokeSubagent["invoke_subagent()"]
        CheckStatus["check_status()"]
        SetupCLI["setup_cursor_cli()"]
    end
    
    subgraph Files ["Файлы конфигурации"]
        OrchestratorMD["01_orchestrator.md"]
        AgentsYAML["agents.yaml"]
        PromptFiles["02-10_*.md<br/><i>промпты агентов</i>"]
    end
    
    subgraph CLI ["cursor-agent CLI"]
        Executor["executor<br/><i>простые задачи</i>"]
        Analyst["analyst"]
        TZReviewer["tz_reviewer"]
        Architect["architect"]
        ArchReviewer["architecture_reviewer"]
        Planner["planner"]
        PlanReviewer["plan_reviewer"]
        Developer["developer"]
        CodeReviewer["code_reviewer"]
    end

    User -->|"задача"| Orchestrator
    
    Orchestrator -->|"MCP"| GetGuide
    Orchestrator -->|"MCP"| InvokeSubagent
    Orchestrator -->|"MCP"| CheckStatus
    Orchestrator -->|"MCP"| SetupCLI
    
    GetGuide -.->|"читает"| OrchestratorMD
    GetGuide -.->|"читает"| AgentsYAML
    
    InvokeSubagent -.->|"читает промпт"| PromptFiles
    InvokeSubagent -->|"subprocess"| CLI
    
    CLI -->|"output"| InvokeSubagent
    InvokeSubagent -->|"результат"| Orchestrator
    Orchestrator -->|"context"| Orchestrator
    Orchestrator -->|"итог"| User
```

### Как работает workflow

1. **User** даёт задачу Orchestrator Agent в Cursor UI
2. **Orchestrator** вызывает `get_orchestration_guide()` — получает инструкции и список агентов
3. **Orchestrator** классифицирует задачу:

   **Простая задача** (исследование, мелкие правки, добавление атрибутов):
   - Вызывает `executor` напрямую → получает результат

   **Сложная задача** (новый функционал, архитектурные изменения):
   - **Сначала**: `executor` (исследование проекта)
   - **Затем**: `analyst` → `tz_reviewer` → `architect` → `architecture_reviewer` → `planner` → `plan_reviewer` → `developer` → `code_reviewer`

4. Результат каждого агента передаётся следующему через параметр `context`
5. **Orchestrator** возвращает финальный результат пользователю

> **Важно:** Orchestrator — только координатор! Он НЕ исследует код, НЕ анализирует проект сам. Всё делегируется субагентам через `invoke_subagent()`.

### Sequence диаграмма (простые задачи)

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant O as 🎯 Orchestrator
    participant MCP as ⚙️ MCP Server
    participant CLI as 🔧 cursor-agent

    U->>O: Поисследуй структуру проекта
    
    Note over O,MCP: Получение инструкций
    O->>MCP: get_orchestration_guide()
    MCP-->>O: {guide, agents}
    
    Note over O: Классификация: простая задача
    O->>MCP: invoke_subagent(executor, task)
    MCP->>CLI: cursor-agent -p "executor prompt"
    CLI-->>MCP: output/analysis.md
    MCP-->>O: {success, output_file, modified_files}
    
    O->>U: ✅ Результат в output/analysis.md
```

### Sequence диаграмма (сложные задачи)

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant O as 🎯 Orchestrator
    participant MCP as ⚙️ MCP Server
    participant CLI as 🔧 cursor-agent

    U->>O: Разработай REST API для пользователей
    
    Note over O,MCP: Получение инструкций
    O->>MCP: get_orchestration_guide()
    MCP-->>O: {guide, agents}
    
    Note over O,CLI: Этап 0: Исследование проекта
    O->>MCP: invoke_subagent(executor, "Исследуй проект")
    MCP->>CLI: cursor-agent -p "executor prompt"
    CLI-->>MCP: output/project_analysis.md
    MCP-->>O: {success, output_file}
    
    Note over O,CLI: Этап 1: Анализ
    O->>MCP: invoke_subagent(analyst, task, context=исследование)
    MCP->>CLI: cursor-agent -p "analyst prompt"
    CLI-->>MCP: ТЗ
    MCP-->>O: {success, output: ТЗ}
    
    O->>MCP: invoke_subagent(tz_reviewer, context=ТЗ)
    MCP->>CLI: cursor-agent -p "reviewer prompt"
    CLI-->>MCP: замечания / ✅ OK
    MCP-->>O: {success, output}
    
    Note over O,CLI: Этап 2: Архитектура
    O->>MCP: invoke_subagent(architect, context=ТЗ)
    MCP->>CLI: cursor-agent -p "architect prompt"
    CLI-->>MCP: архитектура
    MCP-->>O: {success, output}
    
    O->>MCP: invoke_subagent(architecture_reviewer, context)
    MCP->>CLI: cursor-agent -p "reviewer prompt"
    CLI-->>MCP: ✅ OK
    MCP-->>O: {success, output}
    
    Note over O,CLI: Этап 3: Планирование
    O->>MCP: invoke_subagent(planner, context)
    MCP->>CLI: cursor-agent -p "planner prompt"
    CLI-->>MCP: план задач
    MCP-->>O: {success, output}
    
    O->>MCP: invoke_subagent(plan_reviewer, context)
    MCP->>CLI: cursor-agent -p "reviewer prompt"
    CLI-->>MCP: ✅ OK
    MCP-->>O: {success, output}
    
    Note over O,CLI: Этап 4: Разработка (для каждой задачи)
    loop Для каждой задачи из плана
        O->>MCP: invoke_subagent(developer, task=задача)
        MCP->>CLI: cursor-agent -p "developer prompt"
        CLI-->>MCP: код + тесты
        MCP-->>O: {success, output}
        
        O->>MCP: invoke_subagent(code_reviewer, context=код)
        MCP->>CLI: cursor-agent -p "reviewer prompt"
        CLI-->>MCP: ✅ OK
        MCP-->>O: {success, output}
    end
    
    O->>U: ✅ Разработка завершена
```

## Быстрый старт

### 1. Установка

```bash
git clone https://github.com/your-repo/cursor-subagent-mcp
cd cursor-subagent-mcp
uv sync
```

### 2. Настройка MCP

Создайте `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "cursor-subagent": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/cursor-subagent-mcp", "cursor-subagent-mcp"]
    }
  }
}
```

> **Важно:** Замените `/path/to/cursor-subagent-mcp` на реальный путь к клонированному репозиторию.

### 3. Установка cursor-agent CLI

Попросите агента:
```
Вызови setup_cursor_cli для установки cursor-agent
```

Или вручную:
```bash
curl -L https://cursor.com/install | gunzip | bash

# Добавление в PATH (для bash)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Или для zsh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 4. Проверка

```
Вызови check_status
```

Ожидаемый ответ:
```json
{
  "cursor_agent_available": true,
  "cursor_agent_message": "cursor-agent found at: /Users/.../.local/bin/cursor-agent",
  "config_loaded": true,
  "agent_count": 9
}
```

## Использование

Просто дайте задачу агенту:

```
Разработай REST API для управления пользователями с авторизацией через JWT.
```

Агент автоматически:
1. Вызовет `get_orchestration_guide()` — получит инструкции
2. Запустит workflow: analyst → tz_reviewer → architect → ... → code_reviewer
3. Передаст результаты между агентами через `context`

## MCP Tools

| Tool | Описание |
|------|----------|
| `get_orchestration_guide()` | ⭐ **Вызывать первым!** Возвращает инструкции + список агентов |
| `invoke_subagent(agent_role, task, context)` | Вызывает субагента |
| `check_status()` | Проверяет доступность cursor-agent CLI |
| `setup_cursor_cli()` | Устанавливает cursor-agent CLI |

### invoke_subagent

```python
invoke_subagent(
    agent_role="executor",     # executor, analyst, architect, planner, developer, *_reviewer
    task="Поисследуй проект",  # задача
    context="...",             # код проекта или результаты предыдущих агентов
    model="claude-sonnet-4",   # опционально
    timeout=300                # опционально
)
```

**Возвращает:**
```json
{
  "success": true,
  "output": "Результат работы агента...",
  "error": null,
  "agent_role": "analyst",
  "model_used": "claude-sonnet-4-20250514"
}
```

## Агенты

| Роль | Описание | Промпт |
|------|----------|--------|
| `executor` | **Простые задачи:** исследование, мелкие правки, добавление атрибутов | `10_executor_agent.md` |
| `analyst` | Создаёт ТЗ с юзер-кейсами | `02_analyst_prompt.md` |
| `tz_reviewer` | Проверяет качество ТЗ | `03_tz_reviewer_prompt.md` |
| `architect` | Проектирует архитектуру | `04_architect_prompt.md` |
| `architecture_reviewer` | Проверяет архитектуру | `05_architecture_reviewer_prompt.md` |
| `planner` | Создаёт план задач | `06_agent_planner.md` |
| `plan_reviewer` | Проверяет план | `07_agent_plan_reviewer.md` |
| `developer` | Реализует код и тесты | `08_agent_developer.md` |
| `code_reviewer` | Проверяет код | `09_agent_code_reviewer.md` |

Промпты находятся в `agents-master/`. Конфигурация агентов в `agents.yaml`.

## Конфигурация

`agents.yaml`:

```yaml
agents:
  analyst:
    name: "Аналитик"
    description: "Создаёт ТЗ с юзер-кейсами"
    prompt_file: "agents-master/02_analyst_prompt.md"
    default_model: "claude-sonnet-4-20250514"
```

## Разработка

```bash
# Запуск тестов
uv run pytest

# Локальный запуск сервера
uv run cursor-subagent-mcp
```

## Лицензия

MIT
