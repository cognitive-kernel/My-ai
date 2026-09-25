from __future__ import annotations

# Additional expert-level units. Existing topic names are intentionally preserved so
# completed learning sessions remain valid after this expansion.
PYTHON_ADVANCED = [
    (17, "Python data model", "Object protocol, special methods, attribute lookup, equality, hashing and iteration"),
    (18, "Descriptors", "Descriptor protocol, properties, __get__, __set__, __delete__ and managed attributes"),
    (19, "Metaclasses and class creation", "type, __new__, __init_subclass__, metaclasses and class customization"),
    (20, "MRO and multiple inheritance", "C3 linearization, super(), cooperative inheritance and mixins"),
    (21, "Advanced functions and closures", "Callable objects, closure cells, partials, higher-order functions and signatures"),
    (22, "Iterators and generators", "Iterator protocol, yield, send, throw, close and generator pipelines"),
    (23, "Context managers", "with protocol, contextlib, ExitStack and exception-safe resource handling"),
    (24, "Advanced typing", "ParamSpec, TypeVar, TypeVarTuple, Protocol, overload, TypedDict and type narrowing"),
    (25, "Asyncio internals", "Event loop, tasks, cancellation, timeouts, queues, synchronization and structured concurrency"),
    (26, "Concurrency", "Threads, processes, executors, synchronization, race conditions and safe parallelism"),
    (27, "Networking and sockets", "TCP/UDP sockets, TLS concepts, framing, timeouts and resilient network clients"),
    (28, "Subprocess and OS integration", "Process lifecycle, pipes, signals, environment and safe command execution"),
    (29, "Import system", "Import machinery, finders, loaders, module specs, namespace packages and import hooks"),
    (30, "Packaging and distribution", "pyproject.toml, wheels, sdists, dependency resolution, publishing and reproducibility"),
    (31, "Testing at scale", "pytest architecture, fixtures, parametrization, mocks, property testing and regression suites"),
    (32, "Debugging and profiling", "tracebacks, pdb, logging, cProfile, tracemalloc and performance diagnosis"),
    (33, "Memory management", "References, refcounting, garbage collection, weak references and memory leaks"),
    (34, "CPython and bytecode", "Interpreter pipeline, bytecode, frames, compilation and implementation-aware optimization"),
    (35, "Python security", "Injection risks, unsafe deserialization, secrets, dependency risks, sandbox boundaries and hardening"),
    (36, "Production architecture", "Configuration, dependency injection, observability, resilience, graceful shutdown and deployment"),
    (37, "Real-project code reading", "Trace unfamiliar Python repositories, map dependencies, identify invariants and locate defects"),
    (38, "Bug fixing and refactoring", "Reproduce defects, make minimal fixes, preserve behavior and add regression tests"),
    (39, "Performance engineering", "Benchmark design, algorithmic complexity, I/O bottlenecks, caching and profiling-driven optimization"),
    (40, "Expert Python capstone", "Build, test, debug, secure and profile a production-style Python service"),
]

