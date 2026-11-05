#!/usr/bin/env python3
"""Log which Karabiner rules fire and report them as per-layer keyboard heatmaps.

    heat.py on                start the receiver LaunchAgent and instrument the goku profile
    heat.py off               stop the receiver and remove the instrumentation; the log stays
    heat.py report [--days N]
    heat.py serve             the receiver itself, run by launchd

Instrumented rules send a send_user_command datagram; the receiver appends one JSON object per event
to ~/.local/state/goku/usage.jsonl and re-instruments karabiner.json after goku rewrites it. Only rules
are instrumented, so keys without a rule (ordinary letters) are never recorded.

Do not log through shell_command: Karabiner SIGKILLs the running shell_command when it starts the next
one, so logging would lose its own events and could kill the rule's real commands.
"""

import argparse
import json
import math
import os
import plistlib
import re
import socket
import subprocess
import sys
import tempfile
import time
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KARABINER = Path.home() / ".config/karabiner/karabiner.json"
STATE = Path.home() / ".local/state/goku"
LOG = STATE / "usage.jsonl"
SOCKET = STATE / "usage.sock"
AGENT_LABEL = "com.sid.goku-heat"
AGENT_PLIST = Path.home() / f"Library/LaunchAgents/{AGENT_LABEL}.plist"
AGENT_PYTHON = "/opt/homebrew/bin/python3"
SYNC_INTERVAL_SECONDS = 2

MODIFIERS = {
    "left_command": "⌘", "right_command": "R⌘", "left_option": "⌥", "right_option": "R⌥",
    "left_control": "⌃", "right_control": "R⌃", "left_shift": "⇧", "right_shift": "R⇧",
}  # fmt: skip
PASSTHROUGH = {*MODIFIERS, "fn"}
SHELL_ACTIONS = [
    (re.compile(r'hsurl\("(.*?)"\)'), "hs"),
    (re.compile(r"bin/aerospace (.*)"), "as"),
    (re.compile(r"as\.py (.*)"), "as-py"),
    (re.compile(r"\bdo (.*)"), "rex"),
    (re.compile(r"bin/m1ddc (.*)"), "m1ddc"),
]
ROWS = [
    ("", "grave_accent_and_tilde 1 2 3 4 5 6 7 8 9 0 hyphen equal_sign"),
    ("   ", "q w e r t y u i o p open_bracket close_bracket"),
    ("     ", "a s d f g h j k l semicolon quote"),
    ("        ", "z x c v b n m comma period slash"),
]
ON_GRID = {key for _, row in ROWS for key in row.split()}
KEY_LABELS = {
    "grave_accent_and_tilde": "`", "hyphen": "-", "equal_sign": "=", "open_bracket": "[", "close_bracket": "]",
    "semicolon": ";", "quote": "'", "comma": ",", "period": ".", "slash": "/", "caps_lock": "Caps",
    "escape": "Esc", "return_or_enter": "⏎", "up_arrow": "↑", "down_arrow": "↓", "tab": "Tab", "fn": "Fn",
    **MODIFIERS,
}  # fmt: skip
HEAT = [(229, 16), (222, 16), (215, 16), (208, 16), (160, 231)]
MIRRORS = {
    "bracket-l-mode": "bracket-r-mode", "bracket-r-mode": "bracket-l-mode",
    "rex-comma-mode": "rex-period-mode", "rex-period-mode": "rex-comma-mode",
}  # fmt: skip
REVERSAL_WINDOW_MS = 2000


def phases(manipulator: dict):
    """Every event list a manipulator can post, named by when it fires."""
    delayed = manipulator.get("to_delayed_action", {})
    yield "press", manipulator.get("to")
    yield "tap", manipulator.get("to_if_alone")
    yield "hold", manipulator.get("to_if_held_down")
    yield "release", manipulator.get("to_after_key_up")
    yield "delayed", delayed.get("to_if_invoked")
    yield "canceled", delayed.get("to_if_canceled")


