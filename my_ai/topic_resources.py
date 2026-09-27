from __future__ import annotations

from typing import Dict, List, Tuple


# Supplementary resources are intentionally separate from official documentation.
# Each learning topic receives topic-specific external references through
# supplementary_source_urls(). Official sources remain available through
# curriculum.py and are merged by the learner.

FOREX_CURRICULUM = [
    {"order": 1, "topic": "Forex fundamentals", "goal": "Understand FX, currencies, participants, spot markets and the role of exchange rates."},
    {"order": 2, "topic": "Currency pairs and quotes", "goal": "Read base/quote currencies, bid/ask quotes, direct and indirect quotations."},
    {"order": 3, "topic": "Pips, spreads and transaction costs", "goal": "Understand pips, pipettes, spreads, commissions, swaps and trading costs."},
    {"order": 4, "topic": "Leverage and margin", "goal": "Understand leverage, margin requirements, liquidation risk and why leverage magnifies losses."},
    {"order": 5, "topic": "Order types and execution", "goal": "Understand market, limit, stop, stop-limit and conditional orders and execution mechanics."},
    {"order": 6, "topic": "Brokers and trading venues", "goal": "Understand OTC dealer models, regulated venues, counterparties, liquidity and execution quality."},
    {"order": 7, "topic": "Forex market sessions", "goal": "Understand global sessions, liquidity windows, overlaps and time-zone effects."},
    {"order": 8, "topic": "FX market structure", "goal": "Understand OTC structure, dealers, liquidity providers, electronic venues and fragmentation."},
    {"order": 9, "topic": "Fundamental analysis", "goal": "Connect macroeconomic conditions and policy expectations to currency valuation."},
    {"order": 10, "topic": "Central banks and monetary policy", "goal": "Understand policy rates, guidance, balance sheets and their transmission to FX."},
    {"order": 11, "topic": "Interest rates and yield differentials", "goal": "Understand rate differentials, carry concepts and their relationship with exchange rates."},
    {"order": 12, "topic": "Inflation and currency markets", "goal": "Understand inflation measures, expectations and their potential FX implications."},
    {"order": 13, "topic": "Employment and economic growth", "goal": "Interpret employment, GDP and growth indicators as macroeconomic evidence."},
    {"order": 14, "topic": "Economic calendars and news", "goal": "Read economic calendars, distinguish releases from expectations and evaluate event risk."},
    {"order": 15, "topic": "Technical analysis foundations", "goal": "Understand charts, timeframes, trends, market structure and technical hypotheses."},
    {"order": 16, "topic": "Support and resistance", "goal": "Study support/resistance as testable market-structure hypotheses rather than guarantees."},
    {"order": 17, "topic": "Candlesticks and price action", "goal": "Read OHLC candles, formations and price-action context without treating patterns as certainty."},
    {"order": 18, "topic": "Trend and market structure", "goal": "Identify trends, ranges, breakouts, pullbacks and structural changes."},
    {"order": 19, "topic": "Technical indicators", "goal": "Understand moving averages, momentum and volatility indicators and their limitations."},
    {"order": 20, "topic": "Volatility and ATR", "goal": "Measure volatility and understand how changing volatility affects analysis and risk."},
    {"order": 21, "topic": "Correlation and currency relationships", "goal": "Analyze relationships among currency pairs and recognize unstable correlations."},
    {"order": 22, "topic": "Market sentiment", "goal": "Study positioning, sentiment indicators and behavioral signals as contextual evidence."},
    {"order": 23, "topic": "Risk management", "goal": "Build a risk framework covering loss limits, exposure, diversification and drawdown."},
    {"order": 24, "topic": "Position sizing", "goal": "Calculate position size from defined risk, stop distance, contract value and account constraints."},
    {"order": 25, "topic": "Drawdown and risk of ruin", "goal": "Understand drawdowns, probability of loss sequences and capital-preservation constraints."},
    {"order": 26, "topic": "Trading plans and journals", "goal": "Create a rule-based study/trading plan and maintain reproducible records for review."},
    {"order": 27, "topic": "Backtesting and validation", "goal": "Design reproducible historical tests, avoid look-ahead bias and separate research from validation."},
    {"order": 28, "topic": "Strategy design and evaluation", "goal": "Define hypotheses, rules, metrics, robustness checks and failure conditions."},
    {"order": 29, "topic": "Trading psychology and behavioral finance", "goal": "Study cognitive biases, discipline, decision processes and behavioral failure modes."},
    {"order": 30, "topic": "Algorithmic and systematic FX", "goal": "Understand systematic rules, data pipelines, execution assumptions and model risk."},
    {"order": 31, "topic": "FX derivatives and futures", "goal": "Understand currency futures, forwards, options and differences from retail spot FX."},
    {"order": 32, "topic": "FX microstructure and execution", "goal": "Study liquidity, order flow, price discovery, slippage and execution quality."},
    {"order": 33, "topic": "Regulation, fraud and broker due diligence", "goal": "Identify regulatory concepts, disclosures, registration checks and common forex fraud patterns."},
    {"order": 34, "topic": "Forex research project", "goal": "Complete an evidence-based FX research project with data, methodology, testing, risk analysis and documented limitations."},
]

