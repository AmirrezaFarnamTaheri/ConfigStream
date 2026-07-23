import ast
import os
import sys


def check_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content)
    except Exception as e:
        return {"error": str(e)}

    missing_return_types = 0
    missing_arg_types = 0
    functions = []
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
            if node.returns is None and node.name != "__init__":
                missing_return_types += 1
            for arg in node.args.args:
                if arg.arg != "self" and arg.arg != "cls" and arg.annotation is None:
                    missing_arg_types += 1
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)

    return {
        "missing_return_types": missing_return_types,
        "missing_arg_types": missing_arg_types,
        "func_count": len(functions),
        "class_count": len(classes),
    }


if __name__ == "__main__":
    base_dir = r"D:\GitHub\ConfigStream\src\configstream"
    total_files = 0
    total_missing_ret = 0
    total_missing_arg = 0
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                res = check_file(filepath)
                if "error" not in res:
                    total_files += 1
                    total_missing_ret += res["missing_return_types"]
                    total_missing_arg += res["missing_arg_types"]
    print(f"Total files: {total_files}")
    print(f"Missing Return Types: {total_missing_ret}")
    print(f"Missing Arg Types: {total_missing_arg}")
