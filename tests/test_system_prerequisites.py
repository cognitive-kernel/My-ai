import pytest

from my_ai import file_processing


def test_generic_os_package_install_requires_confirmation(monkeypatch):
    with pytest.raises(PermissionError):
        file_processing.install_os_packages(["ffmpeg"], confirmed=False)


def test_generic_os_package_install_uses_argv_without_shell(monkeypatch):
    calls = []

    monkeypatch.setattr(file_processing, "assert_mutation_allowed", lambda _: None)
    monkeypatch.setattr(file_processing.shutil, "which", lambda name: "/usr/bin/apt-get" if name == "apt-get" else None)
    monkeypatch.setattr(file_processing.subprocess, "run", lambda command, **kwargs: calls.append((command, kwargs)))

    result = file_processing.install_os_packages(["ffmpeg", "git"], confirmed=True)

    assert result["packages"] == ["ffmpeg", "git"]
    assert calls[0][0] == ["apt-get", "install", "-y", "ffmpeg", "git"]
    assert calls[0][1]["check"] is True


def test_generic_os_package_name_rejects_shell_metacharacters(monkeypatch):
    monkeypatch.setattr(file_processing, "assert_mutation_allowed", lambda _: None)
    with pytest.raises(ValueError):
        file_processing.install_os_packages(["ffmpeg;rm -rf /"], confirmed=True)
