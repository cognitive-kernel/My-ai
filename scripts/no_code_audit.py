#!/usr/bin/env python3
"""Inventory mutable hard-coded configuration for migration into the registry."""
from __future__ import annotations
import ast, pathlib, re, json


def scan(root="my_ai"):
    findings=[]
    for path in pathlib.Path(root).rglob("*.py"):
        try: tree=ast.parse(path.read_text(encoding="utf-8"))
        except Exception: continue
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=="getenv":
                findings.append({"file":str(path),"line":node.lineno,"kind":"env"})
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                v=node.value
                if re.match(r"https?://",v) or re.match(r"\d+(\.\d+)?(s|ms|m|h)$",v):
                    findings.append({"file":str(path),"line":node.lineno,"kind":"mutable-literal","value":v[:160]})
    return findings

if __name__=="__main__":
    print(json.dumps(scan(),ensure_ascii=False,indent=2))