FOREX_SOURCES = [
    "https://www.babypips.com/learn/forex",
    "https://www.cmegroup.com/education/courses/introduction-to-fx.html",
    "https://www.cftc.gov/LearnAndProtect/forexfrauds",
    "https://www.bis.org/publications/working-paper-1094-foreign-exchange-market",
]

# Topic-specific supplementary sources. These complement official documentation
# with independent educators, exchanges, regulators, standards bodies and other references.
FOREX_TOPIC_SOURCES: Dict[str, List[str]] = {
    "Forex fundamentals": ["https://www.babypips.com/learn/forex/preschool", "https://www.cmegroup.com/education/courses/introduction-to-fx.html", "https://www.bis.org/publications/working-paper-1094-foreign-exchange-market"],
    "Currency pairs and quotes": ["https://www.babypips.com/learn/forex/preschool", "https://www.investopedia.com/terms/f/forex.asp", "https://www.cmegroup.com/education/courses/introduction-to-fx.html"],
    "Pips, spreads and transaction costs": ["https://www.babypips.com/learn/forex/preschool", "https://www.investopedia.com/terms/b/bid-and-ask.asp", "https://www.investopedia.com/terms/f/forex.asp"],
    "Leverage and margin": ["https://www.babypips.com/learn/forex/preschool", "https://www.cftc.gov/LearnAndProtect/forexfrauds", "https://www.investopedia.com/terms/m/margin.asp"],
    "Order types and execution": ["https://www.babypips.com/learn/forex", "https://www.investopedia.com/terms/o/order.asp", "https://www.cmegroup.com/education/courses/introduction-to-fx.html"],
    "Brokers and trading venues": ["https://www.cftc.gov/LearnAndProtect/forexfrauds", "https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_MustKnowForex.html", "https://www.bis.org/publications/qr-202512/fx-trade-execution-landscape-through-prism-2025-bis-triennial-survey"],
    "Forex market sessions": ["https://www.babypips.com/learn/forex", "https://www.investopedia.com/terms/f/forex.asp", "https://www.bis.org/publications/qr-202512/fx-trade-execution-landscape-through-prism-2025-bis-triennial-survey"],
    "FX market structure": ["https://www.bis.org/publications/working-paper-1094-foreign-exchange-market", "https://www.bis.org/publications/qr-202512/fx-trade-execution-landscape-through-prism-2025-bis-triennial-survey", "https://www.cmegroup.com/education/courses/introduction-to-fx.html"],
    "Fundamental analysis": ["https://www.babypips.com/learn/forex/undergraduate-freshman", "https://www.investopedia.com/terms/f/fundamentalanalysis.asp", "https://www.federalreserve.gov/monetarypolicy.htm"],
    "Central banks and monetary policy": ["https://www.federalreserve.gov/monetarypolicy.htm", "https://www.babypips.com/learn/forex/undergraduate-freshman", "https://www.investopedia.com/terms/m/monetarypolicy.asp"],
    "Interest rates and yield differentials": ["https://www.investopedia.com/terms/i/interestrate.asp", "https://www.federalreserve.gov/monetarypolicy.htm", "https://www.babypips.com/learn/forex/undergraduate-freshman"],
    "Inflation and currency markets": ["https://www.investopedia.com/terms/i/inflation.asp", "https://www.federalreserve.gov/monetarypolicy.htm", "https://www.babypips.com/learn/forex/undergraduate-freshman"],
    "Employment and economic growth": ["https://www.investopedia.com/terms/g/gdp.asp", "https://www.investopedia.com/terms/u/unemployment.asp", "https://www.babypips.com/learn/forex/undergraduate-freshman"],
    "Economic calendars and news": ["https://www.babypips.com/learn/forex", "https://www.investopedia.com/economic-calendar/", "https://www.cmegroup.com/education.html"],
    "Technical analysis foundations": ["https://www.babypips.com/learn/forex/elementary", "https://www.investopedia.com/technical-analysis-4689657", "https://www.cmegroup.com/education.html"],
    "Support and resistance": ["https://www.babypips.com/learn/forex/elementary", "https://www.investopedia.com/terms/s/support.asp", "https://www.investopedia.com/terms/r/resistance.asp"],
    "Candlesticks and price action": ["https://www.babypips.com/learn/forex/elementary", "https://www.investopedia.com/terms/c/candlestick.asp", "https://www.investopedia.com/terms/p/price-action.asp"],
    "Trend and market structure": ["https://www.babypips.com/learn/forex/elementary", "https://www.investopedia.com/terms/t/trendtrading.asp", "https://www.investopedia.com/technical-analysis-4689657"],
    "Technical indicators": ["https://www.babypips.com/learn/forex/elementary", "https://www.investopedia.com/technical-analysis-4689657", "https://www.investopedia.com/terms/m/movingaverage.asp"],
    "Volatility and ATR": ["https://www.babypips.com/learn/forex/middle-school", "https://www.investopedia.com/terms/a/atr.asp", "https://www.investopedia.com/terms/v/volatility.asp"],
    "Correlation and currency relationships": ["https://www.babypips.com/learn/forex", "https://www.investopedia.com/terms/c/correlation.asp", "https://www.bis.org/publications/working-paper-1094-foreign-exchange-market"],
    "Market sentiment": ["https://www.babypips.com/learn/forex", "https://www.investopedia.com/terms/m/marketsentiment.asp", "https://www.cmegroup.com/education.html"],
    "Risk management": ["https://www.cftc.gov/LearnAndProtect/forexfrauds", "https://www.babypips.com/learn/forex/undergraduate-junior", "https://www.investopedia.com/terms/r/riskmanagement.asp"],
    "Position sizing": ["https://www.babypips.com/learn/forex/undergraduate-junior", "https://www.investopedia.com/terms/p/positionsizing.asp", "https://www.cftc.gov/LearnAndProtect/forexfrauds"],
    "Drawdown and risk of ruin": ["https://www.babypips.com/learn/forex/undergraduate-junior", "https://www.investopedia.com/terms/d/drawdown.asp", "https://www.investopedia.com/terms/r/risk-of-ruin.asp"],
    "Trading plans and journals": ["https://www.babypips.com/learn/forex/undergraduate-junior", "https://www.investopedia.com/terms/t/trading-plan.asp", "https://www.cftc.gov/LearnAndProtect/forexfrauds"],
    "Backtesting and validation": ["https://www.babypips.com/learn/forex/undergraduate-junior", "https://www.investopedia.com/terms/b/backtesting.asp", "https://www.cmegroup.com/education.html"],
    "Strategy design and evaluation": ["https://www.babypips.com/learn/forex/undergraduate-junior", "https://www.investopedia.com/terms/t/trading-strategy.asp", "https://www.cmegroup.com/education.html"],
    "Trading psychology and behavioral finance": ["https://www.babypips.com/learn/forex/undergraduate-junior", "https://www.investopedia.com/terms/b/behavioralfinance.asp", "https://www.cftc.gov/LearnAndProtect/forexfrauds"],
    "Algorithmic and systematic FX": ["https://www.bis.org/publications/qr-202512/fx-trade-execution-landscape-through-prism-2025-bis-triennial-survey", "https://www.cmegroup.com/education.html", "https://www.investopedia.com/terms/a/algorithmictrading.asp"],
    "FX derivatives and futures": ["https://www.cmegroup.com/education/courses/introduction-to-fx.html", "https://www.cmegroup.com/education/courses.html", "https://www.investopedia.com/terms/f/forex.asp"],
    "FX microstructure and execution": ["https://www.bis.org/publications/qr-202512/fx-trade-execution-landscape-through-prism-2025-bis-triennial-survey", "https://www.bis.org/publications/working-paper-1094-foreign-exchange-market", "https://www.cmegroup.com/education/courses/introduction-to-fx.html"],
    "Regulation, fraud and broker due diligence": ["https://www.cftc.gov/LearnAndProtect/forexfrauds", "https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_MustKnowForex.html", "https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/cftcnasaaforexalert.html"],
    "Forex research project": ["https://www.bis.org/publications/working-paper-1094-foreign-exchange-market", "https://www.babypips.com/learn/forex", "https://www.cmegroup.com/education/courses/introduction-to-fx.html"],
}

