#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
from pathlib import Path

import httpx
import yaml


class OpenWebUI:
    def __init__(self, base_url: str, token: str, timeout: float = 120) -> None:
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
            follow_redirects=True,
        )

    def close(self) -> None:
        self.client.close()

    def request(self, method: str, path: str, **kwargs):
        response = self.client.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise RuntimeError(
                f"{method} {path} failed ({response.status_code}): {response.text[:2000]}"
            )
        return response.json() if response.content else None


def parse_skill(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Skill is missing YAML frontmatter: {path}")
    metadata = yaml.safe_load(match.group(1))
    return {
        "id": metadata["name"],
        "name": metadata["name"].replace("-", " ").title(),
        "description": metadata["description"],
        "content": match.group(2).strip(),
        "meta": {"tags": ["ai-lab-cookbook"]},
        "is_active": True,
        "access_grants": None,
    }


def sign_in(base_url: str, email: str, password: str) -> str:
    response = httpx.post(
        f"{base_url.rstrip('/')}/api/v1/auths/signin",
        json={"email": email, "password": password},
        timeout=30,
        follow_redirects=True,
    )
    response.raise_for_status()
    token = response.json().get("token")
    if not token:
        raise RuntimeError("Open WebUI sign-in did not return a token.")
    return token


def update_tool_valves(api: OpenWebUI, tool_id: str, valves: dict) -> None:
    """Persist global tool valves using Open WebUI's top-level valve payload."""
    saved = api.request(
        "POST",
        f"/api/v1/tools/id/{tool_id}/valves/update",
        json=valves,
    )
    if not isinstance(saved, dict) or any(saved.get(key) != value for key, value in valves.items()):
        raise RuntimeError(f"Open WebUI did not persist the expected valves for {tool_id}.")


def upsert_skills(api: OpenWebUI, root: Path) -> None:
    for path in sorted((root / "cookbook/skills").glob("*/SKILL.md")):
        payload = parse_skill(path)
        exists = api.client.get(f"/api/v1/skills/id/{payload['id']}").status_code == 200
        route = f"/api/v1/skills/id/{payload['id']}/update" if exists else "/api/v1/skills/create"
        api.request("POST", route, json=payload)
        print(f"{'Updated' if exists else 'Created'} skill: {payload['id']}")


def upsert_prompts(api: OpenWebUI, root: Path) -> None:
    existing = {item["command"]: item for item in api.request("GET", "/api/v1/prompts/")}
    for path in sorted((root / "cookbook/prompts").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["access_grants"] = payload.get("access_grants") or []
        current = existing.get(payload["command"])
        route = (
            f"/api/v1/prompts/id/{current['id']}/update" if current else "/api/v1/prompts/create"
        )
        api.request("POST", route, json=payload)
        print(f"{'Updated' if current else 'Created'} prompt: {payload['command']}")


def upsert_tools(api: OpenWebUI, root: Path, args: argparse.Namespace) -> None:
    for path in sorted((root / "cookbook/tools").glob("*.py")):
        tool_id = path.stem
        payload = {
            "id": tool_id,
            "name": tool_id.replace("_", " ").title(),
            "content": path.read_text(encoding="utf-8"),
            "meta": {"description": "Managed by the AI Lab cookbook."},
            "access_grants": [],
        }
        exists = api.client.get(f"/api/v1/tools/id/{tool_id}").status_code == 200
        route = f"/api/v1/tools/id/{tool_id}/update" if exists else "/api/v1/tools/create"
        api.request("POST", route, json=payload)
        print(f"{'Updated' if exists else 'Created'} tool: {tool_id}")

    if args.assistant_api_token:
        update_tool_valves(
            api,
            "lab_observer",
            {
                "api_base": args.assistant_api_base,
                "api_token": args.assistant_api_token,
                "timeout_seconds": 30,
            },
        )
        print("Configured Lab Observer read-only API valve.")
    else:
        print("Lab Observer installed but not configured: supply --assistant-api-token.")

    if args.research_gateway_api_key:
        for tool_id in ("research_gateway", "finance_search"):
            update_tool_valves(
                api,
                tool_id,
                {
                    "api_base": args.research_gateway_api_base,
                    "api_key": args.research_gateway_api_key,
                    "timeout_seconds": 180,
                },
            )
        print("Configured the loopback-only Research Gateway and Finance Search valves.")
    else:
        print("Research Gateway installed but not configured: supply its API key.")

    if args.github_repositories:
        valves = {
            "allowed_repositories": args.github_repositories,
            "timeout_seconds": 20,
        }
        if args.github_token:
            valves["github_token"] = args.github_token
        update_tool_valves(api, "github_reader", valves)
        print("Configured GitHub Reader allowlist.")
    else:
        print("GitHub Reader installed deny-all: supply --github-repositories to enable it.")

    if args.alpaca_api_key_id and args.alpaca_api_secret_key:
        update_tool_valves(
            api,
            "market_data",
            {
                "alpaca_api_key_id": args.alpaca_api_key_id,
                "alpaca_api_secret_key": args.alpaca_api_secret_key,
                "default_feed": args.alpaca_default_feed,
                "timeout_seconds": 20,
            },
        )
        print(f"Configured Market Data with the {args.alpaca_default_feed} feed.")
    else:
        print("Market Data installed but disabled: supply both Alpaca credentials.")

    official_valves = {"timeout_seconds": 25}
    if args.sec_contact_email:
        official_valves["sec_contact_email"] = args.sec_contact_email
    update_tool_valves(api, "official_finance_data", official_valves)
    if args.sec_contact_email:
        print("Configured SEC access with the operator contact email.")
    else:
        print("Bank of Canada enabled; SEC calls require --sec-contact-email.")


def upsert_knowledge(api: OpenWebUI, root: Path) -> dict[str, dict]:
    manifest = yaml.safe_load(
        (root / "cookbook/knowledge/manifest.yaml").read_text(encoding="utf-8")
    )
    response = api.request("GET", "/api/v1/knowledge/")
    existing = {item["name"]: item for item in response.get("items", [])}
    result = dict(existing)
    for definition in manifest["collections"]:
        current = existing.get(definition["name"])
        payload = {
            "name": definition["name"],
            "description": definition["description"],
            "access_grants": None,
        }
        if current:
            collection = api.request(
                "POST", f"/api/v1/knowledge/{current['id']}/update", json=payload
            )
            print(f"Updated knowledge: {definition['name']}")
        else:
            collection = api.request("POST", "/api/v1/knowledge/create", json=payload)
            print(f"Created knowledge: {definition['name']}")
        result[definition["name"]] = collection
        files_response = api.request("GET", f"/api/v1/knowledge/{collection['id']}/files?limit=200")
        remote_files = {item["filename"]: item for item in files_response.get("items", [])}
        for relative in definition["files"]:
            local_path = root / relative
            content = local_path.read_text(encoding="utf-8")
            filename = local_path.name
            remote = remote_files.get(filename)
            if remote:
                existing_content = api.request(
                    "GET", f"/api/v1/files/{remote['id']}/data/content"
                ).get("content", "")
                if existing_content != content:
                    api.request(
                        "POST",
                        f"/api/v1/files/{remote['id']}/data/content/update",
                        json={"content": content},
                    )
                    print(f"  Updated file: {filename}")
                else:
                    print(f"  Unchanged file: {filename}")
            else:
                with local_path.open("rb") as handle:
                    api.request(
                        "POST",
                        "/api/v1/files/?process=true&process_in_background=false",
                        files={"file": (filename, handle, "text/markdown")},
                        data={"metadata": json.dumps({"knowledge_id": collection["id"]})},
                    )
                print(f"  Uploaded file: {filename}")
    return result


def upsert_models(api: OpenWebUI, root: Path, knowledge: dict[str, dict]) -> None:
    available = {item["id"] for item in api.request("GET", "/api/models").get("data", [])}
    for path in sorted((root / "cookbook/models").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["access_grants"] = payload.get("access_grants") or []
        if payload["base_model_id"] not in available:
            raise RuntimeError(
                f"Base model {payload['base_model_id']} for {payload['id']} is not available."
            )
        names = payload["meta"].pop("knowledge_names", [])
        if names:
            payload["meta"]["knowledge"] = [
                {"id": knowledge[name]["id"], "name": name, "type": "collection"} for name in names
            ]
        exists = (
            api.client.get("/api/v1/models/model", params={"id": payload["id"]}).status_code == 200
        )
        route = "/api/v1/models/model/update" if exists else "/api/v1/models/create"
        api.request("POST", route, json=payload)
        print(f"{'Updated' if exists else 'Created'} model: {payload['name']}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Idempotently sync the AI Lab cookbook into Open WebUI."
    )
    parser.add_argument("--url", default=os.getenv("OPENWEBUI_URL", "http://192.168.0.221:8080"))
    parser.add_argument("--email", default=os.getenv("OPENWEBUI_EMAIL", "isaac@ailab.local"))
    parser.add_argument("--password", default=os.getenv("OPENWEBUI_PASSWORD"))
    parser.add_argument("--password-file", type=Path)
    parser.add_argument("--assistant-api-base", default="http://127.0.0.1:18088")
    parser.add_argument("--assistant-api-token", default=os.getenv("AILAB_API_TOKEN"))
    parser.add_argument("--research-gateway-api-base", default="http://127.0.0.1:18089")
    parser.add_argument(
        "--research-gateway-api-key", default=os.getenv("RESEARCH_GATEWAY_API_KEY")
    )
    parser.add_argument("--github-token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--github-repositories", default=os.getenv("AILAB_GITHUB_REPOSITORIES", ""))
    parser.add_argument("--alpaca-api-key-id", default=os.getenv("ALPACA_API_KEY_ID", ""))
    parser.add_argument("--alpaca-api-secret-key", default=os.getenv("ALPACA_API_SECRET_KEY", ""))
    parser.add_argument(
        "--alpaca-default-feed",
        choices=("iex", "sip", "delayed_sip"),
        default=os.getenv("ALPACA_DEFAULT_FEED", "iex"),
    )
    parser.add_argument("--sec-contact-email", default=os.getenv("SEC_CONTACT_EMAIL", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        counts = {
            "models": len(list((root / "cookbook/models").glob("*.json"))),
            "knowledge": len(
                yaml.safe_load((root / "cookbook/knowledge/manifest.yaml").read_text())[
                    "collections"
                ]
            ),
            "prompts": len(list((root / "cookbook/prompts").glob("*.json"))),
            "skills": len(list((root / "cookbook/skills").glob("*/SKILL.md"))),
            "tools": len(list((root / "cookbook/tools").glob("*.py"))),
        }
        print(json.dumps({"url": args.url, "planned": counts}, indent=2))
        return 0

    password = args.password
    if args.password_file:
        password = args.password_file.read_text(encoding="utf-8").strip()
    if not password:
        password = getpass.getpass(f"Open WebUI password for {args.email}: ")
    token = sign_in(args.url, args.email, password)
    api = OpenWebUI(args.url, token)
    try:
        upsert_skills(api, root)
        upsert_prompts(api, root)
        upsert_tools(api, root, args)
        knowledge = upsert_knowledge(api, root)
        upsert_models(api, root, knowledge)
    finally:
        api.close()
    print("Open WebUI cookbook sync complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
