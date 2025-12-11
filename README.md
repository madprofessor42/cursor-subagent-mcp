# Cursor Subagent MCP Server

MCP-сервер для оркестрации мультиагентной разработки в Cursor. Позволяет основному агенту в UI Cursor вызывать специализированных субагентов через `cursor-agent` CLI.

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                        Cursor UI                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Orchestrator Agent (UI)                   │  │
│  │   Координирует работу, определяет следующие шаги      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server (this package)                 │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────────────┐   │
│  │ list_agents │ │get_agent_   │ │   invoke_subagent    │   │
│  │             │ │   prompt    │ │                      │   │
│  └─────────────┘ └─────────────┘ └──────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ subprocess
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     cursor-agent CLI                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Analyst  │ │Architect │ │ Planner  │ │Developer │ ...   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Установка

### Требования

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (рекомендуется) или pip
- Cursor с установленным CLI (`cursor-agent`)

### Установка с uv

```bash
# Клонирование репозитория
git clone <repository-url>
cd cursor-subagent-mcp

# Установка зависимостей
uv sync
```

### Установка с pip

```bash
pip install -e .
```

## Настройка Cursor

Добавьте MCP-сервер в конфигурацию Cursor. Создайте или отредактируйте файл `.cursor/mcp.json` в корне проекта:

```json
{
  "mcpServers": {
    "subagent": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/cursor-subagent-mcp", "cursor-subagent-mcp"]
    }
  }
}
```

Или для глобальной установки:

```json
{
  "mcpServers": {
    "subagent": {
      "command": "cursor-subagent-mcp"
    }
  }
}
```

## Доступные инструменты

### `list_agents`

Возвращает список всех доступных субагентов с их описаниями.

```
Агенты:
- analyst: Создаёт ТЗ с юзер-кейсами
- tz_reviewer: Проверяет качество ТЗ
- architect: Проектирует архитектуру
- architecture_reviewer: Проверяет архитектуру
- planner: Создаёт план задач
- plan_reviewer: Проверяет план
- developer: Реализует код и тесты
- code_reviewer: Проверяет код
```

### `get_agent_prompt`

Возвращает полный системный промпт агента для инспекции.

**Параметры:**
- `agent_role` (str): Идентификатор роли агента

### `invoke_subagent`

Вызывает субагента для выполнения задачи.

**Параметры:**
- `agent_role` (str): Роль агента для вызова
- `task` (str): Задача для агента
- `context` (str, optional): Дополнительный контекст
- `model` (str, optional): Переопределение модели
- `timeout` (float, optional): Таймаут в секундах

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

### `check_status`

Проверяет статус сервера и его зависимостей.

## Процесс разработки

Рекомендуемый процесс мультиагентной разработки:

### Этап 1: Анализ
```
1. invoke_subagent(agent_role="analyst", task="<постановка задачи>")
   → Получаем ТЗ

2. invoke_subagent(agent_role="tz_reviewer", task="Проверь ТЗ", context="<ТЗ>")
   → Получаем замечания

3. При наличии замечаний:
   invoke_subagent(agent_role="analyst", task="Исправь замечания: <замечания>", context="<ТЗ>")
```

### Этап 2: Архитектура
```
4. invoke_subagent(agent_role="architect", task="Спроектируй архитектуру", context="<ТЗ>")
   → Получаем архитектуру

5. invoke_subagent(agent_role="architecture_reviewer", task="Проверь архитектуру", context="<ТЗ + архитектура>")
   → Получаем замечания
```

### Этап 3: Планирование
```
6. invoke_subagent(agent_role="planner", task="Создай план задач", context="<ТЗ + архитектура>")
   → Получаем план

7. invoke_subagent(agent_role="plan_reviewer", task="Проверь план", context="<ТЗ + план>")
   → Получаем замечания
```

### Этап 4: Разработка
```
Для каждой задачи из плана:

8. invoke_subagent(agent_role="developer", task="Выполни задачу: <описание>", context="<код проекта>")
   → Получаем изменения

9. invoke_subagent(agent_role="code_reviewer", task="Проверь изменения", context="<изменения + задача>")
   → Получаем замечания
```

## Конфигурация агентов

Агенты настраиваются через файл `agents.yaml`:

```yaml
agents:
  analyst:
    name: "Аналитик"
    description: "Создаёт ТЗ с юзер-кейсами"
    prompt_file: "agents-master/02_analyst_prompt.md"
    default_model: "claude-sonnet-4-20250514"

  # ... остальные агенты
```

### Поддерживаемые параметры

- `name`: Человекочитаемое имя агента
- `description`: Описание роли агента
- `prompt_file`: Путь к файлу с системным промптом
- `default_model`: Модель по умолчанию

## Промпты агентов

Промпты агентов находятся в директории `agents-master/`:

| Файл | Роль |
|------|------|
| `02_analyst_prompt.md` | Аналитик |
| `03_tz_reviewer_prompt.md` | Ревьюер ТЗ |
| `04_architect_prompt.md` | Архитектор |
| `05_architecture_reviewer_prompt.md` | Ревьюер архитектуры |
| `06_agent_planner.md` | Планировщик |
| `07_agent_plan_reviewer.md` | Ревьюер плана |
| `08_agent_developer.md` | Разработчик |
| `09_agent_code_reviewer.md` | Ревьюер кода |

## Пример использования

После настройки MCP-сервера в Cursor, используйте агента-оркестратора в UI:

```
Используя подход по оркестрации мультиагентной разработки, 
выполни разработку системы по следующей постановке:

<ваша постановка задачи>

Инструкция оркестратора находится в agents-master/01_orchestrator.md.
Вызывай субагентов через MCP tool invoke_subagent.
```

## Разработка

### Запуск тестов

```bash
uv run pytest
```

### Локальный запуск сервера

```bash
uv run cursor-subagent-mcp
```

## Лицензия

MIT
