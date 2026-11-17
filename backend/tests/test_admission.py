from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import runpy
from threading import Event
from unittest.mock import Mock

import jwt
import pytest
from gunicorn.config import Config

from bedrock_chat.app import create_app


RESULT = {"text": "synthetic answer", "usage": {"input_tokens": 1, "output_tokens": 1}}


@pytest.fixture
def clock(monkeypatch):
    value = [0.0]
    monkeypatch.setattr("bedrock_chat.admission.monotonic", lambda: value[0])
    return value


def test_burst_refill_fractional_time_and_capacity(clock):
    model = Mock(return_value=RESULT)
    client = create_app(auth=Mock(), model_service=model, settings={}).test_client()
    def query():
        return client.post("/query", json={"prompt": "synthetic"})
    assert [query().status_code for _ in range(3)] == [200, 200, 429]
    clock[0] = .5
    assert query().status_code == 429
    clock[0] = 1
    assert query().status_code == 200
    clock[0] = 1.5
    assert query().status_code == 429
    clock[0] = 2
    assert query().status_code == 200
    clock[0] = 100
    assert [query().status_code for _ in range(3)] == [200, 200, 429]
    assert model.call_count == 6
    rejected = query()
    assert rejected.json == {"error": "Inference busy or rate limit reached; retry deliberately later"}
    assert rejected.headers["Cache-Control"] == "no-store"
    assert rejected.headers["Referrer-Policy"] == "no-referrer"


@pytest.mark.parametrize(("error", "status"), [(None, 200), (RuntimeError("private exception"), 502), (TimeoutError("private exception"), 504)])
def test_overlapping_queries_reject_without_queueing_or_consuming_burst_and_ready_stays_available(clock, error, status, caplog):
    entered, release = Event(), Event()
    def blocked_model(prompt, history):
        entered.set()
        assert release.wait(timeout=5), "test did not release model"
        if error is not None:
            raise error
        return RESULT
    model = Mock(side_effect=blocked_model)
    app = create_app(auth=Mock(), model_service=model, settings={})
    def query():
        with app.test_client() as client:
            return client.post("/query", json={"prompt": "private prompt"}, headers={"Authorization": "Bearer private"})
    with ThreadPoolExecutor(max_workers=4) as pool:
        first = pool.submit(query)
        try:
            assert entered.wait(timeout=3)
            rejected = pool.submit(query).result(timeout=2)
            assert rejected.status_code == 429
            assert "private" not in rejected.text
            ready = pool.submit(lambda: app.test_client().get("/ready")).result(timeout=2)
            assert ready.status_code == 200 and ready.text == "ready"
            assert model.call_count == 1
        finally:
            release.set()
        assert first.result(timeout=2).status_code == status
    model.side_effect = None; model.return_value = RESULT
    assert query().status_code == 200
    assert model.call_count == 2
    assert query().status_code == 429
    assert "private" not in caplog.text


def test_unauthorized_invalid_and_public_requests_do_not_consume_admission(clock):
    auth = Mock(side_effect=jwt.InvalidTokenError("private")); model = Mock(return_value=RESULT)
    client = create_app(auth=auth, model_service=model, settings={}).test_client()
    for _ in range(3):
        assert client.post("/query", json={"prompt": "ok"}).status_code == 401
    auth.side_effect = None
    for _ in range(3):
        assert client.post("/query", json={"prompt": ""}).status_code == 400
        assert client.post("/query", data="{", content_type="application/json").status_code == 400
        assert client.post("/query", data="bad").status_code == 415
        assert client.post("/query", data="x" * (256 * 1024 + 1), content_type="application/json").status_code == 413
        assert client.get("/ready").status_code == 200
        assert client.options("/query").status_code == 204
        assert client.get("/unknown").status_code == 404
    model.assert_not_called()
    assert [client.post("/query", json={"prompt": "ok"}).status_code for _ in range(3)] == [200, 200, 429]
    model.assert_called_with("ok", [])
    assert model.call_count == 2


def test_serialization_failure_releases_slot_but_consumes_accepted_request(clock):
    model = Mock(return_value={"text": object()})
    client = create_app(auth=Mock(), model_service=model, settings={}).test_client()
    assert client.post("/query", json={"prompt": "ok"}).status_code == 502
    model.return_value = RESULT
    assert client.post("/query", json={"prompt": "ok"}).status_code == 200
    assert client.post("/query", json={"prompt": "ok"}).status_code == 429
    assert model.call_count == 2


def test_app_recreation_resets_process_local_allowance(clock):
    model = Mock(return_value=RESULT)
    def make():
        return create_app(auth=Mock(), model_service=model, settings={}).test_client()
    first = make()
    assert [first.post("/query", json={"prompt": "ok"}).status_code for _ in range(3)] == [200, 200, 429]
    assert make().post("/query", json={"prompt": "ok"}).status_code == 200


def test_gunicorn_config_keeps_one_process_and_probe_threads():
    settings = runpy.run_path(str(Path("gunicorn.conf.py")))
    config = Config()
    for name in ("workers", "worker_class", "threads", "bind", "accesslog", "errorlog", "control_socket_disable", "worker_tmp_dir", "timeout", "loglevel"):
        config.set(name, settings[name])
    assert config.workers == 1
    assert config.threads == 4
    assert config.worker_class.__name__ == "ThreadWorker"
    assert config.bind == ["0.0.0.0:8000"]
    assert config.accesslog is None and config.errorlog == "-"
    assert config.control_socket_disable is True
    assert config.worker_tmp_dir == "/tmp" and config.timeout == 30
    assert config.loglevel == "warning"