# Supplementary pools for the existing technical domains. Rules are keyword based
# so newly appended advanced topics also receive topic-relevant links without
# requiring a second hard-coded list.
FOREX_RULES: List[Tuple[Tuple[str, ...], Tuple[str, ...]]] = [
    (("mql4",), ("https://www.mql4.com/en/docs", "https://www.mql4.com/en/docs/basis", "https://www.mql4.com/en/docs/series")),
    (("mql5",), ("https://www.mql5.com/en/docs", "https://www.mql5.com/en/docs/runtime", "https://www.mql5.com/en/docs/trading")),
    (("metatrader", "custom trading dashboards"), ("https://www.metatrader5.com/en/terminal/help", "https://www.mql5.com/en/docs/objects", "https://www.mql5.com/en/docs/runtime/event_fire")),
    (("backtest", "optimization", "walk-forward", "out-of-sample", "monte carlo"), ("https://www.mql5.com/en/docs/runtime/testing", "https://www.investopedia.com/terms/b/backtesting.asp", "https://www.babypips.com/learn/forex/undergraduate-junior")),
    (("risk", "position sizing", "drawdown", "risk of ruin", "capital"), ("https://www.cftc.gov/LearnAndProtect/forexfrauds", "https://www.babypips.com/learn/forex/undergraduate-junior", "https://www.investopedia.com/terms/r/riskmanagement.asp")),
    (("indicator", "moving average", "rsi", "macd", "stochastic", "bollinger", "atr", "adx", "cci", "williams", "ichimoku", "sar", "obv", "mfi", "cmf", "vwap", "pivot", "donchian", "keltner", "envelopes", "oscillator", "divergence", "fibonacci"), ("https://www.babypips.com/learn/forex/elementary", "https://www.investopedia.com/technical-analysis-4689657", "https://www.babypips.com/learn/forex/best-technical-indicator-forex")),
    (("elliott", "harmonic", "chart pattern", "reversal pattern", "candlestick", "price action"), ("https://www.babypips.com/learn/forex/summer-school", "https://www.investopedia.com/technical-analysis-4689657", "https://www.babypips.com/learn/forex/riding-elliotts-waves")),
    (("trend", "market structure", "support", "resistance", "breakout", "pullback", "retest", "bos", "choch", "liquidity", "order block", "imbalance", "supply", "demand"), ("https://www.babypips.com/learn/forex/elementary", "https://www.babypips.com/learn/forex/middle-school", "https://www.investopedia.com/technical-analysis-4689657")),
    (("fundamental", "macro", "central bank", "interest rate", "inflation", "employment", "economic", "intermarket", "news"), ("https://www.babypips.com/learn/forex/undergraduate-freshman", "https://www.investopedia.com/forex-4427685", "https://www.federalreserve.gov/monetarypolicy.htm")),
    (("broker", "execution", "spread", "commission", "order", "leverage", "margin", "lot", "pip", "session", "liquidity", "volatility"), ("https://www.babypips.com/learn/forex/preschool", "https://www.cftc.gov/LearnAndProtect/forexfrauds", "https://www.cmegroup.com/education/courses/introduction-to-fx.html")),
    (("currency pair", "base and quote", "majors", "minors", "exotics"), ("https://www.babypips.com/learn/forex/preschool", "https://www.investopedia.com/terms/f/forex.asp", "https://www.cmegroup.com/education/courses/introduction-to-fx.html")),
    (("stop loss", "take profit", "dynamic stop", "target"), ("https://www.babypips.com/learn/forex", "https://www.investopedia.com/terms/s/stop-lossorder.asp", "https://www.investopedia.com/terms/t/take-profitorder.asp")),
    (("scalping", "swing trading", "position trading", "mean-reversion", "momentum strategies"), ("https://www.babypips.com/learn/forex", "https://www.investopedia.com/forex-4427685", "https://www.cmegroup.com/education.html")),
    (("market regime", "regime"), ("https://www.bis.org/publications/working-paper-1094-foreign-exchange-market", "https://www.babypips.com/learn/forex", "https://www.investopedia.com/technical-analysis-4689657")),
    (("psychology", "journal", "statistics", "expectancy", "strategy engineering", "entry and exit", "trading plan"), ("https://www.babypips.com/learn/forex/undergraduate-junior", "https://www.investopedia.com/terms/b/behavioralfinance.asp", "https://www.cftc.gov/LearnAndProtect/forexfrauds")),
    (("algorithmic", "quantitative", "portfolio", "systematic", "production", "robustness"), ("https://www.bis.org/publications/qr-202512/fx-trade-execution-landscape-through-prism-2025-bis-triennial-survey", "https://www.mql5.com/en/docs", "https://www.cmegroup.com/education.html")),
    (("futures", "derivatives"), ("https://www.cmegroup.com/education/courses/introduction-to-fx.html", "https://www.cmegroup.com/education/courses.html", "https://www.investopedia.com/terms/f/futures.asp")),
    (("regulation", "fraud", "due diligence"), ("https://www.cftc.gov/LearnAndProtect/forexfrauds", "https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_MustKnowForex.html", "https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/cftcnasaaforexalert.html")),
    (("market structure", "microstructure", "execution", "research project", "capstone"), ("https://www.bis.org/publications/working-paper-1094-foreign-exchange-market", "https://www.bis.org/publications/qr-202512/fx-trade-execution-landscape-through-prism-2025-bis-triennial-survey", "https://www.cmegroup.com/education/courses/introduction-to-fx.html")),
]

