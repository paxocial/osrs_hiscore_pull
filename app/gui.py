"""Simple Tkinter GUI for fetching OSRS snapshots and reports."""

from __future__ import annotations

import threading
import traceback
from pathlib import Path
import codecs

import tkinter as tk
from tkinter import ttk, messagebox

from agents.osrs_snapshot_agent import SnapshotAgent
from agents.report_agent import ReportAgent
from core.clipboard import copy_text

DEFAULT_CONFIG_PATH = Path("config/project.json")
SNAPSHOT_DIR = Path("data/snapshots")
REPORT_DIR = Path("reports")


class SnapshotApp(tk.Tk):
    MODES = [
        "Auto-detect",
        "main",
        "ironman",
        "hardcore",
        "ultimate",
        "deadman",
        "tournament",
        "seasonal",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.title("OSRS Snapshot Agent")
        self.resizable(False, False)

        self.config_path = DEFAULT_CONFIG_PATH
        self.snapshot_agent = SnapshotAgent(SNAPSHOT_DIR, config_path=self.config_path)
        self.report_agent = ReportAgent(REPORT_DIR, scribe_config=self.config_path)

        self._build_ui()
        self._fetch_thread: threading.Thread | None = None

    def _build_ui(self) -> None:
        padding = {"padx": 10, "pady": 5}

        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="nsew", **padding)

        ttk.Label(frame, text="Player name:").grid(row=0, column=0, sticky="w")
        self.player_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.player_var, width=30).grid(row=0, column=1, sticky="ew")

        ttk.Label(frame, text="Mode:").grid(row=1, column=0, sticky="w")
        self.mode_var = tk.StringVar(value=self.MODES[0])
        ttk.Combobox(
            frame,
            textvariable=self.mode_var,
            values=self.MODES,
            state="readonly",
            width=28,
        ).grid(row=1, column=1, sticky="ew")

        self.fetch_button = ttk.Button(frame, text="Fetch Snapshot", command=self._on_fetch)
        self.fetch_button.grid(row=2, column=0, columnspan=2, pady=(10, 5))

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(frame, textvariable=self.status_var, wraplength=320, justify="left")
        self.status_label.grid(row=3, column=0, columnspan=2, sticky="w")

        frame.columnconfigure(1, weight=1)

    def _on_fetch(self) -> None:
        player = self.player_var.get().strip()
        if not player:
            messagebox.showwarning("Missing player", "Please enter a RuneScape name.")
            return

        if self._fetch_thread and self._fetch_thread.is_alive():
            messagebox.showinfo("Busy", "A snapshot is already in progress.")
            return

        requested_mode = self.mode_var.get()
        if requested_mode.lower().startswith("auto"):
            account = {"name": player}
            mode_text = "Auto-detecting mode..."
        else:
            account = {"name": player, "mode": requested_mode}
            mode_text = f"Mode: {requested_mode}"

        self.fetch_button.configure(state=tk.DISABLED)
        self._set_status(self._decode_unicode_escapes(f"🔍 Fetching snapshot for {player} ({mode_text})"))

        self._fetch_thread = threading.Thread(
            target=self._run_snapshot,
            args=(account,),
            daemon=True,
        )
        self._fetch_thread.start()

    def _run_snapshot(self, account: dict[str, str]) -> None:
        player = account["name"]
        try:
            results = self.snapshot_agent.run([account])
            if not results:
                raise RuntimeError("SnapshotAgent returned no result")
            result = results[0]

            if not result.success or not result.snapshot_path:
                self._set_status(f"Failed to fetch snapshot for {player}: {result.message}")
                return

            report_result = None
            if result.payload:
                report_result = self.report_agent.build_from_payload(
                    payload=result.payload,
                    report_source=result.snapshot_path,
                    delta_summary=result.delta_summary,
                )

            report_path = report_result.report_path if report_result and report_result.success else None
            status_lines = [
                self._decode_unicode_escapes(f"✅ Snapshot saved: {result.snapshot_path}"),
            ]

            # Add mode detection information
            if result.metadata:
                requested_mode = result.metadata.get("requested_mode", "unknown")
                resolved_mode = result.metadata.get("resolved_mode", "unknown")
                if requested_mode != resolved_mode:
                    status_lines.append(self._decode_unicode_escapes(f"🔄 Mode Detection: Requested '{requested_mode}' → Resolved '{resolved_mode}' ✅"))
                else:
                    status_lines.append(self._decode_unicode_escapes(f"✅ Mode confirmed: {resolved_mode}"))

            if report_path:
                status_lines.append(self._decode_unicode_escapes(f"📄 Report saved: {report_path}"))

            clipboard_text = None
            if report_path and report_path.exists():
                try:
                    report_text = report_path.read_text(encoding="utf-8")
                    clipboard_text = f"{report_text}\n\nSnapshot JSON: {result.snapshot_path.resolve()}"
                except OSError:
                    pass

            if clipboard_text and copy_text(clipboard_text):
                status_lines.append(self._decode_unicode_escapes("📋 Report copied to clipboard."))
            elif clipboard_text:
                status_lines.append(self._decode_unicode_escapes("📋 Report ready (clipboard copy unavailable)."))

            self._set_status("\n".join(status_lines))
        except Exception as exc:  # pragma: no cover - GUI surface
            traceback.print_exc()
            self._set_status(self._decode_unicode_escapes(f"❌ Error: {exc}"))
        finally:
            self.after(0, lambda: self.fetch_button.configure(state=tk.NORMAL))

    def _set_status(self, message: str) -> None:
        # Ensure Unicode characters are properly handled for Tkinter
        try:
            # First, decode any literal Unicode escape sequences
            if '\\u' in message:
                decoded_message = codecs.decode(message, 'unicode_escape')
                message = decoded_message

            # Ensure the message is properly encoded for display
            # Tkinter should handle UTF-8 encoded strings properly
            if isinstance(message, str):
                # Make sure the string is clean and displayable
                message = message.encode('utf-8', errors='replace').decode('utf-8')

        except Exception:
            # If anything fails, fall back to a safe version
            pass

        self.after(0, lambda: self.status_var.set(message))

    def _decode_unicode_escapes(self, text: str) -> str:
        """Helper method to decode Unicode escape sequences and handle emoji display.

        Args:
            text: Text that may contain Unicode escape sequences or emoji

        Returns:
            Text with Unicode escapes decoded and emoji handled for display
        """
        try:
            # First, decode any literal Unicode escape sequences
            if '\\u' in text:
                text = codecs.decode(text, 'unicode_escape')

            # Replace emoji with ASCII alternatives if emoji display is problematic
            emoji_replacements = {
                '✅': '[OK]',
                '❌': '[ERROR]',
                '🔍': '[SEARCH]',
                '🔄': '[CHANGE]',
                '📄': '[REPORT]',
                '📋': '[COPY]',
                '🏆': '[MILESTONE]',
                '📊': '[ANALYTICS]',
                '📈': '[PROGRESS]',
                '⚡': '[FAST]',
                '🎯': '[GOAL]'
            }

            # Check if any emoji replacements are needed
            for emoji, replacement in emoji_replacements.items():
                if emoji in text:
                    text = text.replace(emoji, replacement)

        except Exception:
            pass

        return text


def main() -> None:
    app = SnapshotApp()
    app.mainloop()


if __name__ == "__main__":
    main()
