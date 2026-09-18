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
{"order":1,"topic":"HTML fundamentals","goal":"HTML5 document structure, semantic elements, forms, tables, media, accessibility and validation"},
{"order":2,"topic":"CSS fundamentals","goal":"Selectors, cascade, box model, layout, Flexbox, Grid, responsive design and media queries"},
{"order":3,"topic":"JavaScript fundamentals","goal":"Variables, types, functions, objects, arrays, DOM, events, modules, fetch, async/await and browser APIs"},
{"order":4,"topic":"jQuery","goal":"Selectors, DOM manipulation, events, effects, AJAX, forms and safe integration with modern JavaScript"},
{"order":5,"topic":"Web fundamentals","goal":"HTTP/HTTPS, URLs, DNS, cookies, sessions, headers, status codes, JSON, REST and browser/server architecture"},
{"order":6,"topic":"PHP syntax and execution","goal":"PHP tags, statements, variables, types, arrays, functions, CLI and web-server execution"},
{"order":7,"topic":"PHP control flow and functions","goal":"Conditions, loops, scope, closures, generators, exceptions and error handling"},
{"order":8,"topic":"PHP OOP","goal":"Classes, interfaces, traits, inheritance, namespaces, autoloading and dependency injection"},
{"order":9,"topic":"Composer and packages","goal":"Composer, PSR standards, autoloading, semantic versioning and package management"},
{"order":10,"topic":"PHP HTTP and web programming","goal":"Requests, responses, routing, forms, sessions, cookies, uploads, CSRF and authentication"},
{"order":11,"topic":"SQL fundamentals for PHP","goal":"Relational databases, CRUD, joins, aggregation, constraints, normalization and transactions"},
{"order":12,"topic":"MySQL with PHP","goal":"MySQL schema design, indexes, PDO, prepared statements, transactions, migrations and optimization"},
{"order":13,"topic":"PostgreSQL with PHP","goal":"PostgreSQL fundamentals, PDO, types, indexes, transactions and production integration"},
{"order":14,"topic":"SQLite with PHP","goal":"SQLite files, PDO, transactions, indexes, migrations and embedded application databases"},
{"order":15,"topic":"SQL Server with PHP","goal":"SQL Server/T-SQL integration through PDO drivers, schemas, transactions and query optimization"},
{"order":16,"topic":"PHP architecture","goal":"MVC, layered architecture, services, repositories, dependency injection and configuration"},
{"order":17,"topic":"PHP frameworks","goal":"Laravel fundamentals, routing, controllers, middleware, validation, ORM, queues and application structure"},
{"order":18,"topic":"Frontend integration","goal":"PHP with HTML/CSS/JavaScript/jQuery, AJAX/fetch, JSON APIs and progressive enhancement"},
{"order":19,"topic":"Authentication and authorization","goal":"Sessions, password hashing, roles, permissions, OAuth concepts, JWT and secure authentication flows"},
{"order":20,"topic":"Web security","goal":"OWASP risks, XSS, SQL injection, CSRF, SSRF, file upload security, secrets and secure headers"},
{"order":21,"topic":"Testing and quality","goal":"PHPUnit, integration tests, static analysis, code style, debugging and logging"},
{"order":22,"topic":"Production PHP","goal":"Nginx/Apache, PHP-FPM, environment configuration, caching, queues, workers, monitoring and deployment"},
{"order":23,"topic":"Performance and scalability","goal":"OPcache, database optimization, caching, profiling, concurrency and horizontal scaling"},
{"order":24,"topic":"Modern PHP web project","goal":"Build a complete production-style CRUD website with frontend, API, authentication, database, tests and deployment"}]
JAVASCRIPT_CURRICULUM=[
{"order":1,"topic":"JavaScript fundamentals","goal":"Syntax, variables, values and expressions"},
{"order":2,"topic":"Control flow and functions","goal":"Conditions, loops, functions and scope"},
{"order":3,"topic":"Objects and arrays","goal":"Objects, arrays, destructuring and iteration"},
{"order":4,"topic":"Modules","goal":"ES modules, imports, exports and package management"},
{"order":5,"topic":"Async JavaScript","goal":"Promises, async/await and event loops"},
{"order":6,"topic":"Web APIs","goal":"DOM, fetch, storage and browser events"},
{"order":7,"topic":"Node.js","goal":"Node runtime, filesystem, HTTP and processes"},
{"order":8,"topic":"Testing and production","goal":"Testing, security, performance and deployment"}]
SQLSERVER_CURRICULUM=[
{"order":1,"topic":"SQL Server fundamentals","goal":"SQL Server architecture, databases, schemas, SSMS and connections"},
{"order":2,"topic":"T-SQL basics","goal":"SELECT, INSERT, UPDATE, DELETE, filtering, sorting and aliases"},
{"order":3,"topic":"Joins and subqueries","goal":"INNER, LEFT, RIGHT joins, subqueries and set operations"},
{"order":4,"topic":"Data modeling","goal":"Tables, keys, constraints, normalization and relationships"},
{"order":5,"topic":"Indexes","goal":"Clustered, nonclustered, composite indexes and query performance"},
{"order":6,"topic":"Transactions and concurrency","goal":"Transactions, isolation levels, locks and deadlocks"},
{"order":7,"topic":"Views procedures and functions","goal":"Views, stored procedures, functions and triggers"},
{"order":8,"topic":"Security and administration","goal":"Users, roles, permissions, backups and recovery"},
{"order":9,"topic":"Query optimization","goal":"Execution plans, statistics and performance tuning"},
{"order":10,"topic":"Application integration","goal":"SQL Server access from Python, PHP, JavaScript and mobile backends"}]
MYSQL_CURRICULUM=[
{"order":1,"topic":"MySQL fundamentals","goal":"Server, databases, schemas, clients and connections"},
{"order":2,"topic":"SQL basics","goal":"SELECT, INSERT, UPDATE, DELETE, filtering and sorting"},
{"order":3,"topic":"Joins and subqueries","goal":"Joins, subqueries, unions and aggregation"},
{"order":4,"topic":"Data modeling","goal":"Tables, keys, constraints, normalization and relationships"},
{"order":5,"topic":"Indexes and storage engines","goal":"Indexes, InnoDB and query performance"},
{"order":6,"topic":"Transactions","goal":"Transactions, isolation, locking and consistency"},
{"order":7,"topic":"Views routines and triggers","goal":"Views, procedures, functions and triggers"},
{"order":8,"topic":"Security and backup","goal":"Users, privileges, backups and recovery"},
{"order":9,"topic":"Optimization","goal":"EXPLAIN, indexes, statistics and performance tuning"},
{"order":10,"topic":"Application integration","goal":"MySQL access from Python, PHP, JavaScript and mobile backends"}]
SQLITE_CURRICULUM=[
{"order":1,"topic":"SQLite fundamentals","goal":"Embedded database architecture, files, connections and CLI"},
{"order":2,"topic":"SQLite SQL","goal":"Tables, CRUD, filtering, sorting and aggregation"},
{"order":3,"topic":"Relationships and constraints","goal":"Keys, foreign keys, constraints and normalization"},
{"order":4,"topic":"Indexes and query planning","goal":"Indexes, EXPLAIN QUERY PLAN and performance"},
{"order":5,"topic":"Transactions","goal":"Transactions, WAL, locking and concurrency"},
{"order":6,"topic":"SQLite features","goal":"CTEs, window functions, JSON and full-text search"},
{"order":7,"topic":"Application integration","goal":"SQLite with Python, PHP, JavaScript, Android and iOS"},
{"order":8,"topic":"Reliability and deployment","goal":"Migrations, backups, corruption handling and production practices"}]
ANDROID_CURRICULUM=[
{"order":1,"topic":"Android platform fundamentals","goal":"Android architecture, SDK, projects, Gradle and Android Studio"},
{"order":2,"topic":"Kotlin for Android","goal":"Kotlin syntax, null safety, classes, collections and coroutines"},
{"order":3,"topic":"UI with Jetpack Compose","goal":"Composable UI, state, layouts, navigation and Material"},
{"order":4,"topic":"Android app architecture","goal":"ViewModel, lifecycle, repositories and unidirectional data flow"},
{"order":5,"topic":"Networking","goal":"HTTP APIs, JSON, Retrofit and error handling"},
{"order":6,"topic":"Local databases","goal":"SQLite, Room, entities, DAOs, migrations and transactions"},
{"order":7,"topic":"Security and permissions","goal":"App permissions, secure storage, authentication and networking security"},
{"order":8,"topic":"Testing and release","goal":"Unit/UI tests, debugging, signing, builds and Play release"}]
IOS_CURRICULUM=[
{"order":1,"topic":"iOS platform fundamentals","goal":"iOS SDK, Xcode, projects, simulators and app lifecycle"},
{"order":2,"topic":"Swift for iOS","goal":"Swift syntax, optionals, structs, classes, protocols and concurrency"},
{"order":3,"topic":"SwiftUI","goal":"Views, state, navigation, lists and reusable components"},
{"order":4,"topic":"iOS app architecture","goal":"Observable state, MVVM-style separation, lifecycle and data flow"},
{"order":5,"topic":"Networking","goal":"URLSession, HTTP APIs, JSON decoding and error handling"},
{"order":6,"topic":"Local databases","goal":"Core Data, SQLite, persistence, migrations and transactions"},
{"order":7,"topic":"Security and permissions","goal":"Keychain, app permissions, privacy and secure networking"},
{"order":8,"topic":"Testing and release","goal":"Unit/UI tests, debugging, signing, archives and App Store release"}]

