import json
import os
from pathlib import Path
import runpy
import subprocess
from unittest.mock import Mock

from azure.identity import CredentialUnavailableError
import pytest
from langchain_core.messages import AIMessage

from bedrock_chat import cli, model
from test_model import SETTINGS


@pytest.mark.parametrize("probe",[False,True])
@pytest.mark.parametrize("error",[None, CredentialUnavailableError("secret"),model.ModelResponseError("secret"), RuntimeError("secret")])
def test_sdk(monkeypatch,capsys,probe,error):
    monkeypatch.setattr("sys.argv",["query","--tenant",SETTINGS["AZURE_TENANT_ID"],*(["--probe"] if probe else ["question"])])
    factory=Mock();factory.return_value.invoke.return_value=AIMessage(content="answer",usage_metadata={"input_tokens":10,"output_tokens":2,"total_tokens":12})
    factory.side_effect=error
    monkeypatch.setattr(cli,"create_model",factory)
    assert cli.main()==(1 if error else 0)
    output=capsys.readouterr();assert "secret" not in output.err
    if error:assert "No retry was made" in output.err
    else:
        assert json.loads(output.out)=={"text":"answer","usage":{"input_tokens":10,"output_tokens":2}}
        assert factory.return_value.invoke.call_args.args[0][-1].content==("Hello" if probe else "question")
    assert factory.call_args.kwargs["completion_tokens"]==(32 if probe else 512)
    assert factory.call_args.args[0]["AZURE_AUTH_MODE"]=="azure_cli"
    assert factory.call_args.args[0]["AZURE_TENANT_ID"]==SETTINGS["AZURE_TENANT_ID"]


@pytest.mark.parametrize("args",[[],[" "],["x"*4001],["--probe","custom"]])
def test_invalid_sdk_prompt(monkeypatch,args):
    monkeypatch.setattr("sys.argv",["query","--tenant",SETTINGS["AZURE_TENANT_ID"],*args])
    with pytest.raises(SystemExit) as error:cli.main()
    assert error.value.code==2


def test_module_entry(monkeypatch):
    monkeypatch.setattr("sys.argv",["query","--tenant",SETTINGS["AZURE_TENANT_ID"],"question"])
    monkeypatch.setattr(model,"create_model",Mock(side_effect=CredentialUnavailableError("secret")))
    with pytest.raises(SystemExit) as error:runpy.run_module("bedrock_chat.cli",run_name="__main__")
    assert error.value.code==1


@pytest.mark.parametrize("status",[0,1])
def test_shell_example(tmp_path,status):
    stub=tmp_path/"python"
    stub.write_text('''#!/bin/sh
[ "$1" = '-m' ] && [ "$2" = 'bedrock_chat.cli' ] && [ "$3" = '--tenant' ] && [ "$4" = 'tenant' ] && [ "$5" = '--probe' ] || exit 9
printf 'stubbed invocation\\n'
exit "$STUB_STATUS"
''');stub.chmod(0o755)
    env={**os.environ,"PYTHON":str(stub),"AZURE_TENANT_ID":"tenant","STUB_STATUS":str(status)}
    script=Path("examples/query.sh");subprocess.run(["sh","-n",str(script)],check=True)
    result=subprocess.run(["sh",str(script),"--probe"],env=env,capture_output=True,text=True)
    assert result.returncode==status and result.stdout.strip()=="stubbed invocation"
    env.pop("AZURE_TENANT_ID")
    assert subprocess.run(["sh",str(script)],env=env,capture_output=True).returncode!=0
