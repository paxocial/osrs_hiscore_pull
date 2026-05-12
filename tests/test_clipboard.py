from __future__ import annotations

from core import clipboard


class _DummyPyperclipException(Exception):
    pass


class _RaisesPyperclipError:
    PyperclipException = _DummyPyperclipException

    @staticmethod
    def copy(text: str) -> None:
        raise _DummyPyperclipException("clipboard unavailable")


class _RaisesFileNotFound:
    PyperclipException = _DummyPyperclipException

    @staticmethod
    def copy(text: str) -> None:
        raise FileNotFoundError("clip.exe")


class _WorkingClipboard:
    PyperclipException = _DummyPyperclipException

    @staticmethod
    def copy(text: str) -> None:
        return None


def test_copy_text_returns_false_when_backend_missing(monkeypatch):
    monkeypatch.setattr(clipboard, "pyperclip", None)
    assert clipboard.copy_text("hello") is False


def test_copy_text_returns_false_on_pyperclip_exception(monkeypatch):
    monkeypatch.setattr(clipboard, "pyperclip", _RaisesPyperclipError)
    assert clipboard.copy_text("hello") is False


def test_copy_text_returns_false_on_os_error(monkeypatch):
    monkeypatch.setattr(clipboard, "pyperclip", _RaisesFileNotFound)
    assert clipboard.copy_text("hello") is False


def test_copy_text_returns_true_on_success(monkeypatch):
    monkeypatch.setattr(clipboard, "pyperclip", _WorkingClipboard)
    assert clipboard.copy_text("hello") is True
