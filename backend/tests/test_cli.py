import json
import os
from pathlib import Path
import runpy
import subprocess
from unittest.mock import Mock

from botocore.exceptions import ClientError, NoCredentialsError
import pytest

from bedrock_chat import cli


@pytest.mark.parametrize("error", [None, NoCredentialsError(),
    ClientError({"Error": {"Code": "AccessDeniedException", "Message": "secret"}}, "Converse")])
def test_sdk(monkeypatch, capsys, error):
    monkeypatch.setattr("sys.argv", ["query", "--profile", "temporary", "question"])
    session = Mock()
    session.return_value.client.return_value.converse.return_value = {
        "output": {"message": {"content": [{"text": "answer"}, {"text": " text"}]}},
        "usage": {"inputTokens": 10, "outputTokens": 2},
    }
    session.return_value.client.return_value.converse.side_effect = error
    monkeypatch.setattr(cli.boto3, "Session", session)
    assert cli.main() == (1 if error else 0)
    output = capsys.readouterr()
    assert "secret" not in output.err
    if error:
        assert "check temporary profile" in output.err
    else:
        assert json.loads(output.out)["text"] == "answer text"
    session.assert_called_once_with(profile_name="temporary")
    call = session.return_value.client.return_value.converse.call_args.kwargs
    assert call["inferenceConfig"] == {"maxTokens": 512}
    assert call["modelId"] == "amazon.nova-micro-v1:0"


@pytest.mark.parametrize("prompt", [" ", "x"*4001])
def test_invalid_sdk_prompt(monkeypatch, prompt):
    monkeypatch.setattr("sys.argv", ["query", "--profile", "temporary", prompt])
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2


def test_module_entry(monkeypatch):
    monkeypatch.setattr("sys.argv", ["query", "--profile", "temporary", "question"])
    monkeypatch.setattr(cli.boto3, "Session", Mock(side_effect=NoCredentialsError()))
    with pytest.raises(SystemExit) as error:
        runpy.run_module("bedrock_chat.cli", run_name="__main__")
    assert error.value.code == 1


@pytest.mark.parametrize("status", [0, 1])
def test_shell_example(tmp_path, status):
    stub = tmp_path / "aws"
    stub.write_text('''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
assert args[:2] == ['bedrock-runtime', 'converse']
assert args[args.index('--profile')+1] == 'temporary'
assert args[args.index('--region')+1] == 'us-east-1'
assert json.loads(args[args.index('--inference-config')+1]) == {'maxTokens':512}
assert json.loads(args[args.index('--messages')+1])[0]['role'] == 'user'
print('stubbed invocation')
sys.exit(int(os.environ['STUB_STATUS']))
''')
    stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
           "AWS_PROFILE": "temporary", "STUB_STATUS": str(status)}
    script = Path("examples/query.sh")
    subprocess.run(["sh", "-n", str(script)], check=True)
    result = subprocess.run(["sh", str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == status
    assert result.stdout.strip() == "stubbed invocation"
