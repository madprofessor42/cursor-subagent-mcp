"""Tests for executor installer functions."""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cursor_subagent_mcp.executor.installer import install_cursor_cli
from cursor_subagent_mcp.executor.models import ExecutionResult


class TestInstallCursorCli:
    """Tests for install_cursor_cli() function."""

    @pytest.mark.asyncio
    async def test_install_cursor_cli_success(self):
        """TC-UNIT-01: Проверка работы install_cursor_cli() при успешной установке."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(
            b"Installer detected: macOS\nCursor CLI installed successfully",
            b""
        ))

        with patch("asyncio.create_subprocess_shell", return_value=mock_process), \
             patch("os.path.exists") as mock_exists, \
             patch("builtins.open", create=True) as mock_open, \
             patch("os.path.expanduser", return_value="/home/test"), \
             patch("os.path.join", side_effect=lambda *args: "/".join(args)):
            
            # Mock shell config file exists and doesn't have .local/bin
            mock_exists.side_effect = lambda path: path == "/home/test/.zshrc" or path == "/home/test/.local/bin/cursor-agent"
            
            # Mock file reading
            mock_file = MagicMock()
            mock_file.read.return_value = "# Some config\n"
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock(return_value=None)
            mock_open.return_value = mock_file

            result = await install_cursor_cli()

            assert isinstance(result, ExecutionResult)
            assert result.success is True
            assert "Step 1" in result.output
            assert "Step 2" in result.output
            assert result.error is None
            assert result.return_code == 0

    @pytest.mark.asyncio
    async def test_install_cursor_cli_timeout(self):
        """TC-UNIT-02: Проверка обработки таймаута при установке."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("asyncio.create_subprocess_shell", return_value=mock_process):
            result = await install_cursor_cli()

            assert isinstance(result, ExecutionResult)
            assert result.success is False
            assert "Installation timed out after 120 seconds" in result.error
            assert result.return_code == -1

    @pytest.mark.asyncio
    async def test_install_cursor_cli_installation_failure(self):
        """Проверка обработки ошибки установки."""
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(
            b"Installer error",
            b"Failed to download"
        ))

        with patch("asyncio.create_subprocess_shell", return_value=mock_process):
            result = await install_cursor_cli()

            assert isinstance(result, ExecutionResult)
            assert result.success is False
            assert "Installation failed" in result.error
            assert result.return_code == 1

    @pytest.mark.asyncio
    async def test_install_cursor_cli_path_configuration(self):
        """TC-UNIT-03: Проверка настройки PATH в shell конфигурации."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(
            b" Cursor CLI installed successfully",
            b""
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            shell_config = os.path.join(tmpdir, ".zshrc")
            cursor_agent_path = os.path.join(tmpdir, ".local", "bin", "cursor-agent")
            
            # Create shell config file
            Path(shell_config).parent.mkdir(parents=True, exist_ok=True)
            with open(shell_config, "w") as f:
                f.write("# Original config\n")

            # Create cursor-agent binary
            Path(cursor_agent_path).parent.mkdir(parents=True, exist_ok=True)
            Path(cursor_agent_path).touch()

            def expanduser_side_effect(path):
                if path == "~":
                    return tmpdir
                if path == "~/.local/bin":
                    return os.path.join(tmpdir, ".local", "bin")
                return path.replace("~", tmpdir)

            def exists_side_effect(path):
                if path == shell_config:
                    return True
                if path == cursor_agent_path:
                    return True
                # Also check for paths that detect_shell might check
                if path == os.path.join(tmpdir, ".zshrc"):
                    return True
                if path == os.path.join(tmpdir, ".bashrc"):
                    return False
                return False

            with patch("asyncio.create_subprocess_shell", return_value=mock_process), \
                 patch("cursor_subagent_mcp.executor.shell.detect_shell", return_value="zsh"), \
                 patch("cursor_subagent_mcp.executor.shell.get_shell_config_file", return_value=shell_config), \
                 patch("os.path.expanduser", side_effect=expanduser_side_effect), \
                 patch("os.path.exists", side_effect=exists_side_effect), \
                 patch("asyncio.create_subprocess_exec") as mock_exec:
                
                # Mock login process
                login_process = AsyncMock()
                login_process.returncode = 0
                login_process.communicate = AsyncMock(return_value=(b"Login successful", b""))
                mock_exec.return_value = login_process

                result = await install_cursor_cli()

                # Check that PATH was added to shell config
                with open(shell_config, "r") as f:
                    content = f.read()
                    assert ".local/bin" in content
                    assert "Added by cursor-subagent-mcp installer" in content

                assert isinstance(result, ExecutionResult)
                assert result.success is True

    @pytest.mark.asyncio
    async def test_install_cursor_cli_path_already_configured(self):
        """Проверка обработки случая, когда PATH уже настроен."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(
            b" Cursor CLI installed successfully",
            b""
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            shell_config = os.path.join(tmpdir, ".zshrc")
            cursor_agent_path = os.path.join(tmpdir, ".local", "bin", "cursor-agent")
            
            # Create shell config file with PATH already configured
            Path(shell_config).parent.mkdir(parents=True, exist_ok=True)
            with open(shell_config, "w") as f:
                f.write("# Original config\n")
                f.write('export PATH="$HOME/.local/bin:$PATH"\n')

            # Create cursor-agent binary
            Path(cursor_agent_path).parent.mkdir(parents=True, exist_ok=True)
            Path(cursor_agent_path).touch()

            def expanduser_side_effect(path):
                if path == "~":
                    return tmpdir
                if path == "~/.local/bin":
                    return os.path.join(tmpdir, ".local", "bin")
                return path.replace("~", tmpdir)

            def exists_side_effect(path):
                if path == shell_config:
                    return True
                if path == cursor_agent_path:
                    return True
                # Also check for paths that detect_shell might check
                if path == os.path.join(tmpdir, ".zshrc"):
                    return True
                if path == os.path.join(tmpdir, ".bashrc"):
                    return False
                return False

            with patch("asyncio.create_subprocess_shell", return_value=mock_process), \
                 patch("cursor_subagent_mcp.executor.shell.detect_shell", return_value="zsh"), \
                 patch("cursor_subagent_mcp.executor.shell.get_shell_config_file", return_value=shell_config), \
                 patch("os.path.expanduser", side_effect=expanduser_side_effect), \
                 patch("os.path.exists", side_effect=exists_side_effect), \
                 patch("asyncio.create_subprocess_exec") as mock_exec:
                
                login_process = AsyncMock()
                login_process.returncode = 0
                login_process.communicate = AsyncMock(return_value=(b"Login successful", b""))
                mock_exec.return_value = login_process

                result = await install_cursor_cli()

                # Check that PATH was not added again
                with open(shell_config, "r") as f:
                    content = f.read()
                    # Count occurrences of .local/bin
                    assert content.count(".local/bin") == 1  # Only the original one

                assert isinstance(result, ExecutionResult)
                assert result.success is True
                assert "PATH already configured" in result.output

    @pytest.mark.asyncio
    async def test_install_cursor_cli_login_timeout(self):
        """Проверка обработки таймаута при логине."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(
            b" Cursor CLI installed successfully",
            b""
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            shell_config = os.path.join(tmpdir, ".zshrc")
            cursor_agent_path = os.path.join(tmpdir, ".local", "bin", "cursor-agent")
            
            Path(shell_config).parent.mkdir(parents=True, exist_ok=True)
            with open(shell_config, "w") as f:
                f.write("# Config\n")

            # Create cursor-agent binary
            Path(cursor_agent_path).parent.mkdir(parents=True, exist_ok=True)
            Path(cursor_agent_path).touch()

            def expanduser_side_effect(path):
                if path == "~":
                    return tmpdir
                if path == "~/.local/bin":
                    return os.path.join(tmpdir, ".local", "bin")
                return path.replace("~", tmpdir)

            def exists_side_effect(path):
                if path == shell_config:
                    return True
                if path == cursor_agent_path:
                    return True
                return False

            with patch("asyncio.create_subprocess_shell", return_value=mock_process), \
                 patch("cursor_subagent_mcp.executor.shell.get_shell_config_file", return_value=shell_config), \
                 patch("os.path.expanduser", side_effect=expanduser_side_effect), \
                 patch("os.path.exists", side_effect=exists_side_effect), \
                 patch("asyncio.create_subprocess_exec") as mock_exec:
                
                login_process = AsyncMock()
                login_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
                mock_exec.return_value = login_process

                result = await install_cursor_cli()

                assert isinstance(result, ExecutionResult)
                assert result.success is True  # Installation succeeded, only login timed out
                assert "Authentication timed out" in result.output or "timed out" in result.output.lower()

    @pytest.mark.asyncio
    async def test_install_cursor_cli_path_configuration_error(self):
        """Проверка обработки ошибки при настройке PATH."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(
            b" Cursor CLI installed successfully",
            b""
        ))

        with patch("asyncio.create_subprocess_shell", return_value=mock_process), \
             patch("cursor_subagent_mcp.executor.shell.get_shell_config_file", return_value="/nonexistent/.zshrc"), \
             patch("os.path.exists", return_value=False), \
             patch("builtins.open", side_effect=PermissionError("Permission denied")):
            
            result = await install_cursor_cli()

            assert isinstance(result, ExecutionResult)
            assert result.success is False
            assert "Failed to configure PATH" in result.error
            assert result.return_code == -1
