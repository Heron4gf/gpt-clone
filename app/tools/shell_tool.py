# app/tools/shell_tool.py
import subprocess
from typing import Optional
from agents import function_tool

@function_tool
def execute_shell_command(command: str, timeout: Optional[int] = 10) -> str:
    """
    Execute a shell command and return its output.
    
    Args:
        command: The shell command to execute.
        timeout: Maximum execution time in seconds (default: 10).
        
    Returns:
        Output from the command execution.
    """
    try:
        # Set up safe execution environment
        process = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if process.returncode != 0:
            return f"Error (exit code {process.returncode}):\n{process.stderr}"
        
        return process.stdout or "[Command executed successfully with no output]"
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"
