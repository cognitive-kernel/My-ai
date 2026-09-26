# Network and Offline Policy

My-AI is offline-first. Network access is an explicit exception, not a default capability.

Allowed online categories:
- Configured LLM backend when it is online.
- Explicitly confirmed chat web-learning after the local assistant says it does not know.
- Explicitly configured educational learning sources and scheduled learning review.
- Pentest/security tools and targets that require network access.
- Online installation of missing prerequisites and educational tools.
- Git/GitHub operations.

Everything else must use local resources and local processing.

## Chat unknown -> confirmed learning

1. Search local memory/knowledge first.
2. If the local LLM cannot answer reliably, emit `__MYAI_UNKNOWN__`.
3. My-AI tells the user it does not know and asks for confirmation.
4. Only after confirmation, search the web and fetch permitted public pages.
5. The local LLM extracts a lesson from the evidence.
6. Store the source and knowledge locally.
7. Add the lesson to the matching learning domain.
8. If the topic does not exist, create a new curriculum topic.

## Prerequisites

`my_ai/runtime_prerequisites.py` checks `requirements.txt` and selected system tools at startup. With `MYAI_AUTO_INSTALL_PREREQUISITES=true` it installs missing Python packages and supported system tools through the local OS package manager. The default is `false` so application startup does not perform package installation.

New network-capable features must be explicitly added to the allowed list and documented here before implementation.