SQLSERVER_ADVANCED = [
    (11, "Advanced T-SQL", "CTEs, window functions, APPLY, PIVOT, set operators and advanced expressions"),
    (12, "Stored procedures and programmable objects", "Procedures, functions, triggers, parameters, error handling and deployment"),
    (13, "Execution plans", "Estimated versus actual plans, operators, cardinality and plan diagnosis"),
    (14, "Statistics and cardinality estimation", "Statistics objects, histograms, estimation errors and maintenance"),
    (15, "Advanced indexing", "Covering, filtered, included-column, columnstore and index design tradeoffs"),
    (16, "Advanced query optimization", "SARGability, joins, parameter sensitivity, hints and evidence-based tuning"),
    (17, "Transactions and isolation", "ACID, isolation levels, row versioning, locks and blocking"),
    (18, "Deadlocks and concurrency diagnosis", "Deadlock graphs, blocking chains, wait analysis and remediation"),
    (19, "TempDB and temporary objects", "Temp tables, table variables, version store and TempDB contention"),
    (20, "SQL Server security", "Logins, users, roles, ownership chaining, encryption and least privilege"),
    (21, "Backup and restore", "Full, differential, log backups, recovery models and point-in-time recovery"),
    (22, "High availability and disaster recovery", "Always On concepts, failover, RPO/RTO and recovery planning"),
    (23, "Monitoring and diagnostics", "DMVs, Query Store, Extended Events, waits and operational telemetry"),
    (24, "Database design at scale", "Partitioning, compression, temporal data, constraints and schema evolution"),
    (25, "SQL Server on Linux and containers", "Deployment, configuration, persistence, networking and operational differences"),
    (26, "Application connectivity", "Connection pooling, parameterization, transactions and driver behavior from applications"),
    (27, "SQL Server performance engineering", "Workload baselines, bottleneck isolation, benchmarking and regression prevention"),
    (28, "Migration and version upgrades", "Compatibility levels, migrations, rollback plans and upgrade validation"),
    (29, "Database troubleshooting", "Reproduce failures, inspect errors, isolate root causes and verify fixes"),
    (30, "SQL Server expert capstone", "Design, optimize, secure, monitor, back up and troubleshoot a production-style database"),
]


