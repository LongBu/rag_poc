"""Review all exported image layers and metadata before public distribution."""
import json
from pathlib import PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile

SECRET = re.compile(
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----\s+[A-Za-z0-9+/=\r\n]{64,}|"
    rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[A-Z0-9]{16})\b|"
    rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}\b"
)
PRIVATE = re.compile(
    r"(?:^|/)(?:\.aws|\.azure|\.git|\.env(?:\.[^/]*)?|terraform\.tfstate[^/]*|"
    r"[^/]+\.(?:tfvars(?:\.json)?|tfplan(?:\.[^/]*)?|tfstate(?:\.[^/]*)?))(?:/|$)"
)


def check(path, data):
    assert not PRIVATE.search(path), "Private file in image layer"
    assert not SECRET.search(data), f"Credential marker in image content: {path}"
    # Application additions are allowlisted in every layer, including deleted files.
    if path.startswith("app/"):
        assert (
            path == "app/gunicorn.conf.py"
            or re.fullmatch(r"app/bedrock_chat/[a-z_]+\.py", path)
            or path == "app/bedrock_chat/static/index.html"
            or re.fullmatch(r"app/bedrock_chat/static/assets/[A-Za-z0-9_-]+\.(?:js|css)", path)
        ), "Unexpected application artifact in image layer"


def review(image):
    config = json.loads(subprocess.check_output(["docker", "image", "inspect", image]))[0]
    assert config["Architecture"] == "amd64" and config["Os"] == "linux"
    assert config["Config"]["User"] == "10001:10001"
    metadata = json.dumps(config).encode() + subprocess.check_output(
        ["docker", "history", "--no-trunc", "--format", "{{json .}}", image]
    )
    assert not SECRET.search(metadata), "Credential marker in image metadata/history"
    expected_env = {"PATH", "HOME", "TMPDIR", "PYTHONDONTWRITEBYTECODE", "PYTHONUNBUFFERED",
                    "LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2", "LANG", "GPG_KEY",
                    "PYTHON_VERSION", "PYTHON_SHA256"}
    assert all(e.partition("=")[0] in expected_env for e in config["Config"]["Env"]), "Unexpected image environment"
    layers = files = 0
    with tempfile.TemporaryFile() as exported:
        subprocess.run(["docker", "image", "save", image], stdout=exported, check=True)
        exported.seek(0)
        with tarfile.open(fileobj=exported) as archive:
            manifest = json.load(archive.extractfile("manifest.json"))
            assert len(manifest) == 1
            for layer in manifest[0]["Layers"]:
                layers += 1
                with tarfile.open(fileobj=archive.extractfile(layer), mode="r|*") as contents:
                    for member in contents:
                        path = str(PurePosixPath(member.name)).removeprefix("/")
                        assert not PRIVATE.search(path), "Private path in image layer"
                        if member.isfile():
                            files += 1
                            check(path, contents.extractfile(member).read())
                        elif member.issym() or member.islnk():
                            assert not PRIVATE.search(member.linkname), "Private link in image layer"
    print(f"Reviewed {layers} layers and {files} files plus config/history: {config['Id']}")


def self_check():
    check("app/bedrock_chat/app.py", b"public code")
    check("opt/venv/lib/azure/identity/_credentials/managed_identity.py", b"library")
    check("opt/venv/serialization.py", b'HEADER = b"-----BEGIN PRIVATE KEY-----"')
    for path, data in [("app/private.log", b""), ("root/.azure/cache", b""),
                       ("terraform.tfstate.backup", b""), ("private.tfvars", b""),
                       ("app/bedrock_chat/app.py", b"-----BEGIN PRIVATE KEY-----\n" + b"A" * 64)]:
        try:
            check(path, data)
        except AssertionError:
            continue
        raise AssertionError("Review accepted a forbidden fixture")
    print("Image review self-check passed")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_check()
    else:
        review(sys.argv[1] if len(sys.argv) > 1 else "private-azure-chat:local")
