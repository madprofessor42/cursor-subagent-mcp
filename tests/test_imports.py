"""Tests for checking import dependencies and circular imports."""

import re
from pathlib import Path


def check_file_imports(file_path: Path, package_root: Path) -> list[str]:
    """Check imports in a file and return local imports.
    
    Args:
        file_path: Path to the Python file.
        package_root: Path to the package root.
        
    Returns:
        List of local import module names.
    """
    local_imports = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Match relative imports: from ..module import ...
        relative_pattern = r"from\s+(\.+)(\w+(?:\.\w+)*)\s+import"
        for match in re.finditer(relative_pattern, content):
            dots = match.group(1)
            module = match.group(2)
            local_imports.append((dots, module))
        
        # Match absolute imports: from cursor_subagent_mcp.module import ...
        absolute_pattern = r"from\s+cursor_subagent_mcp\.(\w+(?:\.\w+)*)\s+import"
        for match in re.finditer(absolute_pattern, content):
            module = match.group(1)
            local_imports.append(("", module))
        
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return local_imports


def resolve_import(dots: str, module: str, current_file: Path, package_root: Path) -> str:
    """Resolve a relative import to a module path.
    
    Args:
        dots: The dots from the import (e.g., "..").
        module: The module name.
        current_file: Path to the current file.
        package_root: Path to the package root.
        
    Returns:
        Resolved module path relative to package root.
    """
    if dots:
        # Relative import
        rel_path = current_file.relative_to(package_root)
        parts = list(rel_path.parts[:-1])  # Remove filename
        
        # Go up (len(dots) - 1) levels
        levels_up = len(dots) - 1
        if levels_up > 0:
            parts = parts[:-levels_up]
        
        # Add module parts
        if module:
            parts.extend(module.split("."))
        
        return "/".join(parts)
    else:
        # Absolute import
        return module.replace(".", "/")


def test_config_no_executor_or_tools_imports():
    """Test that config.py does not import executor/ or tools/."""
    package_root = Path(__file__).parent.parent / "src" / "cursor_subagent_mcp"
    config_file = package_root / "config.py"
    
    assert config_file.exists(), "config.py should exist"
    
    imports = check_file_imports(config_file, package_root)
    
    violations = []
    for dots, module in imports:
        resolved = resolve_import(dots, module, config_file, package_root)
        if "executor" in resolved:
            violations.append(f"config.py imports executor module: {resolved}")
        if "tools" in resolved:
            violations.append(f"config.py imports tools module: {resolved}")
    
    assert not violations, "config.py should not import executor/ or tools/:\n" + "\n".join(violations)


def test_executor_no_tools_or_server_imports():
    """Test that executor/ modules do not import tools/ or server.py."""
    package_root = Path(__file__).parent.parent / "src" / "cursor_subagent_mcp"
    executor_dir = package_root / "executor"
    
    if not executor_dir.exists():
        return  # Skip if executor doesn't exist
    
    violations = []
    
    for py_file in executor_dir.rglob("*.py"):
        if py_file.name == "__pycache__":
            continue
        
        imports = check_file_imports(py_file, package_root)
        
        for dots, module in imports:
            resolved = resolve_import(dots, module, py_file, package_root)
            rel_path = py_file.relative_to(package_root)
            
            if "tools" in resolved:
                violations.append(f"{rel_path} imports tools module: {resolved}")
            if resolved == "server" or resolved.endswith("/server"):
                violations.append(f"{rel_path} imports server.py: {resolved}")
    
    assert not violations, "executor/ modules should not import tools/ or server.py:\n" + "\n".join(violations)


def test_no_circular_imports_basic():
    """Basic test for circular imports by checking import structure."""
    package_root = Path(__file__).parent.parent / "src" / "cursor_subagent_mcp"
    
    # Build dependency graph
    graph = {}
    
    # Process all Python files
    for py_file in package_root.rglob("*.py"):
        if py_file.name == "__pycache__":
            continue
        
        rel_path = str(py_file.relative_to(package_root).with_suffix("")).replace("\\", "/")
        imports = check_file_imports(py_file, package_root)
        
        dependencies = set()
        for dots, module in imports:
            resolved = resolve_import(dots, module, py_file, package_root)
            # Only track local dependencies
            if resolved and (resolved.startswith("executor/") or 
                           resolved.startswith("tools/") or 
                           resolved == "config" or
                           resolved == "server"):
                dependencies.add(resolved)
        
        graph[rel_path] = dependencies
    
    # Check for simple cycles (A -> B -> A)
    cycles = []
    for module, deps in graph.items():
        for dep in deps:
            if dep in graph and module in graph.get(dep, set()):
                cycles.append(f"{module} <-> {dep}")
    
    assert not cycles, f"Found circular dependencies:\n" + "\n".join(cycles)


def test_import_structure():
    """Test that import structure follows architectural rules."""
    package_root = Path(__file__).parent.parent / "src" / "cursor_subagent_mcp"
    
    # Check that config.py exists
    config_file = package_root / "config.py"
    assert config_file.exists(), "config.py should exist"
    
    # Check that executor/logging.py imports config (this is allowed)
    logging_file = package_root / "executor" / "logging.py"
    if logging_file.exists():
        imports = check_file_imports(logging_file, package_root)
        has_config_import = any(
            "config" in resolve_import(dots, module, logging_file, package_root)
            for dots, module in imports
        )
        assert has_config_import, "executor/logging.py should import config.find_config_file"
    
    # Check that tools modules import config and executor (this is allowed)
    tools_dir = package_root / "tools"
    if tools_dir.exists():
        for py_file in tools_dir.rglob("*.py"):
            if py_file.name == "__pycache__" or py_file.name == "__init__.py":
                continue
            
            imports = check_file_imports(py_file, package_root)
            resolved_imports = {
                resolve_import(dots, module, py_file, package_root)
                for dots, module in imports
            }
            
            # Tools should be able to import config and executor
            # This is just a structural check, not a violation check
            rel_path = py_file.relative_to(package_root)
            # No assertions here - tools can import anything except server