def describe(rule: dict, manipulator: dict) -> dict:
    """The fields shared by all events of one manipulator."""
    source = manipulator["from"]
    conditions = manipulator.get("conditions", [])
    scope = [
        bundle.strip("^$").replace("\\", "")
        for condition in conditions
        if condition["type"] == "frontmost_application_if"
        for bundle in condition["bundle_identifiers"]
    ]
    layers = [condition["name"] for condition in conditions if condition["type"] == "variable_if"]
    if "simultaneous" in source:
        # Goku simlayer: the first `to` event turns the layer on and the last key is the one inside it.
        key = source["simultaneous"][-1].get("key_code", "")
        layer = next((event["set_variable"]["name"] for event in manipulator["to"] if "set_variable" in event), "")
        via = "simultaneous"
    else:
        key = next((source[field] for field in ("key_code", "consumer_key_code", "pointing_button", "any") if field in source), "")
        layer = layers[-1] if layers else ""
        via = "key"
    return {
        "rule": rule["description"],
        "layer": layer,
        "key": key,
        "mods": source.get("modifiers", {}).get("mandatory", []),
        "scope": ",".join(scope),
        "via": via,
    }


def summarize_shell(command: str) -> str:
    for pattern, prefix in SHELL_ACTIONS:
        if match := pattern.search(command):
            return f"{prefix}:{match.group(1)}"
    return "sh:" + re.sub(r'^export PATH="[^"]*";', "", command)


def summarize(events: list[dict]) -> str:
    parts = []
    for event in events:
        if "set_variable" in event:
            parts.append(f"{event['set_variable']['name']}={event['set_variable']['value']}")
        elif "shell_command" in event:
            parts.append(summarize_shell(event["shell_command"]))
        elif code := event.get("key_code") or event.get("consumer_key_code") or event.get("pointing_button"):
            parts.append("+".join([*event.get("modifiers", []), code]))
        else:
            parts.append(next(iter(event)))
    return "; ".join(parts)


def is_log_event(event: dict) -> bool:
    return event.get("send_user_command", {}).get("endpoint") == str(SOCKET)


def is_passthrough(events: list[dict]) -> bool:
    """A modifier sent as itself: every chord would log it, and nothing about the rule happened yet."""
    return all(event.get("key_code") in PASSTHROUGH and not event.get("modifiers") for event in events)


def log_event(fields: dict, phase: str, events: list[dict]) -> dict:
    return {"send_user_command": {"endpoint": str(SOCKET), "payload": {**fields, "phase": phase, "do": summarize(events)}}}


def strip(rules: list[dict]) -> None:
    for rule in rules:
        for manipulator in rule["manipulators"]:
            for _, events in phases(manipulator):
                if events:
                    events[:] = [event for event in events if not is_log_event(event)]


def instrument(rules: list[dict]) -> None:
    strip(rules)
    for rule in rules:
        for manipulator in rule["manipulators"]:
            fields = describe(rule, manipulator)
            for phase, events in phases(manipulator):
                if events and not (phase == "press" and is_passthrough(events)):
                    # First, so the rule's last key event stays last and keeps its hold and key repeat.
                    events.insert(0, log_event(fields, phase, events))


def goku_rules(config: dict) -> list[dict]:
    for profile in config["profiles"]:
        if profile["name"] == "goku":
            return profile["complex_modifications"]["rules"]
    raise SystemExit("karabiner.json: no goku profile")


def rewrite(transform) -> bool:
    """Apply transform to the goku rules; write karabiner.json only if that changed them."""
    config = json.loads(KARABINER.read_text())
    rules = goku_rules(config)
    before = json.dumps(rules)
    transform(rules)
    if json.dumps(rules) == before:
        return False
    descriptor, temporary = tempfile.mkstemp(dir=KARABINER.parent, prefix=".karabiner-heat-")
    with os.fdopen(descriptor, "w") as file:
        json.dump(config, file, ensure_ascii=False, indent=4)
        file.write("\n")
    os.chmod(temporary, KARABINER.stat().st_mode & 0o777)
    os.replace(temporary, KARABINER)
    return True


def frontmost_app() -> str:
    front = subprocess.run(["/usr/bin/lsappinfo", "front"], capture_output=True, text=True).stdout.strip()
    info = subprocess.run(["/usr/bin/lsappinfo", "info", "-only", "bundleid", front], capture_output=True, text=True).stdout
    match = re.search(r'bundleID="([^"]*)"', info)
    return match.group(1) if match else ""


def keep_instrumented(synced_mtime: int | None) -> int | None:
    """goku rewrites karabiner.json without the logging events; put them back."""
    if KARABINER.stat().st_mtime_ns == synced_mtime:
        return synced_mtime
    try:
        rewrite(instrument)
    except json.JSONDecodeError:  # goku is mid-write: retry on the next tick
        return synced_mtime
    return KARABINER.stat().st_mtime_ns