C_ADVANCED=[
(11,"C preprocessor and macros","Macro expansion, conditional compilation, include guards and safe macro design"),
(12,"C undefined behavior","Integer overflow, strict aliasing, lifetime rules, sequencing and defensive coding"),
(13,"Advanced pointers","Function pointers, pointer-to-pointer, opaque pointers and callback design"),
(14,"Memory debugging lab","AddressSanitizer, UndefinedBehaviorSanitizer, Valgrind concepts and leak diagnosis"),
(15,"POSIX systems programming","Processes, signals, file descriptors, pipes and process lifecycle"),
(16,"Threads and synchronization","pthreads, mutexes, condition variables, atomics and race diagnosis"),
(17,"C build engineering","Make, CMake concepts, compiler/linker flags and reproducible builds"),
(18,"C networking","Sockets, TCP/UDP, framing, timeouts and resilient clients"),
(19,"C security engineering","Input validation, memory safety boundaries, privilege separation and hardening"),
(20,"Expert C capstone","Build, test, debug, secure and profile a production-style C service"),
]
PHP_ADVANCED=[
(27,"Modern PHP language internals","Attributes, enums, readonly properties, fibers, generators and modern type features"),
(28,"PHP runtime internals","Zend Engine concepts, opcode cache, memory model and request lifecycle"),
(29,"Advanced Composer","Dependency constraints, autoloading, scripts, repositories, lockfiles and supply-chain hygiene"),
(30,"Advanced Laravel architecture","Service container, events, queues, policies, jobs, caching and domain boundaries"),
(31,"Advanced API engineering","Versioning, pagination, idempotency, validation, rate limits and error contracts"),
(32,"PHP observability","Structured logging, metrics, tracing, health checks and incident diagnostics"),
(33,"PHP performance lab","Profiling, OPcache, database bottlenecks, caching and load-test interpretation"),
(34,"PHP security engineering","Secure sessions, SSRF defenses, upload isolation, secrets and dependency auditing"),
(35,"PHP production operations","Workers, queues, deployment, migrations, rollback and configuration management"),
(36,"Expert PHP capstone","Design, secure, test, optimize and deploy a production-style PHP application"),
]
JAVASCRIPT_ADVANCED=[
(9,"JavaScript runtime internals","Execution contexts, closures, prototypes, garbage collection and event-loop behavior"),
(10,"Advanced async patterns","Cancellation, concurrency limits, retries, timeouts and backpressure"),
(11,"Browser performance","Rendering, layout, paint, memory, profiling and performance budgets"),
(12,"Web security engineering","XSS, CSP, CSRF, prototype pollution, trusted types and secure DOM handling"),
(13,"Node.js internals","Streams, buffers, worker threads, child processes and runtime diagnostics"),
(14,"Advanced TypeScript concepts","Structural typing, generics, conditional types and API design"),
(15,"Frontend architecture","State management, component boundaries, code splitting and progressive enhancement"),
(16,"Testing at scale","Unit, integration, browser, contract and regression testing"),
(17,"Production JavaScript","Observability, deployment, caching, resilience and dependency management"),
(18,"Expert JavaScript capstone","Build, test, secure, profile and deploy a production-style web service"),
]
MYSQL_ADVANCED=[
(11,"Advanced MySQL SQL","CTEs, window functions, recursive queries and advanced aggregation"),
(12,"MySQL optimizer","EXPLAIN, EXPLAIN ANALYZE, cost estimates and query-plan diagnosis"),
(13,"Advanced indexing","Composite, covering, functional and invisible indexes with workload trade-offs"),
(14,"InnoDB internals","Buffer pool, redo/undo, MVCC, clustered indexes and durability"),
(15,"Locking and deadlocks","Isolation, row locks, gap locks, deadlock diagnosis and retry strategies"),
(16,"Replication and high availability","Replication concepts, failover, consistency and recovery planning"),
(17,"MySQL security","Accounts, privileges, TLS, secrets, auditing and least privilege"),
(18,"Backup and recovery lab","Logical/physical backup concepts, restore validation and recovery objectives"),
(19,"Production troubleshooting","Slow queries, waits, resource saturation and evidence-driven diagnosis"),
(20,"Expert MySQL capstone","Design, secure, optimize, back up and operate a production-style database"),
]
SQLITE_ADVANCED=[
(9,"SQLite internals","B-trees, pages, journaling, WAL and storage architecture"),
(10,"Query planner internals","EXPLAIN QUERY PLAN, statistics, indexes and planner behavior"),
(11,"Advanced SQLite SQL","CTEs, recursive queries, window functions, JSON and FTS"),
(12,"Concurrency engineering","WAL, busy handling, transactions and multi-process access"),
(13,"Schema migration engineering","Versioned migrations, compatibility, rollback and data preservation"),
(14,"SQLite security","File permissions, extension loading, trusted inputs and encryption boundaries"),
(15,"Reliability and corruption diagnosis","Integrity checks, backup strategy, recovery and failure analysis"),
(16,"SQLite performance lab","Indexes, batching, prepared statements, profiling and benchmark design"),
(17,"Application architecture","Repositories, transactions, connection lifecycle and test isolation"),
(18,"Expert SQLite capstone","Build, test, migrate, secure and optimize a production-style embedded database"),
]
ANDROID_ADVANCED=[
(9,"Android runtime internals","Processes, threads, lifecycle behavior, memory pressure and configuration changes"),
(10,"Advanced Compose","Recomposition, stability, side effects, custom layouts and performance"),
(11,"Coroutines and structured concurrency","Scopes, cancellation, dispatchers, flows and lifecycle-aware concurrency"),
(12,"Advanced architecture","Domain boundaries, state machines, offline-first design and dependency injection"),
(13,"Advanced networking","Caching, retries, pagination, authentication refresh and resilient API clients"),
(14,"Android security engineering","Keystore, secure storage, exported components, WebView and network security"),
(15,"Android performance lab","Profiling, rendering, memory leaks, startup and battery optimization"),
(16,"Advanced testing","Unit, integration, UI, screenshot and end-to-end testing strategies"),
(17,"Release engineering","Signing, flavors, CI/CD, crash monitoring and staged rollout concepts"),
(18,"Expert Android capstone","Build, secure, test, profile and release a production-style Android app"),
]
IOS_ADVANCED=[
(9,"iOS runtime and lifecycle","Processes, scenes, memory pressure, background execution and lifecycle behavior"),
(10,"Advanced Swift concurrency","actors, tasks, cancellation, async sequences and isolation"),
(11,"Advanced SwiftUI","View identity, rendering, state ownership, navigation and performance"),
(12,"Architecture at scale","Feature modules, dependency boundaries, state management and testability"),
(13,"Advanced networking","URLSession configuration, caching, retries, authentication and resilience"),
(14,"iOS security engineering","Keychain, App Transport Security, entitlements, secure storage and privacy"),
(15,"Performance and Instruments","Time Profiler, allocations, leaks, rendering and startup analysis"),
(16,"Advanced testing","Unit, UI, integration, snapshot and deterministic async testing"),
(17,"Release engineering","Signing, provisioning, archives, CI/CD and staged release practices"),
(18,"Expert iOS capstone","Build, secure, test, profile and release a production-style iOS app"),
]
PENTEST_ADVANCED=[
(12,"Threat modeling workshop","Assets, trust boundaries, abuse cases, attack paths and risk evidence"),
(13,"Advanced web testing","Access control, business logic, request smuggling concepts and chained findings in authorized labs"),
(14,"API security lab","JWT/session flaws, object authorization, rate limits, mass assignment and schema validation"),
(15,"Authentication testing","Credential flows, MFA, password reset, session lifecycle and token handling"),
(16,"Client-side security testing","DOM XSS, CSP, prototype pollution and browser trust boundaries"),
(17,"Network security assessment","Service enumeration, TLS review, segmentation and safe validation"),
(18,"Secure code review lab","Trace data flow, identify sinks, validate exploitability and propose minimal fixes"),
(19,"Automation and evidence","Repeatable checks, test harnesses, evidence capture and false-positive reduction"),
(20,"Professional reporting","Executive summary, technical reproduction, severity rationale, remediation and retest"),
(21,"Expert pentest capstone","Assess an intentionally vulnerable local system from scope through retest"),
]


