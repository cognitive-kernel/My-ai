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
PHP_CURRICULUM=[
{"order":1,"topic":"PHP syntax and execution","goal":"PHP tags, statements, variables and CLI/web execution"},
{"order":2,"topic":"Types and operators","goal":"Scalar types, arrays, objects, operators and coercion"},
{"order":3,"topic":"Control flow and functions","goal":"Conditions, loops, functions, scope and closures"},
{"order":4,"topic":"Arrays and strings","goal":"Array APIs, string handling and common patterns"},
{"order":5,"topic":"OOP","goal":"Classes, interfaces, traits, inheritance and exceptions"},
{"order":6,"topic":"Namespaces and Composer","goal":"Namespaces, autoloading, Composer and packages"},
{"order":7,"topic":"HTTP and web programming","goal":"Requests, responses, sessions, cookies and security"},
{"order":8,"topic":"Databases","goal":"PDO, SQL, transactions and data access"},
{"order":9,"topic":"Testing and tooling","goal":"PHPUnit, static analysis, formatting and debugging"},
{"order":10,"topic":"Production PHP","goal":"Configuration, logging, security, performance and deployment"}]
JAVASCRIPT_CURRICULUM=[
{"order":1,"topic":"JavaScript fundamentals","goal":"Syntax, variables, values and expressions"},
{"order":2,"topic":"Control flow and functions","goal":"Conditions, loops, functions and scope"},
{"order":3,"topic":"Objects and arrays","goal":"Objects, arrays, destructuring and iteration"},
{"order":4,"topic":"Modules","goal":"ES modules, imports, exports and package management"},
{"order":5,"topic":"Async JavaScript","goal":"Promises, async/await and event loops"},
{"order":6,"topic":"Web APIs","goal":"DOM, fetch, storage and browser events"},
{"order":7,"topic":"Node.js","goal":"Node runtime, filesystem, HTTP and processes"},
{"order":8,"topic":"Testing and production","goal":"Testing, security, performance and deployment"}]
LANGUAGE_CURRICULA={"Python":PYTHON_CURRICULUM,"C":C_CURRICULUM,"PHP":PHP_CURRICULUM,"JavaScript":JAVASCRIPT_CURRICULUM}
LANGUAGE_SOURCES={
"Python":["https://docs.python.org/3/tutorial/","https://docs.python.org/3/library/"],
"C":["https://en.cppreference.com/w/c","https://www.gnu.org/software/gnu-c-manual/"],
"PHP":["https://www.php.net/manual/en/","https://www.php.net/docs.php"],
"JavaScript":["https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide","https://developer.mozilla.org/en-US/docs/Web/API"]
}
def curriculum(language):
    for name,data in LANGUAGE_CURRICULA.items():
        if name.lower()==language.lower(): return data
    return []
def canonical_language(language):
    for name in LANGUAGE_CURRICULA:
        if name.lower()==language.strip().lower(): return name
    return language.strip()
def next_topic(language,completed=None):
    completed=completed or set()
    return next((x for x in curriculum(language) if str(x["topic"]) not in completed),None)
def source_urls(language):
    for name,urls in LANGUAGE_SOURCES.items():
        if name.lower()==language.lower(): return urls
    return []
