#!/usr/bin/env python3
# Superworkflows - persistent robotics AI Coding Loop Engineering.
# Copyright (c) 2026 Tsung Xu
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# Dual-licensed: AGPL-3.0-only OR a separate commercial license.

"""Side-effect-free activation assessment for the Superworkflows router."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY = PLUGIN_ROOT / "assets" / "loop-engineering" / "trigger-policy.json"
EXPLICIT_RE = re.compile(r"(?<![\w-])\$(superworkflows|init|status|run|review|release|learn)\b", re.IGNORECASE)
CHILD_ROUTES = {"init", "status", "run", "review", "release", "learn"}


class TriggerError(RuntimeError):
    pass


def load_policy(path: Path) -> dict[str, Any]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TriggerError(f"missing trigger policy: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TriggerError(f"invalid trigger policy JSON: {exc}") from exc
    if policy.get("schema_version") != 1:
        raise TriggerError("unsupported trigger policy schema")
    for field in (
        "policy_version",
        "implicit_persistence",
        "thresholds",
        "weights",
        "signals",
        "external_patterns",
        "routes",
    ):
        if field not in policy:
            raise TriggerError(f"trigger policy is missing: {field}")
    if policy["implicit_persistence"] != "forbidden":
        raise TriggerError("implicit persistence policy must be forbidden")
    for item in policy["external_patterns"]:
        if not isinstance(item, dict) or not item.get("name") or not item.get("regex"):
            raise TriggerError("invalid external pattern")
        try:
            re.compile(item["regex"], re.IGNORECASE)
        except re.error as exc:
            raise TriggerError(f"invalid external pattern {item.get('name')}: {exc}") from exc
    return policy


def normalize(prompt: str) -> str:
    return " ".join(prompt.casefold().split())


def strip_negated_actions(text: str, actions: list[str]) -> str:
    for phrase in (
        "do not modify", "don't modify", "without changing", "without modifying",
        "不要修改", "不修改", "无需修改", "只读分析",
    ):
        text = text.replace(phrase, " ")
    english = [action for action in actions if re.fullmatch(r"[a-z -]+", action)]
    if english:
        forms: set[str] = set()
        for action in english:
            forms.add(action)
            if action.endswith("ie"):
                forms.add(action[:-2] + "ying")
            elif action.endswith("e"):
                forms.add(action[:-1] + "ing")
            elif action.endswith("y"):
                forms.add(action[:-1] + "ying")
            else:
                forms.add(action + "ing")
        alternatives = "|".join(re.escape(action) for action in sorted(forms, key=len, reverse=True))
        text = re.sub(
            rf"\b(?:do\s+not|don't|never|must\s+not|should\s+not|without)\s+(?:the\s+|any\s+)?(?:{alternatives})\b",
            " ",
            text,
        )
    chinese = [action for action in actions if re.search(r"[\u4e00-\u9fff]", action)]
    if chinese:
        alternatives = "|".join(re.escape(action) for action in sorted(chinese, key=len, reverse=True))
        text = re.sub(rf"(?:不要|不需|无需|禁止|不得|不可|不能)\s*(?:{alternatives})", " ", text)
    return text


def hits(text: str, phrases: list[str]) -> list[str]:
    return sorted({phrase for phrase in phrases if phrase.casefold() in text})


def pattern_hits(text: str, patterns: list[dict[str, str]]) -> list[str]:
    return sorted(
        {
            f"pattern:{item['name']}"
            for item in patterns
            if re.search(item["regex"], text, re.IGNORECASE)
        }
    )


def explicit_skill(prompt: str) -> str | None:
    match = EXPLICIT_RE.search(prompt)
    return match.group(1).casefold() if match else None


def select_route(
    policy: dict[str, Any],
    text: str,
    action_text: str,
    matched: dict[str, list[str]],
    explicit: str | None,
) -> str:
    if explicit in CHILD_ROUTES:
        return explicit
    if matched.get("external"):
        return "release"
    for route in ("status", "learn", "init", "release", "run", "review"):
        candidate = action_text if route == "run" else text
        if hits(candidate, policy["routes"].get(route, [])):
            return route
    return "none"


def assess(prompt: str, policy: dict[str, Any]) -> dict[str, Any]:
    if not prompt.strip():
        raise TriggerError("prompt must not be empty")
    text = normalize(prompt)
    action_text = strip_negated_actions(text, policy["signals"]["action"])
    matched = {
        name: hits(action_text if name == "action" else text, phrases)
        for name, phrases in policy["signals"].items()
    }
    matched["external"] = sorted(
        set(matched.get("external", [])) | set(pattern_hits(text, policy["external_patterns"]))
    )
    matched = {name: values for name, values in matched.items() if values}
    score = sum(int(policy["weights"].get(name, 0)) for name in matched if name != "external")
    explicit = explicit_skill(prompt)
    route = select_route(policy, text, action_text, matched, explicit)

    decision = "IGNORE"
    persistence = policy["implicit_persistence"]
    authority = "read-only"
    required_authority = "none"
    provenance = "implicit-semantic"
    reasons: list[str] = []

    if explicit in CHILD_ROUTES - {"release"} and matched.get("external"):
        provenance = "explicit-child"
        decision = "BLOCK_EXTERNAL"
        route = explicit
        if route == "run":
            persistence = "authorized"
            authority = "repository-write"
        elif route == "init":
            persistence = "authorized"
            authority = "repository-write"
        elif route == "status":
            persistence = "existing-read-only"
            authority = "read-only"
        else:
            persistence = "session-only"
            authority = "read-only"
        required_authority = "action-scoped-approval"
        reasons.append(f"${explicit} may keep its local route but cannot execute the external or hardware action")
    elif explicit:
        provenance = "explicit-child" if explicit in CHILD_ROUTES else "explicit-router"
        decision = "EXPLICIT"
        route = route if route != "none" else "run"
        if route == "run":
            persistence = "authorized" if explicit == "run" else "confirm"
            authority = "repository-write"
        elif route == "init":
            persistence = "authorized" if explicit == "init" else "confirm"
            authority = "repository-write" if explicit == "init" else "read-only"
        elif route == "release":
            persistence = "required"
            authority = "pending-approval" if matched.get("external") else "read-only"
            required_authority = "action-scoped-approval" if matched.get("external") else "none"
        elif route in {"status", "review", "learn"}:
            persistence = "existing-read-only" if route == "status" else "session-only"
            authority = "read-only"
        reasons.append("explicit skill invocation")
        if explicit == "superworkflows" and route == "init":
            reasons.append("persistent initialization requires an exact $init invocation")
    elif matched.get("external"):
        decision = "BLOCK_EXTERNAL"
        route = "release"
        persistence = "required"
        authority = "blocked"
        required_authority = "action-scoped-approval"
        reasons.append("external or hardware action requires explicit scoped authorization")
    elif matched.get("continuation"):
        decision = "SUGGEST"
        route = "status"
        persistence = "existing-read-only"
        authority = "read-only"
        reasons.append("continuation language cannot select or resume a run implicitly")
    elif route in {"status", "review"} and (matched.get("assurance") or matched.get("read_only")):
        decision = "ACTIVATE_SESSION_ONLY"
        persistence = "session-only"
        authority = "read-only"
        reasons.append("high-confidence read-only workflow")
    elif (
        route == "run"
        and score >= int(policy["thresholds"]["activate_session_only"])
        and matched.get("action")
        and (matched.get("robotics") or matched.get("complexity"))
        and (matched.get("complexity") or matched.get("assurance") or matched.get("persistence"))
        and not matched.get("simple")
    ):
        decision = "ACTIVATE_SESSION_ONLY"
        persistence = "session-only"
        authority = "repository-write"
        reasons.append("combined action, scope/domain, and assurance signals")
    elif (
        route == "none"
        and matched.get("read_only")
        and not any(matched.get(name) for name in ("action", "assurance", "persistence", "continuation"))
    ):
        reasons.append("generic read-only explanation stays outside Superworkflows")
    elif score >= int(policy["thresholds"]["suggest"]):
        decision = "SUGGEST"
        persistence = "forbidden"
        authority = "read-only"
        reasons.append("plausible but ambiguous workflow fit")
    else:
        reasons.append("insufficient combined signals")

    return {
        "schema_version": 1,
        "policy_version": policy["policy_version"],
        "request_digest": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "provenance": provenance,
        "explicit_skill": explicit,
        "decision": decision,
        "route": route,
        "persistence": persistence,
        "authority": authority,
        "required_authority": required_authority,
        "score": score,
        "matched_signals": matched,
        "reasons": reasons,
        "raw_prompt_retained": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", help="request text; stdin is used when omitted")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY), help="trigger policy JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    prompt = args.prompt if args.prompt is not None else sys.stdin.read()
    try:
        result = assess(prompt, load_policy(Path(args.policy).expanduser().resolve()))
    except TriggerError as exc:
        print(f"triggerctl: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