def _extend(target, additions):
    existing = {str(x["topic"]) for x in target}
    for order, topic, goal in additions:
        if topic not in existing:
            target.append({"order": order, "topic": topic, "goal": goal})


RUST_ADVANCED=[
(31,"Rust compiler diagnostics and MIR","Compiler errors, HIR/MIR concepts, diagnostics and implementation-aware debugging"),
(32,"Advanced trait system","Trait coherence, orphan rules, blanket implementations, associated types and advanced bounds"),
(33,"Higher-ranked lifetimes","for<'a> bounds, lifetime abstraction and callback APIs"),
(34,"Generic associated types","GAT design, lending-style APIs and advanced iterator abstractions"),
(35,"Async runtime internals","Executors, wakers, polling, task scheduling and cancellation semantics"),
(36,"Unsafe code auditing","Safety invariants, aliasing models, provenance concepts and reviewing unsafe blocks"),
(37,"FFI safety engineering","ABI contracts, ownership transfer, callbacks, error translation and panic boundaries"),
(38,"Zero-copy and serialization","Borrowed deserialization, lifetimes, memory layout and allocation-aware data formats"),
(39,"Distributed systems in Rust","Retries, idempotency, timeouts, backpressure, consistency and service boundaries"),
(40,"Production observability","Tracing, metrics, structured logs, health checks and incident diagnostics"),
(41,"Rust performance lab","Benchmarking, flamegraphs, allocation profiling and regression detection"),
(42,"Rust security lab","Dependency auditing, supply-chain controls, fuzzing concepts and hardened input boundaries"),
(43,"Advanced build systems","Cargo workspaces, feature matrices, cross compilation, reproducible builds and CI"),
(44,"Advanced Rust capstone","Design, implement, test, benchmark, secure and operate a multi-component Rust system"),
]

def _extend_rust(target):
    existing={str(x["topic"]) for x in target}
    for order,topic,goal in RUST_ADVANCED:
        if topic not in existing:
            target.append({"order":order,"topic":topic,"goal":goal})

UNIVERSAL_EXPERT_GATES=[
(90,"Advanced architecture and design","Decompose complex systems, choose trade-offs, document invariants and maintainability decisions"),
(91,"Advanced debugging and root-cause analysis","Reproduce failures, isolate root causes, inspect evidence and verify fixes"),
(92,"Security engineering","Threat modeling, secure defaults, input boundaries, secrets, dependency and supply-chain risks"),
(93,"Testing and verification","Unit, integration, regression, negative, property or end-to-end tests with measurable evidence"),
(94,"Performance engineering","Benchmark, profile, identify bottlenecks, optimize and verify regressions"),
(95,"Production operations","Deployment, configuration, observability, reliability, rollback and incident diagnosis"),
(96,"Real-project engineering","Read an unfamiliar repository, implement a feature, review changes and preserve existing behavior"),
(97,"Expert capstone and proficiency gate","Complete a substantial project from requirements through tests, security review, performance evidence and final technical review"),
]

