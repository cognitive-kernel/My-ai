from types import SimpleNamespace
import json

from my_ai import settings_feature as sf


def test_lesson_evidence_and_provenance_are_persisted(monkeypatch):
    sf._setup()
    monkeypatch.setattr(sf, "require_admin", lambda request: {"id": 1, "username": "test-admin"})

    course_id = sf.execute("INSERT INTO custom_courses(name,description) VALUES(?,?)", ("Evidence Course", "test"))
    topic_id = sf.execute(
        "INSERT INTO custom_course_topics(course_id,topic_order,title,goal,source_url) VALUES(?,?,?,?,?)",
        (course_id, 1, "Topic", "Goal", "https://example.com/docs"),
    )
    sf.execute("INSERT INTO custom_course_progress(course_id,topic_id) VALUES(?,?)", (course_id, topic_id))

    evidence = [{"type": "source", "url": "https://example.com/docs", "scope": "Goal"}]
    provenance = {"course_id": course_id, "topic_id": topic_id, "source_url": "https://example.com/docs"}
    sf._set_topic(topic_id, "started", 70, "assessment", lesson="Lesson text", evidence=evidence, provenance=provenance)

    result = sf.course_lesson_evidence(course_id, topic_id, SimpleNamespace())
    assert result["lesson"] == "Lesson text"
    assert result["evidence"] == evidence
    assert result["provenance"]["source_url"] == "https://example.com/docs"


def test_progress_exposes_serialized_lesson_provenance_fields():
    sf._setup()
    course_id = sf.execute("INSERT INTO custom_courses(name,description) VALUES(?,?)", ("Evidence Fields", "test"))
    topic_id = sf.execute(
        "INSERT INTO custom_course_topics(course_id,topic_order,title,goal) VALUES(?,?,?,?)",
        (course_id, 1, "Topic", "Goal"),
    )
    sf.execute("INSERT INTO custom_course_progress(course_id,topic_id) VALUES(?,?)", (course_id, topic_id))
    row = sf._progress(course_id)[0]
    assert json.loads(row["evidence_json"]) == []
    assert json.loads(row["provenance_json"]) == {}
