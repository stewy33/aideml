"""
Python interpreter for executing code snippets and capturing their output.
Supports:
- captures stdout and stderr
- captures exceptions and stack traces
- limits execution time
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import humanize
from dataclasses_json import DataClassJsonMixin

logger = logging.getLogger("aide")


@dataclass
class ExecutionResult(DataClassJsonMixin):
    """
    Result of executing a code snippet in the interpreter.
    Contains the output, execution time, and exception information.
    """

    term_out: list[str]
    exec_time: float
    exc_type: str | None
    exc_info: dict | None = None
    exc_stack: list[tuple] | None = None


class Interpreter:
    def __init__(
        self,
        working_dir: Path | str,
        timeout: int = 3600,
        format_tb_ipython: bool = False,
        agent_file_name: str = "runfile.py",
        sandbox=None,
    ):
        """
        Simulates a standalone Python REPL with an execution time limit.

        Args:
            working_dir (Path | str): working directory of the agent
            timeout (int, optional): Timeout for each code execution step. Defaults to 3600.
            format_tb_ipython (bool, optional): Whether to use IPython or default python REPL formatting for exceptions. Defaults to False.
            agent_file_name (str, optional): The name for the agent's code file. Defaults to "runfile.py".
            sandbox: Sandbox instance for executing code in container. If None, uses local execution.
        """
        self.working_dir = working_dir #Path(working_dir).resolve()
        # assert self.working_dir.exists(), f"Working directory {self.working_dir} does not exist"
        self.timeout = timeout
        self.format_tb_ipython = format_tb_ipython
        self.agent_file_name = agent_file_name
        self.sandbox = sandbox

    async def run(self, code: str, reset_session=True) -> ExecutionResult:
        """
        Execute the provided Python command in sandbox.
        
        Parameters:
            code (str): Python code to execute.
            reset_session (bool, optional): Whether to reset the interpreter session before executing the code. Defaults to True.
                Note: This parameter is kept for API compatibility but has no effect when using sandbox execution.

        Returns:
            ExecutionResult: Object containing the output and metadata of the code execution.
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox is required for execution")
            
        start_time = time.time()
        try:
            result = await self.sandbox.exec(
                cmd=["python3"],
                input=code,
                timeout=self.timeout,
                cwd=str(self.working_dir)
            )
            exec_time = time.time() - start_time
            
            output = []
            if result.stderr:
                output.append(result.stderr)
            if result.stdout:
                output.append(result.stdout)
                
            # Add execution time info
            output.append(
                f"Execution time: {humanize.naturaldelta(exec_time)} seconds "
                f"(time limit is {humanize.naturaldelta(self.timeout)})."
            )
            
            return ExecutionResult(
                term_out=output,
                exec_time=exec_time,
                exc_type=None if result.returncode == 0 else "RuntimeError",
                exc_info={"returncode": result.returncode} if result.returncode != 0 else None,
                exc_stack=None
            )
            
        except Exception as e:
            exec_time = time.time() - start_time
            return ExecutionResult(
                term_out=[str(e)],
                exec_time=exec_time,
                exc_type=e.__class__.__name__,
                exc_info={"error": str(e)},
                exc_stack=None
            )