DOMAIN_RULES: Dict[str, List[Tuple[Tuple[str, ...], Tuple[str, ...]]]] = {
    "Python": [
        (("async", "concurr"), ("https://realpython.com/async-io-python/", "https://realpython.com/python-concurrency/")),
        (("test", "regression"), ("https://realpython.com/pytest-python-testing/", "https://realpython.com/python-testing/")),
        (("packag", "dependenc", "distribution"), ("https://realpython.com/python-modules-packages/", "https://realpython.com/pypi-publish-python-package/")),
        (("profil", "performance", "memory"), ("https://realpython.com/python-profiling/", "https://realpython.com/python-memory-management/")),
        (("descriptor", "metaclass", "data model", "mro"), ("https://realpython.com/python-metaclasses/", "https://realpython.com/python-descriptors/")),
        (("typing", "protocol"), ("https://realpython.com/python-type-checking/", "https://realpython.com/python-protocol/")),
        (("security", "secure"), ("https://realpython.com/python-security/", "https://owasp.org/www-project-top-ten/")),
        (("http", "api", "network", "socket"), ("https://realpython.com/api-integration-in-python/", "https://realpython.com/python-sockets/")),
        (("database", "sqlite", "sql"), ("https://realpython.com/python-sql-libraries/", "https://realpython.com/python-sqlite-sqlalchemy/")),
        (("debug", "bug", "diagnos"), ("https://realpython.com/python-debugging-pdb/", "https://realpython.com/python-logging/")),
    ],
    "C": [
        (("pointer", "memory", "undefined", "sanit"), ("https://beej.us/guide/bgc/html/split/", "https://clang.llvm.org/docs/AddressSanitizer.html")),
        (("thread", "concurr", "posix"), ("https://beej.us/guide/bgipc/html/", "https://man7.org/linux/man-pages/man7/pthreads.7.html")),
        (("build", "make", "compil", "link"), ("https://cmake.org/cmake/help/latest/guide/tutorial/", "https://makefiletutorial.com/")),
        (("network", "socket"), ("https://beej.us/guide/bgnet/html/", "https://man7.org/linux/man-pages/man7/socket.7.html")),
        (("debug", "test"), ("https://beej.us/guide/bggdb/html/", "https://clang.llvm.org/docs/AddressSanitizer.html")),
        (("security", "hardening"), ("https://owasp.org/www-project-code-review-guide/", "https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html")),
    ],
    "PHP": [
        (("composer", "psr", "package"), ("https://phptherightway.com/", "https://getcomposer.org/doc/")),
        (("laravel", "framework"), ("https://laracasts.com/series/laravel-from-scratch", "https://laravel.com/learn")),
        (("security", "xss", "csrf", "ssrf", "upload"), ("https://owasp.org/www-project-web-security-testing-guide/", "https://cheatsheetseries.owasp.org/")),
        (("test", "phpunit"), ("https://phpunit.de/documentation.html", "https://phptherightway.com/#testing")),
        (("performance", "opcache", "profil"), ("https://www.php.net/manual/en/book.opcache.php", "https://phptherightway.com/#infrastructure")),
        (("api", "http", "web"), ("https://phptherightway.com/", "https://developer.mozilla.org/en-US/docs/Web/HTTP")),
        (("database", "mysql", "postgres", "sqlite", "sql server"), ("https://www.php.net/manual/en/pdo.php", "https://owasp.org/www-project-code-review-guide/")),
    ],
    "JavaScript": [
        (("async", "promise", "event loop"), ("https://javascript.info/async", "https://javascript.info/event-loop")),
        (("object", "prototype", "function"), ("https://javascript.info/object", "https://javascript.info/prototypes")),
        (("module", "package"), ("https://javascript.info/modules", "https://javascript.info/modules-intro")),
        (("dom", "browser", "web api"), ("https://javascript.info/document", "https://javascript.info/events")),
        (("node", "stream", "buffer", "process"), ("https://nodejs.org/en/learn", "https://nodejs.org/api/stream.html")),
        (("security", "xss", "csrf", "prototype pollution"), ("https://owasp.org/www-project-top-ten/", "https://cheatsheetseries.owasp.org/")),
        (("test", "production", "performance"), ("https://javascript.info/testing", "https://web.dev/learn/performance/")),
    ],
    "SQL Server": [
        (("execution plan", "query optimization", "optim"), ("https://www.brentozar.com/sql/execution-plans/", "https://www.brentozar.com/sql/query-tuning/")),
        (("index", "performance"), ("https://www.brentozar.com/sql/indexing/", "https://www.brentozar.com/archive/category/indexing/")),
        (("transaction", "concurr", "deadlock", "lock"), ("https://www.brentozar.com/archive/category/locking/", "https://learn.microsoft.com/en-us/sql/relational-databases/sql-server-transaction-locking-and-row-versioning-guide")),
        (("security", "backup", "recover"), ("https://learn.microsoft.com/en-us/sql/relational-databases/security/", "https://www.brentozar.com/archive/category/backups/")),
        (("monitor", "diagnos", "query store"), ("https://www.brentozar.com/archive/category/monitoring/", "https://learn.microsoft.com/en-us/sql/relational-databases/performance/monitor-and-tune-for-performance")),
    ],
    "MySQL": [
        (("optim", "index", "performance"), ("https://www.percona.com/blog/category/mysql-performance/", "https://www.percona.com/blog/category/mysql-optimization/")),
        (("innodb", "storage engine"), ("https://www.percona.com/blog/category/innodb/", "https://www.percona.com/blog/category/mysql/")),
        (("transaction", "lock", "deadlock"), ("https://www.percona.com/blog/category/mysql-locking/", "https://www.percona.com/blog/category/mysql-transactions/")),
        (("security", "backup", "recover"), ("https://www.percona.com/blog/category/mysql-security/", "https://www.percona.com/blog/category/mysql-backup/")),
        (("replication", "high availability"), ("https://www.percona.com/blog/category/mysql-replication/", "https://www.percona.com/blog/category/mysql-high-availability/")),
    ],
    "SQLite": [
        (("query", "index", "planner", "performance"), ("https://www.sqlite.org/queryplanner.html", "https://www.sqlite.org/optoverview.html")),
        (("transaction", "wal", "concurr"), ("https://www.sqlite.org/wal.html", "https://www.sqlite.org/lockingv3.html")),
        (("fts", "json", "cte", "window"), ("https://www.sqlite.org/fts5.html", "https://www.sqlite.org/json1.html")),
        (("security", "reliability", "corruption", "backup"), ("https://www.sqlite.org/security.html", "https://www.sqlite.org/howtocorrupt.html")),
        (("migration", "schema"), ("https://www.sqlite.org/lang_altertable.html", "https://www.sqlite.org/foreignkeys.html")),
    ],
    "Android": [
        (("compose", "ui"), ("https://developer.android.com/develop/ui/compose/documentation", "https://kotlinlang.org/docs/compose-multiplatform.html")),
        (("coroutine", "concurr"), ("https://kotlinlang.org/docs/coroutines-overview.html", "https://kotlinlang.org/docs/coroutines-basics.html")),
        (("architecture", "viewmodel", "repository"), ("https://source.android.com/docs", "https://kotlinlang.org/docs/home.html")),
        (("network", "retrofit", "http"), ("https://square.github.io/retrofit/", "https://kotlinlang.org/docs/coroutines-and-channels.html")),
        (("security", "permission", "keystore"), ("https://source.android.com/docs/security", "https://source.android.com/docs/security/features/keystore")),
        (("test", "performance", "profil"), ("https://source.android.com/docs/setup", "https://kotlinlang.org/docs/jvm-test-using-junit.html")),
    ],
    "iOS": [
        (("swift", "concurr"), ("https://docs.swift.org/swift-book/LanguageGuide/Concurrency.html", "https://www.swift.org/documentation/concurrency/")),
        (("swiftui", "ui"), ("https://www.hackingwithswift.com/quick-start/swiftui", "https://www.swiftbysundell.com/articles/")),
        (("network", "urlsession", "http"), ("https://www.avanderlee.com/swift/urlsession-urlsessiontask-networking/", "https://developer.apple.com/documentation/foundation/urlsession")),
        (("security", "keychain", "privacy"), ("https://developer.apple.com/documentation/security/keychain_services", "https://developer.apple.com/documentation/security")),
        (("test", "testing"), ("https://docs.swift.org/swift-book/documentation/the-swift-programming-language/testing", "https://www.swift.org/documentation/server/guides/testing.html")),
        (("performance", "instruments"), ("https://developer.apple.com/tutorials/instruments", "https://developer.apple.com/documentation/xcode/diagnosing-memory-thread-and-crash-issues-early")),
    ],
    "Rust": [
        (("ownership", "borrow", "lifetime"), ("https://rust-book.cs.brown.edu/ch04-00-understanding-ownership.html", "https://rust-book.cs.brown.edu/ch10-00-generics.html")),
        (("concurr", "thread", "send", "sync"), ("https://rust-book.cs.brown.edu/ch16-00-concurrency.html", "https://rust-book.cs.brown.edu/ch16-04-extensible-concurrency-sync-and-send.html")),
        (("async", "future", "runtime", "pin"), ("https://rust-lang.github.io/async-book/", "https://rust-lang.github.io/async-book/part-guide/async-await.html")),
        (("unsafe", "ffi", "pointer"), ("https://doc.rust-lang.org/nomicon/", "https://doc.rust-lang.org/book/ffi.html")),
        (("cargo", "build", "release"), ("https://doc.rust-lang.org/cargo/", "https://doc.rust-lang.org/cargo/reference/manifest.html")),
        (("test", "benchmark", "performance"), ("https://doc.rust-lang.org/book/ch11-00-testing.html", "https://bheisler.github.io/criterion.rs/book/")),
        (("security", "audit", "fuzz"), ("https://rustsec.org/", "https://rust-fuzz.github.io/book/")),
    ],
    "Pentest": [
        (("web", "xss", "sql injection", "csrf", "ssrf", "upload"), ("https://owasp.org/www-project-web-security-testing-guide/", "https://portswigger.net/web-security")),
        (("api", "authorization"), ("https://wstg.owasp.org/latest/4-Web_Application_Security_Testing/12-API_Testing/00-API_Testing_Overview/", "https://portswigger.net/web-security/api-testing")),
        (("authentication", "session"), ("https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/04-Authentication_Testing/04-Testing_for_Bypassing_Authentication_Schema/", "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html")),
        (("recon", "asset", "enumeration"), ("https://owasp.org/www-project-web-security-testing-guide/", "https://nmap.org/book/man.html")),
        (("code review", "secure code"), ("https://cheatsheetseries.owasp.org/cheatsheets/Secure_Code_Review_Cheat_Sheet.html", "https://owasp.org/www-project-code-review-guide/")),
        (("report", "remediation"), ("https://owasp.org/www-project-web-security-testing-guide/", "https://portswigger.net/web-security")),
    ],
}

