from __future__ import annotations

import re

PYTHON_CURRICULUM=[{"order":1,"topic":"Syntax and execution","goal":"Scripts, indentation, expressions, comments"},{"order":2,"topic":"Variables and types","goal":"Numbers, strings, booleans, None and conversions"},{"order":3,"topic":"Control flow","goal":"if, for, while, match, break and continue"},{"order":4,"topic":"Functions","goal":"Functions, parameters, scope, closures and decorators"},{"order":5,"topic":"Collections","goal":"list, tuple, set, dict and comprehensions"},{"order":6,"topic":"Modules and packages","goal":"Imports, packages, environments and dependencies"},{"order":7,"topic":"Exceptions","goal":"Exception handling and custom exceptions"},{"order":8,"topic":"Files and serialization","goal":"Paths, files, JSON and CSV"},{"order":9,"topic":"Object-oriented Python","goal":"Classes, composition, inheritance and protocols"},{"order":10,"topic":"Typing","goal":"Type hints, generics, protocols and static analysis"},{"order":11,"topic":"Testing","goal":"Unit, integration and regression testing"},{"order":12,"topic":"Async programming","goal":"async/await, tasks and concurrency"},{"order":13,"topic":"Databases","goal":"SQLite, SQL and data-access patterns"},{"order":14,"topic":"HTTP and APIs","goal":"HTTP clients and FastAPI services"},{"order":15,"topic":"Packaging","goal":"Packages, builds and reproducible environments"},{"order":16,"topic":"Production practices","goal":"Logging, security, performance and deployment"}]
C_CURRICULUM=[{"order":1,"topic":"C fundamentals","goal":"Compilation, main, variables and expressions"},{"order":2,"topic":"Control flow","goal":"if, switch, loops and functions"},{"order":3,"topic":"Arrays and strings","goal":"Arrays, C strings and standard library"},{"order":4,"topic":"Pointers","goal":"Pointers, addresses and pointer arithmetic"},{"order":5,"topic":"Memory management","goal":"malloc, calloc, realloc and free"},{"order":6,"topic":"Structs and enums","goal":"User-defined data structures"},{"order":7,"topic":"Files and I/O","goal":"stdio files and binary I/O"},{"order":8,"topic":"Headers and compilation","goal":"Translation units, headers, linker and Make"},{"order":9,"topic":"Debugging and testing","goal":"Compiler warnings, sanitizers and tests"},{"order":10,"topic":"Systems programming","goal":"Processes, POSIX concepts and robust C"}]

