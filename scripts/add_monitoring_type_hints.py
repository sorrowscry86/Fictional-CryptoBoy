#!/usr/bin/env python3
"""
Batch add type hints to monitoring/ files
Fixes 17 functions across 3 files
"""

import re
from pathlib import Path

# Define replacements for each file
REPLACEMENTS = {
    "monitoring/dashboard_service.py": [
        (r"(    def _connect_redis\(self\)):", r"\1 -> None:"),
        (r"(    async def broadcast_to_clients\(self, message: Dict\[str, Any\])):", r"\1 -> None:"),
        (r"(    def setup_routes\(self\)):", r"\1 -> None:"),
        (r"(    async def handle_index\(self, request\)):", r"\1 -> web.Response:"),
        (r"(    async def handle_metrics\(self, request\)):", r"\1 -> web.Response:"),
        (r"(    async def handle_force_buy\(self, request\)):", r"\1 -> web.Response:"),
        (r"(    async def handle_force_sell\(self, request\)):", r"\1 -> web.Response:"),
        (r"(    async def handle_get_open_trades\(self, request\)):", r"\1 -> web.Response:"),
        (r"(    async def handle_get_audit_log\(self, request\)):", r"\1 -> web.Response:"),
        (r"(    async def handle_websocket\(self, request\)):", r"\1 -> web.WebSocketResponse:"),
        (r"(    async def metrics_broadcast_loop\(self\)):", r"\1 -> None:"),
        (r"(    async def start_background_tasks\(self, app\)):", r"\1 -> None:"),
        (r"(    async def cleanup_background_tasks\(self, app\)):", r"\1 -> None:"),
        (r"(    def run\(self\)):", r"\1 -> None:"),
        (r"(^def main\(\)):", r"\1 -> None:"),
    ],
    "monitoring/manual_trade_controller.py": [
        (r"(^def main\(\)):", r"\1 -> None:"),
    ],
    "monitoring/strategy_monitor.py": [
        (r"(^def main\(\)):", r"\1 -> None:"),
    ],
}


def add_type_hints(filepath: Path, replacements: list):
    """Apply regex replacements to add type hints"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        modified = content
        changes = 0

        for pattern, replacement in replacements:
            new_content = re.sub(pattern, replacement, modified, flags=re.MULTILINE)
            if new_content != modified:
                changes += re.sub(pattern, replacement, modified, flags=re.MULTILINE).count(replacement.split("\\1")[-1]) - modified.count(replacement.split("\\1")[-1])
                modified = new_content

        if modified != content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(modified)
            print(f"✓ {filepath}: Applied type hints")
            return True
        else:
            print(f"- {filepath}: No changes needed")
            return False

    except Exception as e:
        print(f"✗ {filepath}: Error - {e}")
        return False


def main():
    """Main execution"""
    project_root = Path(__file__).parent.parent
    total_files = 0
    modified_files = 0

    print("=" * 60)
    print("Adding Type Hints to Monitoring Files")
    print("=" * 60)

    for filepath_str, replacements in REPLACEMENTS.items():
        filepath = project_root / filepath_str
        total_files += 1

        if add_type_hints(filepath, replacements):
            modified_files += 1

    print("=" * 60)
    print(f"Complete: {modified_files}/{total_files} files modified")
    print("=" * 60)


if __name__ == "__main__":
    main()
