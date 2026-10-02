"""Capability inventory for the no-code management surface."""
from __future__ import annotations
from .control_plane import namespace_catalog


CAPABILITIES = {
 "configuration":["registry","validation","reset","import","export","versioning","audit","profiles"],
 "llm":["providers","models","keys","rotation","routing","fallback","health","metrics"],
 "learning":["courses","topics","sources","approval","provenance","version-awareness","experience"],
 "agent":["behavior","persona","planning","workflows","trace","budget","cancellation"],
 "tools":["catalog","permissions","timeouts","retries","http","webhook","command","health"],
 "memory":["short-term","long-term","experiential","retention","provenance","selective-delete"],
 "research":["providers","allowlist","ranking","freshness","manual-sources","approval"],
 "security":["roles","capabilities","network","filesystem","subprocess","approvals","audit"],
 "self-improvement":["self-update","self-repair","snapshots","rollback","proposals","lessons"],
 "scheduler":["jobs","workers","concurrency","priority","quotas","pause-resume-cancel"],
 "multimodal":["image","voice","whisper","tts","routing","health"],
 "execution":["profiles","sandbox","limits","projects","commands","environment-secrets","history"],
 "integrations":["providers","credentials","events","webhooks","mapping","health"],
 "server":["host-port","cors","sessions","uploads","timeouts","rate-limit","maintenance","notifications"],
 "observability":["logs","metrics","traces","telemetry","alerts","dashboard","diagnostics"],
 "database":["backup","restore","retention","encryption","migration","integrity"],
 "behavior":["prompts","policies","versioning","activation","rollback","diff","task-routing"],
 "advanced-agent":["skills","knowledge-graph","hybrid-retrieval","context","verification","confidence",
                   "evaluation","regression","research-agent","secure-environment","parallelism","cache",
                   "budget","events","meta-agent","agent-os","version-evolution"],
}

def inventory():
    return {"capabilities":CAPABILITIES,"control_plane_namespaces":namespace_catalog()}