PHP_CURRICULUM=[
{"order":1,"topic":"HTML fundamentals","goal":"HTML5 structure, semantics, forms, tables, media, accessibility and validation"},
{"order":2,"topic":"CSS fundamentals","goal":"Selectors, cascade, box model, Flexbox, Grid, responsive design and media queries"},
{"order":3,"topic":"JavaScript fundamentals","goal":"Types, functions, objects, arrays, DOM, events, modules, fetch and async/await"},
{"order":4,"topic":"jQuery","goal":"Selectors, DOM, events, effects, AJAX, forms and modern integration"},
{"order":5,"topic":"Web fundamentals","goal":"HTTP/HTTPS, URLs, DNS, cookies, sessions, headers, status codes, JSON and REST"},
{"order":6,"topic":"PHP syntax and execution","goal":"Syntax, variables, types, arrays, functions, CLI and web execution"},
{"order":7,"topic":"PHP control flow and functions","goal":"Conditions, loops, scope, closures, generators, exceptions and errors"},
{"order":8,"topic":"PHP OOP","goal":"Classes, interfaces, traits, inheritance, namespaces and dependency injection"},
{"order":9,"topic":"Composer and PSR","goal":"Composer, autoloading, PSR standards, semantic versioning and packages"},
{"order":10,"topic":"PHP HTTP and web programming","goal":"Requests, responses, routing, forms, sessions, cookies, uploads and authentication"},
{"order":11,"topic":"SQL fundamentals for PHP","goal":"Relational modeling, CRUD, joins, aggregation, constraints and transactions"},
{"order":12,"topic":"MySQL with PHP","goal":"PDO, prepared statements, schema design, indexes, transactions and optimization"},
{"order":13,"topic":"PostgreSQL with PHP","goal":"PDO, PostgreSQL types, indexes, transactions and production integration"},
{"order":14,"topic":"SQLite with PHP","goal":"PDO, files, transactions, indexes, migrations and embedded databases"},
{"order":15,"topic":"SQL Server with PHP","goal":"PDO drivers, T-SQL integration, schemas, transactions and optimization"},
{"order":16,"topic":"PHP architecture","goal":"MVC, layered architecture, services, repositories, dependency injection and configuration"},
{"order":17,"topic":"PHP frameworks","goal":"Laravel routing, controllers, middleware, validation, ORM, queues and application structure"},
{"order":18,"topic":"Frontend integration","goal":"PHP with HTML/CSS/JS/jQuery, AJAX/fetch, JSON APIs and progressive enhancement"},
{"order":19,"topic":"Authentication and authorization","goal":"Sessions, password hashing, roles, permissions, OAuth concepts and JWT"},
{"order":20,"topic":"Web security","goal":"OWASP, XSS, SQL injection, CSRF, SSRF, file upload security, secrets and secure headers"},
{"order":21,"topic":"PHP testing and quality","goal":"PHPUnit, integration tests, static analysis, code style, debugging and logging"},
{"order":22,"topic":"Production PHP","goal":"Nginx/Apache, PHP-FPM, environment configuration, caching, queues, workers, monitoring and deployment"},
{"order":23,"topic":"Performance and scalability","goal":"OPcache, database optimization, caching, profiling, concurrency and horizontal scaling"},
{"order":24,"topic":"Complete PHP project","goal":"Production-style CRUD site with frontend, API, authentication, database, tests and deployment"},
{"order":25,"topic":"Web application security testing","goal":"Threat modeling, secure test environments, vulnerability scanning, OWASP methodology and remediation"},
{"order":26,"topic":"PHP security testing lab","goal":"Test the completed PHP project for XSS, SQL injection, CSRF, authentication, authorization, SSRF, uploads and session weaknesses using safe local labs"}
]

