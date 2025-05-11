import subprocess
import sys
import tempfile
import os
import time
import pytest

@pytest.mark.integration
def test_llm_agent_stop_chat_exits(tmp_path):
    # Prepare a temp DB path
    db_path = tmp_path / "test_products.db"
    env = os.environ.copy()
    env["PRODUCTS_DB"] = str(db_path)

    # Prepare the input sequence: select LLM agent, then immediately say 'stop chat'
    user_inputs = "3\nstop chat\n"

    # Run the main.py script as a subprocess
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd(),
        env=env,
        text=True,
    )
    try:
        # Send the input and get output
        out, err = proc.communicate(input=user_inputs, timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        pytest.fail("Process did not exit in time")

    # Print output for debugging if the exit code is not 0
    if proc.returncode != 0:
        print("STDOUT:\n", out)
        print("STDERR:\n", err)
    # Check exit code
    assert proc.returncode == 0
    # Check for the shutdown message
    assert "Conversation ended by LLM via stop_chat tool." in out 