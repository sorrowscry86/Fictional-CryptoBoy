#!/usr/bin/env python3
"""
Script to identify functions missing return type hints.
VoidCat RDC Quality Standard: 100% type hint coverage required.
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


class TypeHintChecker(ast.NodeVisitor):
    """AST visitor to check for missing return type hints"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.missing_hints: List[Tuple[int, str, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check if function has return type annotation"""
        # Skip special methods (dunder methods)
        if node.name.startswith("__") and node.name.endswith("__"):
            self.generic_visit(node)
            return

        # Skip if has return annotation
        if node.returns is not None:
            self.generic_visit(node)
            return

        # Check if function is a property/setter/deleter decorator
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id in ("property", "setter", "deleter"):
                self.generic_visit(node)
                return

        # Function is missing return type hint
        self.missing_hints.append((node.lineno, node.name, "function"))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async functions for return type hints"""
        # Skip special methods
        if node.name.startswith("__") and node.name.endswith("__"):
            self.generic_visit(node)
            return

        # Skip if has return annotation
        if node.returns is not None:
            self.generic_visit(node)
            return

        # Async function is missing return type hint
        self.missing_hints.append((node.lineno, node.name, "async function"))
        self.generic_visit(node)


def check_file(filepath: Path) -> List[Tuple[int, str, str]]:
    """Check a single Python file for missing type hints"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=str(filepath))
        checker = TypeHintChecker(str(filepath))
        checker.visit(tree)

        return checker.missing_hints
    except SyntaxError as e:
        print(f"  ⚠️  Syntax error in {filepath}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  ⚠️  Error checking {filepath}: {e}", file=sys.stderr)
        return []


def main():
    """Main entry point"""
    # Directories to check
    dirs_to_check = ["llm", "services", "data", "strategies", "monitoring", "risk", "backtest"]

    project_root = Path(__file__).parent.parent
    total_missing = 0
    files_with_issues = 0

    print("=" * 80)
    print("VoidCat RDC Type Hint Coverage Report")
    print("=" * 80)
    print()

    for directory in dirs_to_check:
        dir_path = project_root / directory
        if not dir_path.exists():
            continue

        print(f"\n📂 Checking {directory}/")
        print("-" * 80)

        # Find all Python files
        py_files = sorted(dir_path.rglob("*.py"))

        for py_file in py_files:
            relative_path = py_file.relative_to(project_root)

            missing = check_file(py_file)
            if missing:
                files_with_issues += 1
                print(f"\n  {relative_path} - {len(missing)} missing")

                for lineno, func_name, func_type in missing:
                    print(f"    Line {lineno:4d}: {func_name}() [{func_type}]")

                total_missing += len(missing)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files with missing type hints: {files_with_issues}")
    print(f"Total functions missing hints: {total_missing}")

    if total_missing == 0:
        print("\n✅ PASSED: 100% type hint coverage achieved!")
        return 0
    else:
        print(f"\n❌ FAILED: {total_missing} functions need type hints")
        print("VoidCat RDC Standard: 100% type hint coverage required")
        return 1


if __name__ == "__main__":
    sys.exit(main())