JAVASCRIPT_CURRICULUM=[{"order":1,"topic":"JavaScript fundamentals","goal":"Syntax, variables, values and expressions"},{"order":2,"topic":"Control flow and functions","goal":"Conditions, loops, functions and scope"},{"order":3,"topic":"Objects and arrays","goal":"Objects, arrays, destructuring and iteration"},{"order":4,"topic":"Modules","goal":"ES modules, imports, exports and package management"},{"order":5,"topic":"Async JavaScript","goal":"Promises, async/await and event loops"},{"order":6,"topic":"Web APIs","goal":"DOM, fetch, storage and browser events"},{"order":7,"topic":"Node.js","goal":"Node runtime, filesystem, HTTP and processes"},{"order":8,"topic":"Testing and production","goal":"Testing, security, performance and deployment"}]
SQLSERVER_CURRICULUM=[{"order":1,"topic":"SQL Server fundamentals","goal":"Architecture, databases, schemas, SSMS and connections"},{"order":2,"topic":"T-SQL basics","goal":"SELECT, INSERT, UPDATE, DELETE, filtering and sorting"},{"order":3,"topic":"Joins and subqueries","goal":"Joins, subqueries and set operations"},{"order":4,"topic":"Data modeling","goal":"Tables, keys, constraints, normalization and relationships"},{"order":5,"topic":"Indexes","goal":"Clustered, nonclustered, composite indexes and performance"},{"order":6,"topic":"Transactions and concurrency","goal":"Transactions, isolation, locks and deadlocks"},{"order":7,"topic":"Views procedures and functions","goal":"Views, stored procedures, functions and triggers"},{"order":8,"topic":"Security and administration","goal":"Users, roles, permissions, backups and recovery"},{"order":9,"topic":"Query optimization","goal":"Execution plans, statistics and performance tuning"},{"order":10,"topic":"Application integration","goal":"SQL Server access from Python, PHP, JavaScript and mobile backends"}]
MYSQL_CURRICULUM=[{"order":1,"topic":"MySQL fundamentals","goal":"Server, databases, schemas, clients and connections"},{"order":2,"topic":"SQL basics","goal":"SELECT, INSERT, UPDATE, DELETE, filtering and sorting"},{"order":3,"topic":"Joins and subqueries","goal":"Joins, subqueries, unions and aggregation"},{"order":4,"topic":"Data modeling","goal":"Tables, keys, constraints, normalization and relationships"},{"order":5,"topic":"Indexes and storage engines","goal":"Indexes, InnoDB and query performance"},{"order":6,"topic":"Transactions","goal":"Transactions, isolation, locking and consistency"},{"order":7,"topic":"Views routines and triggers","goal":"Views, procedures, functions and triggers"},{"order":8,"topic":"Security and backup","goal":"Users, privileges, backups and recovery"},{"order":9,"topic":"Optimization","goal":"EXPLAIN, indexes, statistics and performance tuning"},{"order":10,"topic":"Application integration","goal":"MySQL access from Python, PHP, JavaScript and mobile backends"}]
SQLITE_CURRICULUM=[{"order":1,"topic":"SQLite fundamentals","goal":"Embedded database architecture, files, connections and CLI"},{"order":2,"topic":"SQLite SQL","goal":"Tables, CRUD, filtering, sorting and aggregation"},{"order":3,"topic":"Relationships and constraints","goal":"Keys, foreign keys, constraints and normalization"},{"order":4,"topic":"Indexes and query planning","goal":"Indexes, EXPLAIN QUERY PLAN and performance"},{"order":5,"topic":"Transactions","goal":"Transactions, WAL, locking and concurrency"},{"order":6,"topic":"SQLite features","goal":"CTEs, window functions, JSON and full-text search"},{"order":7,"topic":"Application integration","goal":"SQLite with Python, PHP, JavaScript, Android and iOS"},{"order":8,"topic":"Reliability and deployment","goal":"Migrations, backups, corruption handling and production practices"}]
ANDROID_CURRICULUM=[{"order":1,"topic":"Android platform fundamentals","goal":"Architecture, SDK, projects, Gradle and Android Studio"},{"order":2,"topic":"Kotlin for Android","goal":"Syntax, null safety, classes, collections and coroutines"},{"order":3,"topic":"UI with Jetpack Compose","goal":"Composable UI, state, layouts, navigation and Material"},{"order":4,"topic":"Android app architecture","goal":"ViewModel, lifecycle, repositories and unidirectional data flow"},{"order":5,"topic":"Networking","goal":"HTTP APIs, JSON, Retrofit and error handling"},{"order":6,"topic":"Local databases","goal":"SQLite, Room, entities, DAOs, migrations and transactions"},{"order":7,"topic":"Security and permissions","goal":"Permissions, secure storage, authentication and networking security"},{"order":8,"topic":"Testing and release","goal":"Unit/UI tests, debugging, signing, builds and release"}]
IOS_CURRICULUM=[{"order":1,"topic":"iOS platform fundamentals","goal":"iOS SDK, Xcode, projects, simulators and app lifecycle"},{"order":2,"topic":"Swift for iOS","goal":"Syntax, optionals, structs, classes, protocols and concurrency"},{"order":3,"topic":"SwiftUI","goal":"Views, state, navigation, lists and reusable components"},{"order":4,"topic":"iOS app architecture","goal":"Observable state, lifecycle and data flow"},{"order":5,"topic":"Networking","goal":"URLSession, HTTP APIs, JSON decoding and errors"},{"order":6,"topic":"Local databases","goal":"Core Data, SQLite, persistence, migrations and transactions"},{"order":7,"topic":"Security and permissions","goal":"Keychain, permissions, privacy and secure networking"},{"order":8,"topic":"Testing and release","goal":"Unit/UI tests, debugging, signing, archives and release"}]