def _extend_universal(target):
    existing={str(x["topic"]) for x in target}
    for order,topic,goal in UNIVERSAL_EXPERT_GATES:
        if topic not in existing:
            target.append({"order":order,"topic":topic,"goal":goal})

def extend_curricula(curricula):
    # Curricula with an explicit numbered expert track already have their own
    # authoritative endpoint. Do not append the generic gates on top of them;
    # doing so changes Python's 40-topic path into 48 and mixes unrelated
    # completion records into the selected subject.
    if "Python" in curricula:
        _extend(curricula["Python"], PYTHON_ADVANCED)
    if "SQL Server" in curricula:
        _extend(curricula["SQL Server"], SQLSERVER_ADVANCED)
    if "Rust" in curricula:
        _extend_rust(curricula["Rust"])
    explicit = {"Python", "SQL Server", "Rust", "Forex"}
    advanced_map = {
        "C": C_ADVANCED, "PHP": PHP_ADVANCED, "JavaScript": JAVASCRIPT_ADVANCED,
        "MySQL": MYSQL_ADVANCED, "SQLite": SQLITE_ADVANCED, "Android": ANDROID_ADVANCED,
        "iOS": IOS_ADVANCED, "Pentest": PENTEST_ADVANCED,
    }
    for name, additions in advanced_map.items():
        if name in curricula:
            _extend(curricula[name], additions)
    for name, target in curricula.items():
        if name not in explicit and name not in advanced_map:
            _extend_universal(target)