def serve() -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    SOCKET.unlink(missing_ok=True)
    receiver = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    receiver.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
    receiver.bind(str(SOCKET))
    receiver.settimeout(SYNC_INTERVAL_SECONDS)
    synced_mtime = None
    while True:
        try:
            payload = json.loads(receiver.recv(65536))
        except TimeoutError:
            pass
        except ValueError:
            continue
        else:
            record = {"ts": int(time.time() * 1000), "app": frontmost_app(), **payload}
            with LOG.open("a") as log:
                log.write(json.dumps(record, ensure_ascii=False) + "\n")
        synced_mtime = keep_instrumented(synced_mtime)


def launchctl(*args: str, check: bool = False) -> bool:
    return subprocess.run(["launchctl", *args], capture_output=not check, check=check).returncode == 0


def agent_target() -> str:
    return f"gui/{os.getuid()}/{AGENT_LABEL}"


def start() -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    AGENT_PLIST.write_bytes(
        plistlib.dumps(
            {
                "Label": AGENT_LABEL,
                "ProgramArguments": [AGENT_PYTHON, str(Path(__file__).resolve()), "serve"],
                "RunAtLoad": True,
                "KeepAlive": True,
                "StandardErrorPath": str(STATE / "receiver.err"),
            }
        )
    )
    launchctl("bootout", agent_target())
    launchctl("bootstrap", f"gui/{os.getuid()}", str(AGENT_PLIST), check=True)
    rewrite(instrument)


def stop() -> None:
    launchctl("bootout", agent_target())
    AGENT_PLIST.unlink(missing_ok=True)
    SOCKET.unlink(missing_ok=True)
    rewrite(strip)


def key_label(key: str, mods=()) -> str:
    return "".join(MODIFIERS.get(mod, mod) for mod in mods) + KEY_LABELS.get(key, key.upper() if len(key) == 1 else key)


def read_events(since_ms: int) -> list[dict]:
    if not LOG.exists():
        return []
    events = []
    for line in LOG.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("ts", 0) >= since_ms:
            events.append(event)
    return sorted(events, key=lambda event: event["ts"])


def is_use(event: dict) -> bool:
    """One deliberate use of a key. A top-level press that only arms a layer is not one."""
    if event["phase"] in ("tap", "hold", "delayed"):
        return True
    if event["phase"] != "press":
        return False
    return bool(event["layer"]) or not all(
        part.endswith("=1") or part.startswith("hs:whichkey") for part in event["do"].split("; ")
    )


def layer_parents(rules: list[dict]) -> dict[str, str]:
    parents = {}
    for rule in rules:
        for manipulator in rule["manipulators"]:
            fields = describe(rule, manipulator)
            if fields["layer"] and fields["via"] == "key":
                for event in manipulator["to"]:
                    variable = event.get("set_variable", {})
                    if variable.get("value") == 1:
                        parents[variable["name"]] = fields["layer"]
    return parents


def steps_to(layer: str, parents: dict[str, str]) -> int:
    """Key presses a use of this layer takes: ' g q is 3."""
    steps, seen = 1, set()
    while layer and layer not in seen:
        seen.add(layer)
        steps += 1
        layer = parents.get(layer, "")
    return steps


def reversal(first: dict, second: dict) -> bool:
    """second undoes first shortly after: a sign that first was unintended."""
    if second["ts"] - first["ts"] > REVERSAL_WINDOW_MS:
        return False
    if MIRRORS.get(first["layer"]) == second["layer"]:
        return first["key"] == second["key"]
    return first["layer"] == second["layer"] != "" and {first["key"], second["key"]} == {"comma", "period"}


def compact(count: int) -> str:
    if count < 1000:
        return str(count)
    return f"{count / 1000:.1f}k" if count < 10000 else f"{count // 1000}k"


def cell(key: str, count: int, bound: bool, peak: int, color: bool) -> str:
    text = f"{KEY_LABELS.get(key, key.upper())} {compact(count) if count else '·' if bound else '-':>4}"
    if not color:
        return text
    if not count:
        return text if bound else f"\x1b[2m{text}\x1b[0m"
    level = min(int(math.log(count) / math.log(peak + 1) * len(HEAT)), len(HEAT) - 1)
    background, foreground = HEAT[level]
    return f"\x1b[48;5;{background};38;5;{foreground}m{text}\x1b[0m"


