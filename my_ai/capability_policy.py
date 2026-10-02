from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Capability:
    name: str
    read_roles: frozenset[str] = frozenset({'admin'})
    write_roles: frozenset[str] = frozenset({'admin'})
    execute_roles: frozenset[str] = frozenset({'admin'})

CAPABILITIES = {
    'github': Capability('github'),
    'security': Capability('security'),
    'code-execution': Capability('code-execution'),
    'code-generation': Capability('code-generation'),
    'database': Capability('database'),
    'session': Capability('session', frozenset({'admin','user'}), frozenset({'admin','user'}), frozenset({'admin','user'})),
    'self-update': Capability('self-update'),
    'self-repair': Capability('self-repair'),
    'admin': Capability('admin'),
    'tools': Capability('tools'),
    'files': Capability('files'),
    'image-generation': Capability('image-generation'),
    'models': Capability('models', frozenset({'admin','user'}), frozenset({'admin'}), frozenset({'admin','user'})),
    'chat': Capability('chat', frozenset({'admin','user'}), frozenset({'admin','user'}), frozenset({'admin','user'})),
    'learning': Capability('learning', frozenset({'admin','user'}), frozenset({'admin','user'}), frozenset({'admin','user'})),
    'memory': Capability('memory', frozenset({'admin','user'}), frozenset({'admin','user'}), frozenset({'admin','user'})),
    'skill-engine': Capability('skill-engine', frozenset({'admin','user'}), frozenset({'admin'}), frozenset({'admin','user'})),
    'eval': Capability('eval', frozenset({'admin','user'}), frozenset({'admin'}), frozenset({'admin'})),
}

def capability_allowed(user, capability: str, action: str) -> bool:
    cap = CAPABILITIES.get(capability)
    if cap is None or user is None:
        return False
    role = str(user.get('role') or '')
    if action == 'read': return role in cap.read_roles
    if action == 'write': return role in cap.write_roles
    if action == 'execute': return role in cap.execute_roles
    return False

def inventory() -> list[dict[str, object]]:
    return [{'name': c.name, 'read_roles': sorted(c.read_roles), 'write_roles': sorted(c.write_roles), 'execute_roles': sorted(c.execute_roles)} for c in CAPABILITIES.values()]