# Compact model-provided seed knowledge. It is a starting layer, not a substitute for
# versioned official documentation and executable verification.
KNOWLEDGE_SEED = {
    "Python": {
        "Python data model": "Python behavior is defined by protocols implemented through special methods. Attribute lookup, iteration, calling, comparison, hashing and context management are protocol-driven; robust code uses those protocols instead of relying on implementation accidents.",
        "Descriptors": "A descriptor is an object defining __get__, __set__ or __delete__. Descriptors power properties, methods and many ORM/framework abstractions. Non-data descriptors yield to instance attributes while data descriptors take precedence.",
        "Metaclasses and class creation": "Classes are objects created by a metaclass, normally type. __new__, __init_subclass__ and metaclasses can customize class creation; this power should be used only when simpler composition or decorators are insufficient.",
        "MRO and multiple inheritance": "Python uses C3 method resolution order. super() follows the computed MRO rather than simply calling a parent, enabling cooperative multiple inheritance when every class participates consistently.",
        "Iterators and generators": "Iteration follows __iter__ and __next__. Generators suspend execution at yield and can receive values with send(), exceptions with throw() and termination with close().",
        "Context managers": "The with statement delegates resource acquisition/release to __enter__/__exit__. contextlib supplies reusable helpers such as contextmanager and ExitStack for exception-safe resource management.",
        "Advanced typing": "Typing annotations describe intended interfaces. Protocol enables structural typing; ParamSpec preserves callable parameter types; TypedDict models dictionary shapes; static checking complements but does not replace runtime validation.",
        "Asyncio internals": "asyncio schedules coroutines as tasks on an event loop. Cancellation is cooperative; blocking synchronous work should not run directly on the event loop. Timeouts, queues and task groups help build bounded concurrent systems.",
        "Concurrency": "Threads are useful for I/O-bound work; processes provide separate interpreters and address CPU parallelism; executors abstract scheduling. Shared mutable state requires synchronization and careful ownership.",
        "Import system": "Imports resolve modules through finders and loaders and are represented by module specs. Import-time side effects should be minimized because importing is executable behavior.",
        "Packaging and distribution": "Modern Python packaging is described by pyproject.toml. Wheels and source distributions are artifacts; lock or constraint strategies improve reproducibility, while dependency ranges must account for compatibility and security updates.",
        "Testing at scale": "Reliable tests isolate behavior, use fixtures for controlled setup, parameterize equivalent cases and add regression tests for every discovered defect. Integration tests verify boundaries that unit tests cannot.",
        "Debugging and profiling": "Debugging starts with a reproducible failure and evidence. Profilers identify actual bottlenecks; optimization should follow measurement rather than intuition.",
        "Memory management": "CPython primarily uses reference counting plus cyclic garbage collection. Weak references avoid keeping objects alive unnecessarily; leaks often come from unintended object retention rather than a missing free().",
        "CPython and bytecode": "Python source is compiled to an internal code representation executed by the interpreter. Bytecode and interpreter details are implementation-specific, so optimization should preserve language-level semantics and be verified on the target runtime.",
        "Python security": "Treat input, deserialization, subprocesses and dependencies as trust boundaries. Prefer safe parsers, parameterization, least privilege, explicit allowlists and isolated execution over ad-hoc filtering.",
        "Bug fixing and refactoring": "A safe repair reproduces the bug, identifies the smallest root-cause change, adds a regression test, runs the relevant suite and preserves a rollback point.",
    },
    "SQL Server": {
        "Advanced T-SQL": "T-SQL extends relational SQL with constructs such as CTEs, window functions, APPLY and procedural features. Query logic should remain declarative where possible and be validated against expected cardinalities.",
        "Execution plans": "An execution plan describes operators chosen by the optimizer. Actual plans and runtime statistics provide evidence about scans, seeks, joins, memory grants and cardinality errors.",
        "Statistics and cardinality estimation": "Statistics summarize data distribution and guide cardinality estimates. Stale or unrepresentative statistics can cause poor plans, so diagnosis should compare estimates with actual row counts.",
        "Advanced indexing": "Indexes trade write/storage cost for read performance. Covering and filtered indexes can reduce I/O for specific workloads; columnstore targets analytical patterns and must be evaluated against workload characteristics.",
        "Query optimization": "Effective tuning starts from the workload and evidence: inspect plans, waits, I/O and row estimates; improve predicates, joins, indexes and statistics before reaching for hints.",
        "Transactions and isolation": "Transactions provide atomicity and consistency while isolation controls visibility and concurrency. Row-versioning and locking have different resource and contention implications.",
        "Deadlocks and concurrency diagnosis": "Deadlocks arise from cyclic resource dependencies. Deadlock graphs and wait information reveal the cycle; fixes generally reduce lock duration, improve access order or narrow transactions.",
        "SQL Server security": "Security should follow least privilege with separated logins, users and roles, controlled ownership, protected secrets and encryption where appropriate.",
        "Backup and restore": "Recovery planning combines recovery model, backup types and restore testing. A backup is only operationally useful when restoration has been validated against recovery objectives.",
        "Monitoring and diagnostics": "DMVs, Query Store and Extended Events provide complementary evidence for workload behavior, waits, regressions and failures.",
        "SQL Server performance engineering": "Performance work requires a baseline, a measured hypothesis, a controlled change and a post-change comparison to prevent regressions.",
    },
}


# Seed knowledge exists for every major learning domain. It is intentionally compact;
# the learner should combine it with the domain source set and verification exercises.
for _lang, _units in {
    "C": C_ADVANCED, "PHP": PHP_ADVANCED, "JavaScript": JAVASCRIPT_ADVANCED,
    "MySQL": MYSQL_ADVANCED, "SQLite": SQLITE_ADVANCED, "Android": ANDROID_ADVANCED,
    "iOS": IOS_ADVANCED, "Pentest": PENTEST_ADVANCED,
}.items():
    KNOWLEDGE_SEED.setdefault(_lang, {})
    for _order, _topic, _goal in _units:
        KNOWLEDGE_SEED[_lang].setdefault(
            _topic,
            f"{_topic}: {_goal}. Study the official references, implement a small example, test failure cases, inspect evidence, and record the trade-offs and security implications."
        )

def seed_for(language, topic):
    return KNOWLEDGE_SEED.get(language, {}).get(topic, "")
