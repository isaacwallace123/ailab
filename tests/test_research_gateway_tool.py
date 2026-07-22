import importlib.util
import json
from pathlib import Path
from urllib.error import URLError

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_tool():
    path = ROOT / "cookbook" / "tools" / "research_gateway.py"
    spec = importlib.util.spec_from_file_location("cookbook_tool_research_gateway", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_tool_requires_loopback_gateway() -> None:
    tool = load_tool().Tools()
    tool.valves.api_key = "test-key"
    tool.valves.api_base = "https://attacker.example"
    with pytest.raises(ValueError, match="loopback"):
        tool.fetch_public_page("https://example.com/")


def test_tool_sends_only_url_to_gateway(monkeypatch) -> None:
    module = load_tool()
    tool = module.Tools()
    tool.valves.api_key = "test-key"

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"final_url":"https://example.com/","text":"Example Domain"}'

    def fake_urlopen(request, timeout):
        assert request.full_url == "http://127.0.0.1:18089/v1/fetch"
        assert request.headers["X-api-key"] == "test-key"
        assert json.loads(request.data) == {"url": "https://example.com/"}
        assert timeout == 180
        return Response()

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    result = json.loads(tool.fetch_public_page("https://example.com/"))
    assert result["text"] == "Example Domain"


def test_tool_hides_transport_details(monkeypatch) -> None:
    module = load_tool()
    tool = module.Tools()
    tool.valves.api_key = "test-key"
    monkeypatch.setattr(
        module,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("secret host detail")),
    )
    with pytest.raises(RuntimeError, match="unavailable"):
        tool.extract_public_document("https://example.com/report.pdf")