RUST_CURRICULUM=[
{"order":1,"topic":"Rust fundamentals","goal":"Toolchain, Cargo, variables, mutability, expressions, functions and control flow"},
{"order":2,"topic":"Ownership","goal":"Ownership rules, moves, copies, borrowing and resource-oriented programming"},
{"order":3,"topic":"References and borrowing","goal":"Shared and mutable references, borrowing rules, slices and aliasing"},
{"order":4,"topic":"Structs and enums","goal":"Data modeling, methods, associated functions, enums and pattern matching"},
{"order":5,"topic":"Collections","goal":"Vec, String, HashMap, iterators and collection ownership"},
{"order":6,"topic":"Error handling","goal":"Option, Result, ? operator, custom errors and recovery design"},
{"order":7,"topic":"Generics and traits","goal":"Generic types, trait bounds, associated types and trait objects"},
{"order":8,"topic":"Lifetimes","goal":"Lifetime parameters, elision, variance concepts and designing borrowed APIs"},
{"order":9,"topic":"Modules and crates","goal":"Modules, visibility, workspaces, crates, Cargo manifests and dependencies"},
{"order":10,"topic":"Iterators and closures","goal":"Iterator adapters, ownership in closures, combinators and lazy pipelines"},
{"order":11,"topic":"Smart pointers","goal":"Box, Rc, Arc, RefCell, interior mutability and ownership trade-offs"},
{"order":12,"topic":"Concurrency","goal":"Threads, channels, Send, Sync, Arc, Mutex and safe shared state"},
{"order":13,"topic":"Async Rust","goal":"Futures, async/await, runtimes, cancellation, streams and structured concurrency"},
{"order":14,"topic":"Testing","goal":"Unit, integration, documentation and property-oriented testing"},
{"order":15,"topic":"Macros","goal":"Declarative macros, procedural macro concepts, derive and macro hygiene"},
{"order":16,"topic":"Unsafe Rust","goal":"Unsafe boundaries, raw pointers, invariants, FFI and safe abstractions"},
{"order":17,"topic":"FFI and systems programming","goal":"C interoperability, ABI, linking, OS APIs and resource ownership across boundaries"},
{"order":18,"topic":"Networking and services","goal":"TCP/HTTP, TLS concepts, clients, servers, serialization and resilient services"},
{"order":19,"topic":"Databases","goal":"SQL access, connection pooling, transactions, migrations and query safety"},
{"order":20,"topic":"Performance engineering","goal":"Benchmarking, profiling, allocation analysis, zero-copy design and optimization"},
{"order":21,"topic":"Rust security","goal":"Memory safety, dependency auditing, secrets, input validation and threat modeling"},
{"order":22,"topic":"Compiler and type-system concepts","goal":"Type checking, monomorphization, borrow checking and implementation-aware reasoning"},
{"order":23,"topic":"Advanced lifetimes and type design","goal":"Higher-ranked trait bounds, GATs, associated types and advanced API design"},
{"order":24,"topic":"Advanced traits and dispatch","goal":"Object safety, dynamic dispatch, specialization concepts and static versus dynamic trade-offs"},
{"order":25,"topic":"Pinning and self-referential patterns","goal":"Pin, Unpin, projection concepts and safe asynchronous state machines"},
{"order":26,"topic":"Production architecture","goal":"Configuration, observability, resilience, graceful shutdown, deployment and operations"},
{"order":27,"topic":"Cargo and release engineering","goal":"Workspaces, features, profiles, reproducible builds, CI and packaging"},
{"order":28,"topic":"Real-project code reading","goal":"Trace unfamiliar Rust repositories, dependencies, invariants, ownership and failure paths"},
{"order":29,"topic":"Bug fixing and refactoring","goal":"Reproduce defects, preserve invariants, add regression tests and refactor safely"},
{"order":30,"topic":"Expert Rust capstone","goal":"Build, test, secure, benchmark and deploy a production-style Rust service"}
]

