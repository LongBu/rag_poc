"""Build the application ZIP inside the matching Lambda Linux image."""
import platform
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

import cryptography
import numpy
import pydantic_core
from bedrock_chat.app import create_app

assert sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 14)
assert platform.system() == "Linux" and platform.machine() == "x86_64"
assert not create_app(settings={}).debug
target = Path("/out/lambda.zip")
with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
    for path in sorted(Path("/var/task").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            archive.write(path, path.relative_to("/var/task"))
with ZipFile(target) as archive:
    assert archive.testzip() is None
    assert {"run.sh", "bedrock_chat/app.py"} <= set(archive.namelist())
    assert archive.getinfo("run.sh").external_attr >> 16 & 0o111
    size = sum(item.file_size for item in archive.infolist())
    assert size + Path("/opt/extensions/lambda-adapter").stat().st_size < 250 * 1024**2
print(f"ZIP: {target.stat().st_size} bytes; expanded application: {size} bytes")
print("Direct ZIP upload" if target.stat().st_size <= 50 * 1024**2 else "S3 artifact upload required")
