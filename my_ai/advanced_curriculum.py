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
    (16, "Query optimization", "SARGability, joins, parameter sensitivity, hints and evidence-based tuning"),
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
(44,"Expert Rust capstone","Design, implement, test, benchmark, secure and operate a multi-component Rust system"),
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
    for _target in curricula.values():
        _extend_universal(_target)
    if "Python" in curricula:
        _extend(curricula["Python"], PYTHON_ADVANCED)
    if "SQL Server" in curricula:
        _extend(curricula["SQL Server"], SQLSERVER_ADVANCED)
    if "Rust" in curricula:
        _extend_rust(curricula["Rust"])


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


def seed_for(language, topic):
    return KNOWLEDGE_SEED.get(language, {}).get(topic, "")