LANGUAGE_CURRICULA={"Python":PYTHON_CURRICULUM,"C":C_CURRICULUM,"PHP":PHP_CURRICULUM,"JavaScript":JAVASCRIPT_CURRICULUM,"SQL Server":SQLSERVER_CURRICULUM,"MySQL":MYSQL_CURRICULUM,"SQLite":SQLITE_CURRICULUM,"Android":ANDROID_CURRICULUM,"iOS":IOS_CURRICULUM}
CURRICULA=LANGUAGE_CURRICULA
LANGUAGE_ALIASES={"python":"Python","py":"Python","پایتون":"Python","c":"C","سی":"C","php":"PHP","پی اچ پی":"PHP","javascript":"JavaScript","js":"JavaScript","جاوااسکریپت":"JavaScript","sqlserver":"SQL Server","sql server":"SQL Server","mssql":"SQL Server","sql سرور":"SQL Server","mysql":"MySQL","مای اس کیو ال":"MySQL","sqlite":"SQLite","sql lite":"SQLite","android":"Android","اندروید":"Android","ios":"iOS","i os":"iOS","آی او اس":"iOS"}
LANGUAGE_SOURCES={"Python":["https://docs.python.org/3/tutorial/","https://docs.python.org/3/library/"],"C":["https://en.cppreference.com/w/c","https://www.gnu.org/software/gnu-c-manual/"],"PHP":["https://www.php.net/manual/en/","https://www.php.net/docs.php","https://getcomposer.org/doc/","https://laravel.com/docs","https://developer.mozilla.org/en-US/docs/Web/HTML","https://developer.mozilla.org/en-US/docs/Web/CSS","https://developer.mozilla.org/en-US/docs/Web/JavaScript","https://api.jquery.com/"],"JavaScript":["https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide","https://developer.mozilla.org/en-US/docs/Web/API"],"SQL Server":["https://learn.microsoft.com/en-us/sql/sql-server/","https://learn.microsoft.com/en-us/sql/t-sql/"],"MySQL":["https://dev.mysql.com/doc/","https://dev.mysql.com/doc/refman/8.4/en/"],"SQLite":["https://www.sqlite.org/docs.html","https://www.sqlite.org/lang.html"],"Android":["https://developer.android.com/guide","https://developer.android.com/kotlin"],"iOS":["https://developer.apple.com/tutorials/swiftui","https://developer.apple.com/documentation/swift"]}
def curriculum(language):
    return LANGUAGE_CURRICULA.get(canonical_language(language),[])
def canonical_language(language):
    raw=language.strip()
    for name in LANGUAGE_CURRICULA:
        if name.lower()==raw.lower(): return name
    return LANGUAGE_ALIASES.get(raw.lower(),raw)
def next_topic(language="Python",completed=None):
    if isinstance(language,set) and completed is None: completed=language; language="Python"
    completed=completed or set()
    return next((x for x in curriculum(language) if str(x["topic"]) not in completed),None)
def source_urls(language):
    return LANGUAGE_SOURCES.get(canonical_language(language),[])
