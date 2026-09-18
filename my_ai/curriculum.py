from __future__ import annotations
PYTHON_CURRICULUM=[
{"order":1,"topic":"Syntax and execution","goal":"Scripts, indentation, expressions, comments"},
{"order":2,"topic":"Variables and types","goal":"Numbers, strings, booleans, None and conversions"},
{"order":3,"topic":"Control flow","goal":"if, for, while, match, break and continue"},
{"order":4,"topic":"Functions","goal":"Functions, parameters, scope, closures and decorators"},
{"order":5,"topic":"Collections","goal":"list, tuple, set, dict and comprehensions"},
{"order":6,"topic":"Modules and packages","goal":"Imports, packages, environments and dependencies"},
{"order":7,"topic":"Exceptions","goal":"Exception handling and custom exceptions"},
{"order":8,"topic":"Files and serialization","goal":"Paths, files, JSON and CSV"},
{"order":9,"topic":"Object-oriented Python","goal":"Classes, composition, inheritance and protocols"},
{"order":10,"topic":"Typing","goal":"Type hints, generics, protocols and static analysis"},
{"order":11,"topic":"Testing","goal":"Unit, integration and regression testing"},
{"order":12,"topic":"Async programming","goal":"async/await, tasks and concurrency"},
{"order":13,"topic":"Databases","goal":"SQLite, SQL and data-access patterns"},
{"order":14,"topic":"HTTP and APIs","goal":"HTTP clients and FastAPI services"},
{"order":15,"topic":"Packaging","goal":"Packages, builds and reproducible environments"},
{"order":16,"topic":"Production practices","goal":"Logging, security, performance and deployment"}]
C_CURRICULUM=[
{"order":1,"topic":"C fundamentals","goal":"Compilation, main, variables and expressions"},
{"order":2,"topic":"Control flow","goal":"if, switch, loops and functions"},
{"order":3,"topic":"Arrays and strings","goal":"Arrays, C strings and standard library"},
{"order":4,"topic":"Pointers","goal":"Pointers, addresses and pointer arithmetic"},
{"order":5,"topic":"Memory management","goal":"malloc, calloc, realloc and free"},
{"order":6,"topic":"Structs and enums","goal":"User-defined data structures"},
{"order":7,"topic":"Files and I/O","goal":"stdio files and binary I/O"},
{"order":8,"topic":"Headers and compilation","goal":"Translation units, headers, linker and Make"},
{"order":9,"topic":"Debugging and testing","goal":"Compiler warnings, sanitizers and tests"},
{"order":10,"topic":"Systems programming","goal":"Processes, POSIX concepts and robust C"}]
def curriculum(language): return C_CURRICULUM if language.lower()=="c" else PYTHON_CURRICULUM
def next_topic(language,completed=None):
    completed=completed or set()
    return next((x for x in curriculum(language) if str(x["topic"]) not in completed),None)
