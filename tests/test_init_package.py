"""Tests for package __init__.py module."""

import importlib
import inspect
from pathlib import Path

import pytest


def test_version_exists():
    """TC-UNIT-01: Проверка наличия __version__ в __init__.py"""
    from cursor_subagent_mcp import __version__

    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"


def test_version_accessible():
    """Проверка доступности версии через cursor_subagent_mcp.__version__"""
    import cursor_subagent_mcp

    assert hasattr(cursor_subagent_mcp, "__version__")
    assert cursor_subagent_mcp.__version__ == "0.1.0"


def test_init_file_minimal():
    """TC-UNIT-02: Проверка отсутствия ненужных экспортов"""
    import cursor_subagent_mcp

    # Получаем все публичные атрибуты модуля
    public_attrs = [
        name
        for name in dir(cursor_subagent_mcp)
        if not name.startswith("_") or name == "__version__"
    ]

    # Должен быть только __version__ (или минимальный набор)
    # Проверяем, что нет неожиданных экспортов
    unexpected_exports = [
        name
        for name in public_attrs
        if name not in ["__version__"] and not name.startswith("__")
    ]

    # Если есть другие экспорты, проверяем, что они не являются функциями/классами
    for name in unexpected_exports:
        attr = getattr(cursor_subagent_mcp, name)
        # Разрешаем только строки, числа и другие простые типы
        if callable(attr) or inspect.isclass(attr):
            pytest.fail(
                f"Unexpected export in __init__.py: {name} "
                f"(type: {type(attr).__name__})"
            )


def test_package_import():
    """Регрессионный тест: Проверка импорта пакета"""
    import cursor_subagent_mcp

    assert cursor_subagent_mcp is not None
    assert hasattr(cursor_subagent_mcp, "__version__")


def test_entry_point_available():
    """Регрессионный тест: Проверка доступности точки входа через server"""
    from cursor_subagent_mcp.server import main

    assert callable(main)


def test_init_file_content():
    """Проверка содержимого файла __init__.py"""
    init_file = Path(__file__).parent.parent / "src" / "cursor_subagent_mcp" / "__init__.py"

    assert init_file.exists(), "File __init__.py should exist"

    content = init_file.read_text(encoding="utf-8")

    # Проверяем наличие __version__
    assert "__version__" in content, "File should contain __version__"

    # Проверяем, что версия установлена
    assert '"0.1.0"' in content or "'0.1.0'" in content, "File should contain version 0.1.0"

    # Проверяем, что нет явных экспортов функций/классов (кроме __version__)
    # Разрешаем docstring, но не должно быть from ... import или def/class на верхнем уровне
    lines = [line.strip() for line in content.split("\n") if line.strip()]

    # Игнорируем docstring и пустые строки
    code_lines = [
        line
        for line in lines
        if not line.startswith('"""') and not line.startswith("'''") and line
    ]

    # Проверяем, что нет экспортов функций/классов (кроме __version__)
    has_function_def = any(line.startswith("def ") for line in code_lines)
    has_class_def = any(line.startswith("class ") for line in code_lines)
    has_from_import = any(
        line.startswith("from ") and "__version__" not in line
        for line in code_lines
    )

    # Разрешаем только __version__ = ...
    if has_function_def or has_class_def:
        pytest.fail("__init__.py should not contain function or class definitions")

    if has_from_import:
        pytest.fail("__init__.py should not contain from ... import (except __version__)")


def test_package_reload():
    """Проверка перезагрузки модуля"""
    import cursor_subagent_mcp

    # Перезагружаем модуль
    importlib.reload(cursor_subagent_mcp)

    # Проверяем, что версия всё ещё доступна
    assert cursor_subagent_mcp.__version__ == "0.1.0"
