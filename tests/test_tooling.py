from my_ai.tooling import canonical_language, _validate_readonly_sql

def test_language_catalog_contains_all_supported_languages():
    assert {canonical_language(x) for x in ["Python","C","PHP","JavaScript","Rust","Kotlin","Swift","Android","iOS"]} == {"Python","C","PHP","JavaScript","Rust","Kotlin","Swift","Android","iOS"}

def test_readonly_sql_rejects_mutations():
    for sql in ["DELETE FROM Sellers","UPDATE Sellers SET name='x'","DROP TABLE Sellers","EXEC dbo.Reset"]:
        try:
            _validate_readonly_sql(sql)
        except ValueError:
            pass
        else:
            raise AssertionError(sql)

def test_readonly_sql_accepts_select_and_cte():
    assert _validate_readonly_sql("SELECT TOP 10 * FROM Sellers").startswith("SELECT")
    assert _validate_readonly_sql("WITH x AS (SELECT 1 AS id) SELECT * FROM x").startswith("WITH")