def print_layer(title: str, counts: Counter, bound: set, color: bool) -> None:
    print(f"\n{title} · {sum(counts.values())} 次")
    peak = max(counts.values(), default=1)
    has_grid = sum(1 for key, mods in bound if key in ON_GRID and not mods) >= 3
    if has_grid:
        for indent, row in ROWS:
            print(indent + " ".join(cell(key, counts[(key, ())], (key, ()) in bound, peak, color) for key in row.split()))
    others = [entry for entry in counts if not has_grid or entry[0] not in ON_GRID or entry[1]]
    if others:
        print("其它: " + "  ".join(f"{key_label(*entry)} {counts[entry]}" for entry in sorted(others, key=counts.get, reverse=True)))
    unused = sorted(key_label(*entry) for entry in bound if not counts[entry])
    if unused:
        print("0 次: " + " ".join(unused))


def recording_status(rules: list[dict]) -> str:
    live = any(
        is_log_event(event)
        for rule in rules
        for manipulator in rule["manipulators"]
        for _, events in phases(manipulator)
        for event in events or []
    )
    running = launchctl("print", agent_target())
    if running:
        return "记录中" if live else "⚠ 接收进程在运行，但配置未插桩，这段时间没有记录"
    return "⚠ 配置已插桩，但接收进程没有运行（运行 heat.py on）" if live else "未开启"


def report(days: int) -> None:
    rules = goku_rules(json.loads(KARABINER.read_text()))
    color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    events = read_events(int((time.time() - days * 86400) * 1000))
    uses = [event for event in events if is_use(event)]
    titles = {menu["id"]: menu["title"] for menu in tomllib.loads((ROOT / "menus.toml").read_text())["menu"]}
    parents = layer_parents(rules)

    bound = defaultdict(set)
    for rule in rules:
        for manipulator in rule["manipulators"]:
            fields = describe(rule, manipulator)
            bound[(fields["layer"], fields["scope"])].add((fields["key"], tuple(fields["mods"])))
    counts = defaultdict(Counter)
    for event in uses:
        counts[(event["layer"], event["scope"])][(event["key"], tuple(event["mods"]))] += 1

    print(f"Goku 热力图 · 最近 {days} 天 · {len(uses)} 次使用 · {recording_status(rules)}")
    print(f"日志: {LOG}")
    if color:
        print("颜色越深次数越多   · 已绑定但 0 次   - 未绑定")

    groups = sorted({*bound, *counts}, key=lambda group: -sum(counts[group].values()))
    for group in groups:
        if counts[group]:
            layer, scope = group
            name = f"{titles[layer]} ({layer})" if layer in titles else layer or "顶层键"
            print_layer(name + (f" · {scope}" if scope else ""), counts[group], bound[group], color)
    idle = [" · ".join(filter(None, group)) or "顶层键" for group in groups if not counts[group]]
    if idle:
        print("\n本期没用过的层: " + "、".join(idle))

    costly = Counter()
    actions = {}
    for event in uses:
        entry = (event["layer"], event["scope"], event["key"], tuple(event["mods"]))
        if steps_to(event["layer"], parents) >= 3:
            costly[entry] += 1
            actions[entry] = event["do"]
    if costly:
        print("\n最值得变短（次数 × 步数）:")
        ranked = sorted(costly, key=lambda entry: -costly[entry] * steps_to(entry[0], parents))
        for entry in ranked[:10]:
            steps = steps_to(entry[0], parents)
            print(f"  {costly[entry]:>5} × {steps}  {entry[0]} {key_label(entry[2], entry[3])}  {actions[entry][:60]}")

    chords = Counter(
        f"{event['layer']} + {key_label(event['key'], event['mods'])}"
        for event in events
        if event["via"] == "simultaneous" and event["phase"] == "press"
    )
    if chords:
        print("\nsimlayer 触发次数（看不该出现的组合）:")
        print("  " + "  ".join(f"{chord} {count}" for chord, count in chords.most_common(15)))

    undone = Counter(
        f"{first['layer']} {key_label(first['key'])} → {second['layer']} {key_label(second['key'])}"
        for first, second in zip(uses, uses[1:])
        if reversal(first, second)
    )
    if undone:
        print(f"\n{REVERSAL_WINDOW_MS // 1000} 秒内被反向操作（疑似误触）:")
        print("  " + "  ".join(f"{pair} {count}" for pair, count in undone.most_common(10)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["on", "off", "report", "serve"])
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args()

    if args.command == "on":
        start()
        print(f"记录中: {LOG}")
    elif args.command == "off":
        stop()
        print("已停止记录，日志保留")
    elif args.command == "serve":
        serve()
    else:
        report(args.days)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
