#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    cookbook = root / "cookbook"
    errors: list[str] = []

    skill_ids: set[str] = set()
    for path in sorted(cookbook.glob("skills/*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, flags=re.DOTALL)
        require(match is not None, f"{path}: missing YAML frontmatter", errors)
        if not match:
            continue
        frontmatter = yaml.safe_load(match.group(1))
        name = frontmatter.get("name") if isinstance(frontmatter, dict) else None
        description = frontmatter.get("description") if isinstance(frontmatter, dict) else None
        require(name == path.parent.name, f"{path}: name must match directory", errors)
        require(bool(description), f"{path}: description is required", errors)
        require("TODO" not in text, f"{path}: contains an unfinished TODO", errors)
        if name:
            require(name not in skill_ids, f"duplicate skill id: {name}", errors)
            skill_ids.add(name)

    tool_ids: set[str] = set()
    for path in sorted(cookbook.glob("tools/*.py")):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as error:
            errors.append(f"{path}: {error}")
        tool_ids.add(path.stem)

    manifest = yaml.safe_load((cookbook / "knowledge/manifest.yaml").read_text(encoding="utf-8"))
    knowledge_names: set[str] = set()
    require(manifest.get("version") == 1, "knowledge manifest must be version 1", errors)
    for collection in manifest.get("collections", []):
        name = collection.get("name")
        require(bool(name), "knowledge collection is missing a name", errors)
        require(name not in knowledge_names, f"duplicate knowledge collection: {name}", errors)
        knowledge_names.add(name)
        for relative in collection.get("files", []):
            require(
                (root / relative).is_file(), f"knowledge file does not exist: {relative}", errors
            )

    commands: set[str] = set()
    for path in sorted(cookbook.glob("prompts/*.json")):
        prompt = json.loads(path.read_text(encoding="utf-8"))
        command = prompt.get("command", "")
        require(command.startswith("/"), f"{path}: command must start with /", errors)
        require(command not in commands, f"duplicate prompt command: {command}", errors)
        require(bool(prompt.get("content")), f"{path}: content is required", errors)
        commands.add(command)

    model_ids: set[str] = set()
    for path in sorted(cookbook.glob("models/*.json")):
        model = json.loads(path.read_text(encoding="utf-8"))
        model_id = model.get("id")
        require(bool(model_id), f"{path}: id is required", errors)
        require(bool(model.get("base_model_id")), f"{path}: base_model_id is required", errors)
        require(model_id not in model_ids, f"duplicate model id: {model_id}", errors)
        model_ids.add(model_id)
        meta = model.get("meta", {})
        for skill_id in meta.get("skillIds", []):
            require(skill_id in skill_ids, f"{path}: unknown skill {skill_id}", errors)
        for tool_id in meta.get("toolIds", []):
            require(tool_id in tool_ids, f"{path}: unknown tool {tool_id}", errors)
        for knowledge_name in meta.get("knowledge_names", []):
            require(
                knowledge_name in knowledge_names,
                f"{path}: unknown knowledge collection {knowledge_name}",
                errors,
            )

    catalog = yaml.safe_load((cookbook / "catalog/models.yaml").read_text(encoding="utf-8"))
    require(catalog.get("version") == 1, "model catalog must be version 1", errors)
    catalog_ids: set[str] = set()
    workers = catalog.get("workers", {})
    for model in catalog.get("models", []):
        model_id = model.get("id")
        require(model_id not in catalog_ids, f"duplicate catalog model: {model_id}", errors)
        catalog_ids.add(model_id)
        require(
            model.get("status") in {"active", "candidate", "retired"},
            f"catalog model {model_id} has invalid status",
            errors,
        )
        preferred = model.get("preferred_worker")
        require(
            not preferred or preferred in workers,
            f"catalog model {model_id} has unknown worker",
            errors,
        )

    if errors:
        print("Cookbook validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Cookbook valid: "
        f"{len(model_ids)} workspace models, {len(knowledge_names)} knowledge packs, "
        f"{len(commands)} prompts, {len(skill_ids)} skills, and {len(tool_ids)} tools."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