PENTEST_CURRICULUM=[
{"order":1,"topic":"Security fundamentals","goal":"CIA, threat modeling, attack surface, trust boundaries and secure development lifecycle"},
{"order":2,"topic":"Linux and networking for security","goal":"Processes, permissions, TCP/IP, DNS, HTTP, TLS, ports and service enumeration concepts"},
{"order":3,"topic":"Web security foundations","goal":"OWASP methodology, authentication, authorization, sessions, input validation and common web vulnerabilities"},
{"order":4,"topic":"Reconnaissance and asset discovery","goal":"Safe asset inventory, passive reconnaissance, service identification and evidence collection in authorized labs"},
{"order":5,"topic":"Vulnerability assessment","goal":"Risk-based scanning, validation, false positives, severity and remediation evidence"},
{"order":6,"topic":"Web application security testing","goal":"XSS, SQL injection, CSRF, SSRF, file upload, access control and session testing in local labs"},
{"order":7,"topic":"API security testing","goal":"REST/JSON APIs, authentication, authorization, input validation, rate limits and common API risks"},
{"order":8,"topic":"Secure code review","goal":"Find security flaws in PHP, Python, JavaScript and SQL code and propose fixes"},
{"order":9,"topic":"Security testing tools","goal":"Use scanners, proxies and packet-analysis tools against intentionally vulnerable local targets"},
{"order":10,"topic":"Reporting and remediation","goal":"Reproduce findings safely, document impact, recommend fixes and retest remediation"},
{"order":11,"topic":"PHP project penetration-test lab","goal":"Run an authorized end-to-end security assessment of the learned PHP project in an isolated local environment"}
]

LANGUAGE_CURRICULA={"Python":PYTHON_CURRICULUM,"Rust":RUST_CURRICULUM,"C":C_CURRICULUM,"PHP":PHP_CURRICULUM,"JavaScript":JAVASCRIPT_CURRICULUM,"SQL Server":SQLSERVER_CURRICULUM,"MySQL":MYSQL_CURRICULUM,"SQLite":SQLITE_CURRICULUM,"Android":ANDROID_CURRICULUM,"iOS":IOS_CURRICULUM,"Pentest":PENTEST_CURRICULUM}
LANGUAGE_ALIASES={"python":"Python","rust":"Rust","rs":"Rust","راست":"Rust","py":"Python","پایتون":"Python","c":"C","سی":"C","php":"PHP","پی اچ پی":"PHP","javascript":"JavaScript","js":"JavaScript","جاوااسکریپت":"JavaScript","sqlserver":"SQL Server","sql server":"SQL Server","mssql":"SQL Server","sql سرور":"SQL Server","mysql":"MySQL","مای اس کیو ال":"MySQL","sqlite":"SQLite","sql lite":"SQLite","android":"Android","اندروید":"Android","ios":"iOS","i os":"iOS","آی او اس":"iOS","pentest":"Pentest","pen test":"Pentest","penetration testing":"Pentest","penetration test":"Pentest","پنتست":"Pentest","پن تست":"Pentest","تست نفوذ":"Pentest","امنیت":"Pentest","cisco":"Cisco","سیسکو":"Cisco"}

