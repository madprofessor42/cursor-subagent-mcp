# Установка Cursor CLI (cursor-agent)

Для работы MCP-сервера необходим `cursor-agent` — CLI инструмент Cursor.

## Способ 1: Через приложение Cursor (рекомендуется)

1. Откройте приложение Cursor
2. Откройте Command Palette: `Cmd+Shift+P` (macOS) или `Ctrl+Shift+P` (Linux/Windows)
3. Введите и выберите: `Shell Command: Install 'cursor' command in PATH`

Это добавит команды `cursor` и `cursor-agent` в ваш PATH.

## Способ 2: Через терминал

Скрипт установки сжат gzip, поэтому нужно распаковать:

```sh
curl -L https://cursor.com/install | gunzip | bash
```

Или пошагово:

```sh
# Скачать и распаковать
curl -L https://cursor.com/install | gunzip > /tmp/cursor-install.sh

# Запустить
bash /tmp/cursor-install.sh
```

## Добавление в PATH

После установки добавьте `~/.local/bin` в переменную `PATH`:

**Для Bash** (добавить в `~/.bashrc`):

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Для Zsh** (добавить в `~/.zshrc`):

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

```

## Проверка установки

```sh
cursor-agent --version
```

## Основные команды

```sh
# Запуск агента в неинтерактивном режиме
# --print (-p) включает non-interactive режим
# prompt передаётся как позиционный аргумент
cursor-agent --print --model "<model>" -f "<prompt>"

# Пример
cursor-agent --print --model "opus-4.5" -f "Напиши Hello World на Python"

# С JSON выводом для парсинга
cursor-agent --print --output-format json --model "opus-4.5" -f "<prompt>"

# Со стримингом событий в реальном времени
cursor-agent --print --output-format stream-json --model "opus-4.5" -f "<prompt>"

# С рандомной моедлью
cursor-agent --print --output-format stream-json --model "auto" -f "Напиши Hello World на Python"

```



---

# Установка и базовое использование uv

## Установка

Рекомендуемый способ установки через официальный скрипт:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Альтернативный способ через pip:

```sh
pip install uv
```

## Проверка версии

Проверьте установленную версию uv:

```sh
uv --version
```

## Управление версиями Python через uv

- Установить Python 3.11:

```sh
uv python install 3.11
```

- Посмотреть список установленных версий Python:

```sh
uv python list
```

## Инициализация и виртуальное окружение

- Инициализация проекта с указанием версии Python:

```sh
uv init --python 3.11 .
```

- Создание виртуального окружения (.venv):

```sh
uv venv
```

- Активация / Деактивация рабочего окружения

```sh
source .venv/bin/activate
deactivate
```

## Работа с зависимостями
- Установка новой библиотеки:
Через флаг --upgrade можно обновить все библиотеки, для которых доступны новые версии

```sh
uv add requests
```

- Установка библиотеки в dev-группу:

```sh
uv add --dev ruff
```

- Удаление библиотеки:

```sh
uv remove requests
```

## Запуск кода

- Запуск скрипта:

```sh
uv run src/app.py
```

- Запуск модуля:

```sh
uv run python -m src.app
```

- Установка всех зависимостей

```sh
uv sync
```


# Файл pyproject.toml

- Что бы указать дополнительный репозиторий, добавляем его в [[tool.uv.index]]
Указываем default = true, что бы использовать по дефолту

```toml
[[tool.uv.index]]
name = "pypi"
url = "https://pypi.org/simple/"
default = true

[[tool.uv.index]]
name = "<custom_name>"
url = "<custom_url>"
```


- Что бы указать какой пакет из какого репозитория качать - добавляем связь по имени репозитория

```toml
[tool.uv.sources]
some_package = { index = "<custom_name>" }
```


Для того что бы VS код использовал то же окружение что и в терминале, делаем следующее

```bash
1. В терминале где активировано окружение ввести и скопировать результат
   which python

2. VScode - открыть меню команд:
   Shift + Command + P

3. Ввести и выбрать
   Python: Select Interpreter

4. Вставить ранее скопированный путь
```



