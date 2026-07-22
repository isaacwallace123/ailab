from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_sync_module():
    path = ROOT / "scripts" / "sync-openwebui-workspace.py"
    spec = importlib.util.spec_from_file_location("sync_openwebui_workspace", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tool_valves_use_top_level_payload() -> None:
    module = load_sync_module()

    class FakeAPI:
        def __init__(self):
            self.call = None

        def request(self, method, path, **kwargs):
            self.call = (method, path, kwargs)
            return kwargs["json"]

    api = FakeAPI()
    valves = {"api_base": "http://127.0.0.1:18089", "api_key": "secret"}
    module.update_tool_valves(api, "finance_search", valves)

    assert api.call == (
        "POST",
        "/api/v1/tools/id/finance_search/valves/update",
        {"json": valves},
    )
    assert "valves" not in api.call[2]["json"]


def test_shared_model_prompts_do_not_hardcode_a_user_identity() -> None:
    personalized_models = {
        "isaac-general",
        "lab-operator",
        "project-copilot",
        "dad-finance-guide",
    }
    for path in (ROOT / "cookbook" / "models").glob("*.json"):
        model = json.loads(path.read_text(encoding="utf-8"))
        system = model["params"]["system"]
        assert "Isaac" not in system
        if model["id"] in personalized_models:
            assert "{{USER_NAME}}" in system
