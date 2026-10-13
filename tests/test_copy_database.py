import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.copy_database import TargetNotEmptyError, copy_database, main
from app.database import (
    Experience,
    Profile,
    Skill,
    create_database_engine,
    initialize_database,
)


def _source_with_content(tmp_path):
    engine = initialize_database(
        create_database_engine(f"sqlite:///{tmp_path / 'source.db'}")
    )
    with Session(engine) as session, session.begin():
        owner = session.scalar(select(Profile).where(Profile.slug == "owner"))
        owner.display_name = "Chris Setioko"
        sql = Skill(name="SQL", is_visible=False, display_order=2)
        owner.skills.append(sql)
        owner.experiences.append(
            Experience(title="Operations Lead", company="Bakery", skills=[sql])
        )
    return engine


def test_copy_keeps_ids_links_and_flags_and_replaces_starter(tmp_path) -> None:
    source = _source_with_content(tmp_path)
    target = initialize_database(
        create_database_engine(f"sqlite:///{tmp_path / 'target.db'}")
    )

    counts = copy_database(source, target)

    assert counts["profiles"] == 1
    assert counts["experience_skills"] == 1
    with Session(target) as session:
        profiles = session.scalars(select(Profile)).all()
        assert [p.display_name for p in profiles] == ["Chris Setioko"]
        skill = session.scalar(select(Skill))
        assert (skill.name, skill.is_visible, skill.display_order) == ("SQL", False, 2)
        assert [s.name for s in session.scalar(select(Experience)).skills] == ["SQL"]


def test_copy_refuses_target_with_real_content(tmp_path) -> None:
    source = _source_with_content(tmp_path)
    target = _source_with_content(tmp_path / "other")

    with pytest.raises(TargetNotEmptyError):
        copy_database(source, target)

    with Session(target) as session:
        assert session.scalar(select(Profile)).display_name == "Chris Setioko"


def test_main_refuses_missing_source_file(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("COPY_TARGET", f"sqlite:///{tmp_path / 'target.db'}")
    missing = tmp_path / "typo.db"

    assert main([str(missing), "--target-env", "COPY_TARGET"]) == 2
    assert not missing.exists()
    assert "does not exist" in capsys.readouterr().err


def test_main_refuses_unset_target_without_echoing_urls(tmp_path, monkeypatch, capsys) -> None:
    _source_with_content(tmp_path)
    monkeypatch.delenv("COPY_TARGET", raising=False)

    assert main([str(tmp_path / "source.db"), "--target-env", "COPY_TARGET"]) == 2
    assert "COPY_TARGET is not set" in capsys.readouterr().err
