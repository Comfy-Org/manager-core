import pytest
import subprocess
import sys
import os

sys.path.append(os.path.join(os.getcwd(), "glob"))
import manager_core

def test_call_cli_dependencies_success(mocker):
    """Test successful execution of call_cli_dependencies()."""
    mock_check_output = mocker.patch('subprocess.check_output')
    mock_check_output.return_value = "Mocked dependencies output"

    result, error_occurred = manager_core.call_cli_dependencies()

    assert result == "Mocked dependencies output"
    assert error_occurred is False
    mock_check_output.assert_called_once_with([sys.executable, '-m', 'comfy-cli', 'dependencies'], universal_newlines=True)


def test_call_cli_dependencies_failure(mocker):
    """Test failure case of call_cli_dependencies()."""
    mock_check_output = mocker.patch('subprocess.check_output')
    mock_check_output.side_effect = subprocess.CalledProcessError(1, 'cmd')

    from io import StringIO
    import sys
    captured_output = StringIO()
    sys.stdout = captured_output

    result, error_occurred = manager_core.call_cli_dependencies()

    sys.stdout = sys.__stdout__

    assert result is None
    assert error_occurred is True
    assert "[ComfyUI-Manager] Failed to execute the command 'comfy-cli dependencies'." in captured_output.getvalue()