LANGUAGE_SOURCES={"Python":["https://docs.python.org/3/","https://docs.python.org/3/tutorial/","https://docs.python.org/3/library/","https://docs.python.org/3/reference/","https://docs.python.org/3/howto/","https://docs.python.org/3/whatsnew/","https://packaging.python.org/en/latest/","https://packaging.python.org/en/latest/tutorials/","https://packaging.python.org/en/latest/guides/","https://peps.python.org/","https://devguide.python.org/"],"C":["https://en.cppreference.com/w/c","https://www.gnu.org/software/gnu-c-manual/","https://www.open-std.org/jtc1/sc22/wg14/","https://clang.llvm.org/docs/","https://gcc.gnu.org/onlinedocs/"],"PHP":["https://www.php.net/manual/en/","https://www.php.net/releases/","https://getcomposer.org/doc/","https://laravel.com/docs","https://symfony.com/doc/current/","https://developer.mozilla.org/en-US/docs/Web/HTML","https://developer.mozilla.org/en-US/docs/Web/CSS","https://developer.mozilla.org/en-US/docs/Web/JavaScript"],"JavaScript":["https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide","https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference","https://developer.mozilla.org/en-US/docs/Web/API","https://tc39.es/ecma262/","https://nodejs.org/docs/latest/api/","https://nodejs.org/en/learn/"],"SQL Server":["https://learn.microsoft.com/en-us/sql/sql-server/","https://learn.microsoft.com/en-us/sql/t-sql/","https://learn.microsoft.com/en-us/sql/relational-databases/","https://learn.microsoft.com/en-us/sql/database-engine/","https://learn.microsoft.com/en-us/sql/connect/"],"MySQL":["https://dev.mysql.com/doc/","https://dev.mysql.com/doc/refman/8.4/en/","https://dev.mysql.com/doc/mysql-security-excerpt/8.4/en/","https://dev.mysql.com/doc/connector-python/en/"],"SQLite":["https://www.sqlite.org/docs.html","https://www.sqlite.org/lang.html","https://www.sqlite.org/c3ref/intro.html","https://www.sqlite.org/security.html","https://www.sqlite.org/changes.html"],"Android":["https://source.android.com/docs","https://kotlinlang.org/docs/home.html","https://kotlinlang.org/docs/coroutines-overview.html","https://developer.android.com/guide","https://developer.android.com/kotlin"],"iOS":["https://developer.apple.com/tutorials/swiftui","https://developer.apple.com/documentation/swift","https://developer.apple.com/documentation/swiftui","https://developer.apple.com/documentation/xcode","https://developer.apple.com/documentation/security"],"Pentest":["https://owasp.org/www-project-web-security-testing-guide/","https://owasp.org/www-project-top-ten/","https://portswigger.net/web-security","https://nmap.org/book/","https://cheatsheetseries.owasp.org/","https://cwe.mitre.org/","https://attack.mitre.org/"],"Rust":["https://www.rust-lang.org/learn","https://doc.rust-lang.org/book/","https://doc.rust-lang.org/reference/","https://doc.rust-lang.org/cargo/","https://doc.rust-lang.org/std/","https://rust-lang.github.io/async-book/","https://rust-lang.github.io/nomicon/","https://rust-lang.github.io/rust-clippy/"]}

from .forex_curriculum import FOREX_CURRICULUM, FOREX_SOURCES, FOREX_ALIASES

LANGUAGE_CURRICULA["Forex"] = FOREX_CURRICULUM
LANGUAGE_ALIASES.update(FOREX_ALIASES)
LANGUAGE_SOURCES["Forex"] = FOREX_SOURCES

# Extend the existing curriculum without renaming or deleting any old topic.
from .advanced_curriculum import extend_curricula
extend_curricula(LANGUAGE_CURRICULA)

def curriculum(language): return LANGUAGE_CURRICULA.get(canonical_language(language),[])
def canonical_language(language):
    raw=language.strip()
    for name in LANGUAGE_CURRICULA:
        if name.lower()==raw.lower(): return name
    return LANGUAGE_ALIASES.get(raw.lower(),raw)
def next_topic(language="Python",completed=None):
    if isinstance(language,set) and completed is None: completed=language; language="Python"
    completed=completed or set()
    return next((x for x in curriculum(language) if str(x["topic"]) not in completed),None)
def source_urls(language): return LANGUAGE_SOURCES.get(canonical_language(language),[])

def resolve_learning_target(message):
    """Resolve an explicit learning request without matching C inside ordinary words."""
    text = str(message).strip()
    match = re.match(r"^\s*learn(?:\s+about)?\s+(.+?)\s*$", text, re.IGNORECASE)
    if not match:
        return text
    target = match.group(1).strip()
    if target.casefold() in {"c", "c language", "سی"}:
        return "C"
    return target