DOMAIN_FALLBACKS = {
    "Python": ["https://realpython.com/", "https://pycon.org/"],
    "C": ["https://beej.us/guide/bgc/html/split/", "https://en.cppreference.com/w/c"],
    "PHP": ["https://phptherightway.com/", "https://getcomposer.org/doc/", "https://symfony.com/doc/current/"],
    "JavaScript": ["https://javascript.info/", "https://web.dev/learn/javascript/"],
    "SQL Server": ["https://www.brentozar.com/sql/", "https://learn.microsoft.com/en-us/sql/"],
    "MySQL": ["https://www.percona.com/blog/", "https://planet.mysql.com/"],
    "SQLite": ["https://www.sqlite.org/whentouse.html", "https://www.sqlite.org/forum/"],
    "Android": ["https://source.android.com/docs", "https://kotlinlang.org/docs/home.html", "https://square.github.io/retrofit/"],
    "iOS": ["https://www.hackingwithswift.com/100/swiftui", "https://www.swiftbysundell.com/"],
    "Rust": ["https://rust-book.cs.brown.edu/", "https://rust-lang.github.io/async-book/"],
    "Pentest": ["https://portswigger.net/web-security", "https://owasp.org/www-project-web-security-testing-guide/"],
}


def supplementary_source_urls(language: str, topic: str) -> List[str]:
    lang = str(language or "").strip()
    topic_text = str(topic or "").casefold()
    if lang == "Forex":
        forex_matches = list(FOREX_TOPIC_SOURCES.get(str(topic), []))
        for keywords, urls in FOREX_RULES:
            if any(k.casefold() in topic_text for k in keywords):
                forex_matches.extend(urls)
        forex_matches.extend(FOREX_SOURCES)
        return list(dict.fromkeys(forex_matches))

    matches: List[str] = []
    for keywords, urls in DOMAIN_RULES.get(lang, []):
        if any(k.casefold() in topic_text for k in keywords):
            matches.extend(urls)
    matches.extend(DOMAIN_FALLBACKS.get(lang, []))
    return list(dict.fromkeys(matches))


def validate_topic_resources(curricula: dict) -> List[str]:
    missing = []
    for language, topics in curricula.items():
        for item in topics:
            topic = str(item.get("topic", ""))
            if len(supplementary_source_urls(language, topic)) < 2:
                missing.append(f"{language}: {topic}")
    return missing
