"""Progress reporting and logging for IT Glue migration.

Provides rich console output with progress bars, phase tracking,
warnings/errors display, and optional file logging.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from types import TracebackType


class Phase(Enum):
    """Migration phases in execution order."""

    ORGANIZATIONS = "Organizations"
    LOCATIONS = "Locations"
    CONFIGURATION_TYPES = "Configuration Types"
    CONFIGURATIONS = "Configurations"
    CUSTOM_ASSET_TYPES = "Custom Asset Types"
    CUSTOM_ASSETS = "Custom Assets"
    DOCUMENTS = "Documents"
    PASSWORDS = "Passwords"
    RELATIONSHIPS = "Relationships"


PHASE_ORDER: list[Phase] = list(Phase)


@dataclass
class PhaseResult:
    """Result of a completed phase."""

    phase: Phase
    total: int
    succeeded: int
    failed: int
    skipped: int
    disabled: int  # Items created with is_enabled=False
    duration_seconds: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total == 0:
            return 100.0
        return (self.succeeded / self.total) * 100


@dataclass
class MigrationSummary:
    """Summary of the entire migration."""

    phases: list[PhaseResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None

    @property
    def total_duration_seconds(self) -> float:
        """Total migration duration in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    @property
    def total_items(self) -> int:
        """Total items processed across all phases."""
        return sum(p.total for p in self.phases)

    @property
    def total_succeeded(self) -> int:
        """Total items succeeded across all phases."""
        return sum(p.succeeded for p in self.phases)

    @property
    def total_failed(self) -> int:
        """Total items failed across all phases."""
        return sum(p.failed for p in self.phases)


def format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


class ProgressReporter:
    """Rich-based progress reporter for migration operations.

    Displays progress bars, phase tracking, warnings/errors,
    and elapsed time in the console.
    """

    def __init__(
        self,
        console: Console | None = None,
        log_file: Path | str | None = None,
        verbose: bool = False,
    ) -> None:
        """Initialize the progress reporter.

        Args:
            console: Rich console instance (creates new if None).
            log_file: Optional path to log file.
            verbose: If True, show detailed operation logs.
        """
        self.console = console or Console()
        self.verbose = verbose
        self._log_file: TextIO | None = None
        self._logger: logging.Logger | None = None

        # State tracking
        self._summary = MigrationSummary()
        self._current_phase: Phase | None = None
        self._current_phase_index: int = 0
        self._current_total: int = 0
        self._current_succeeded: int = 0
        self._current_failed: int = 0
        self._current_skipped: int = 0
        self._current_disabled: int = 0  # Track items created as disabled
        self._phase_start_time: float = 0.0
        self._current_item: str = ""

        # Rich live display
        self._live: Live | None = None

        # Setup file logging if requested
        if log_file:
            self._setup_file_logging(Path(log_file))

    def _setup_file_logging(self, log_path: Path) -> None:
        """Configure file logging."""
        log_path.parent.mkdir(parents=True, exist_ok=True)

        self._logger = logging.getLogger("itglue_migrate")
        self._logger.setLevel(logging.DEBUG)

        # File handler
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)

        self._log("Migration started")

    def _log(self, message: str, level: str = "INFO") -> None:
        """Write to log file if configured."""
        if self._logger:
            log_method = getattr(self._logger, level.lower(), self._logger.info)
            log_method(message)

    def _build_display(self) -> Panel:
        """Build the live display panel."""
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="left")

        # Phase progress line
        if self._current_phase:
            phase_num = self._current_phase_index + 1
            total_phases = len(PHASE_ORDER)
            current = self._current_succeeded + self._current_failed + self._current_skipped
            total = self._current_total

            if total > 0:
                pct = (current / total) * 100
                status = "..." if current < total else "[green]done[/green]"
            else:
                pct = 0
                status = "[dim]waiting[/dim]"

            phase_text = Text()
            phase_text.append(f"[{phase_num}/{total_phases}] ", style="bold cyan")
            phase_text.append(f"{self._current_phase.value}: ", style="bold")
            phase_text.append(f"{current}/{total} ", style="white")
            phase_text.append(f"({pct:.0f}%) ", style="dim")
            phase_text.append(status)

            table.add_row(phase_text)

        # Completed phases
        for result in self._summary.phases:
            phase_idx = PHASE_ORDER.index(result.phase) + 1
            total_phases = len(PHASE_ORDER)

            phase_line = Text()
            phase_line.append(f"[{phase_idx}/{total_phases}] ", style="dim cyan")
            phase_line.append(f"{result.phase.value}: ", style="dim")
            phase_line.append(f"{result.succeeded}/{result.total} ", style="dim")
            if result.failed == 0:
                phase_line.append("OK", style="green")
            else:
                phase_line.append("!", style="yellow")

            table.add_row(phase_line)

        # Current item being processed
        if self._current_item:
            current_line = Text()
            current_line.append("Current: ", style="dim")
            current_line.append(self._current_item, style="italic")
            table.add_row(current_line)

        # Warnings summary
        if self._summary.warnings:
            table.add_row("")
            table.add_row(Text("Warnings:", style="yellow bold"))
            # Show last 3 warnings
            for warning in self._summary.warnings[-3:]:
                warning_line = Text()
                warning_line.append("  - ", style="yellow")
                warning_line.append(warning, style="yellow")
                table.add_row(warning_line)
            if len(self._summary.warnings) > 3:
                table.add_row(
                    Text(f"  ... and {len(self._summary.warnings) - 3} more", style="dim yellow")
                )

        # Errors summary
        if self._summary.errors:
            table.add_row("")
            table.add_row(Text("Errors:", style="red bold"))
            # Show last 3 errors
            for error in self._summary.errors[-3:]:
                error_line = Text()
                error_line.append("  - ", style="red")
                error_line.append(error, style="red")
                table.add_row(error_line)
            if len(self._summary.errors) > 3:
                table.add_row(
                    Text(f"  ... and {len(self._summary.errors) - 3} more", style="dim red")
                )

        # Elapsed time
        elapsed = self._summary.total_duration_seconds
        table.add_row("")
        table.add_row(Text(f"Elapsed: {format_duration(elapsed)}", style="dim"))

        return Panel(table, title="[bold]IT Glue Migration[/bold]", border_style="blue")

    def start(self) -> None:
        """Start the progress display."""
        self._summary = MigrationSummary()
        self._live = Live(
            self._build_display(),
            console=self.console,
            refresh_per_second=4,
            transient=False,
        )
        self._live.start()

    def stop(self) -> None:
        """Stop the progress display."""
        if self._live:
            self._live.update(self._build_display())
            self._live.stop()
            self._live = None

        self._summary.end_time = datetime.now()
        self._log("Migration completed")

    def start_phase(self, phase: Phase, total: int) -> None:
        """Start a new migration phase.

        Args:
            phase: The phase to start.
            total: Total number of items to process in this phase.
        """
        self._current_phase = phase
        self._current_phase_index = PHASE_ORDER.index(phase)
        self._current_total = total
        self._current_succeeded = 0
        self._current_failed = 0
        self._current_skipped = 0
        self._current_disabled = 0
        self._phase_start_time = time.monotonic()
        self._current_item = ""

        self._log(f"Starting phase: {phase.value} ({total} items)")

        if self._live:
            self._live.update(self._build_display())

    def update_progress(
        self,
        succeeded: int = 0,
        failed: int = 0,
        skipped: int = 0,
        disabled: int = 0,
        current_item: str = "",
    ) -> None:
        """Update progress within the current phase.

        Args:
            succeeded: Number of newly succeeded items.
            failed: Number of newly failed items.
            skipped: Number of newly skipped items.
            disabled: Number of items created as disabled (is_enabled=False).
            current_item: Description of current item being processed.
        """
        self._current_succeeded += succeeded
        self._current_failed += failed
        self._current_skipped += skipped
        self._current_disabled += disabled

        if current_item:
            self._current_item = current_item

        if self.verbose and current_item:
            self._log(f"Processing: {current_item}")

        if self._live:
            self._live.update(self._build_display())

    def set_current_item(self, item: str) -> None:
        """Set the current item being processed.

        Args:
            item: Description of the current item.
        """
        self._current_item = item
        if self._live:
            self._live.update(self._build_display())

    def complete_phase(self) -> PhaseResult:
        """Complete the current phase and return its result.

        Returns:
            PhaseResult with statistics for the completed phase.
        """
        if not self._current_phase:
            raise RuntimeError("No phase in progress")

        duration = time.monotonic() - self._phase_start_time

        result = PhaseResult(
            phase=self._current_phase,
            total=self._current_total,
            succeeded=self._current_succeeded,
            failed=self._current_failed,
            skipped=self._current_skipped,
            disabled=self._current_disabled,
            duration_seconds=duration,
        )

        self._summary.phases.append(result)
        self._current_item = ""

        disabled_info = f", {result.disabled} disabled" if result.disabled > 0 else ""
        self._log(
            f"Completed phase: {self._current_phase.value} - "
            f"{result.succeeded}/{result.total} succeeded, "
            f"{result.failed} failed, {result.skipped} skipped{disabled_info} "
            f"({format_duration(duration)})"
        )

        self._current_phase = None

        if self._live:
            self._live.update(self._build_display())

        return result

    def warning(self, message: str) -> None:
        """Record and display a warning.

        Args:
            message: Warning message.
        """
        self._summary.warnings.append(message)
        self._log(f"Warning: {message}", level="WARNING")

        if self._live:
            self._live.update(self._build_display())

    def error(self, message: str) -> None:
        """Record and display an error.

        Args:
            message: Error message.
        """
        self._summary.errors.append(message)
        self._log(f"Error: {message}", level="ERROR")

        if self._live:
            self._live.update(self._build_display())

    def info(self, message: str) -> None:
        """Record and display an informational message.

        Args:
            message: Info message.
        """
        self._log(message, level="INFO")

        if self._live:
            self._live.update(self._build_display())

    def get_summary(self) -> MigrationSummary:
        """Get the migration summary.

        Returns:
            MigrationSummary with all phase results, warnings, and errors.
        """
        return self._summary

    def print_final_summary(self) -> None:
        """Print a final summary after migration completes."""
        summary = self._summary

        # Build summary table
        table = Table(title="Migration Summary", show_header=True, header_style="bold")
        table.add_column("Phase", style="cyan")
        table.add_column("Total", justify="right")
        table.add_column("Succeeded", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Skipped", justify="right", style="yellow")
        table.add_column("Disabled", justify="right", style="dim yellow")
        table.add_column("Duration", justify="right", style="dim")

        for result in summary.phases:
            disabled_str = str(result.disabled) if result.disabled > 0 else "-"
            table.add_row(
                result.phase.value,
                str(result.total),
                str(result.succeeded),
                str(result.failed),
                str(result.skipped),
                disabled_str,
                format_duration(result.duration_seconds),
            )

        # Totals row
        total_disabled = sum(p.disabled for p in summary.phases)
        disabled_total_str = str(total_disabled) if total_disabled > 0 else "-"
        table.add_section()
        table.add_row(
            "[bold]Total[/bold]",
            f"[bold]{summary.total_items}[/bold]",
            f"[bold green]{summary.total_succeeded}[/bold green]",
            f"[bold red]{summary.total_failed}[/bold red]",
            f"[bold yellow]{sum(p.skipped for p in summary.phases)}[/bold yellow]",
            f"[bold dim yellow]{disabled_total_str}[/bold dim yellow]",
            f"[bold]{format_duration(summary.total_duration_seconds)}[/bold]",
        )

        self.console.print()
        self.console.print(table)

        # Warnings
        if summary.warnings:
            self.console.print()
            self.console.print(f"[yellow bold]Warnings ({len(summary.warnings)}):[/yellow bold]")
            for warning in summary.warnings:
                self.console.print(f"  [yellow]-[/yellow] {warning}")

        # Errors
        if summary.errors:
            self.console.print()
            self.console.print(f"[red bold]Errors ({len(summary.errors)}):[/red bold]")
            for err in summary.errors:
                self.console.print(f"  [red]-[/red] {err}")

        # Final status
        self.console.print()
        if summary.total_failed == 0 and not summary.errors:
            self.console.print("[green bold]Migration completed successfully![/green bold]")
        elif summary.total_failed > 0 or summary.errors:
            self.console.print(
                "[yellow bold]Migration completed with warnings/errors.[/yellow bold]"
            )

    def __enter__(self) -> ProgressReporter:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.stop()


class SimpleProgressReporter:
    """Simple progress reporter without live updates.

    Useful for non-interactive environments or testing.
    """

    def __init__(
        self,
        console: Console | None = None,
        log_file: Path | str | None = None,
        verbose: bool = False,
    ) -> None:
        """Initialize the simple progress reporter.

        Args:
            console: Rich console instance.
            log_file: Optional path to log file.
            verbose: If True, show detailed operation logs.
        """
        self.console = console or Console()
        self.verbose = verbose
        self._summary = MigrationSummary()
        self._current_phase: Phase | None = None
        self._current_phase_index: int = 0
        self._phase_start_time: float = 0.0
        self._current_total: int = 0
        self._current_succeeded: int = 0
        self._current_failed: int = 0
        self._current_skipped: int = 0
        self._current_disabled: int = 0
        self._logger: logging.Logger | None = None

        if log_file:
            self._setup_file_logging(Path(log_file))

    def _setup_file_logging(self, log_path: Path) -> None:
        """Configure file logging."""
        log_path.parent.mkdir(parents=True, exist_ok=True)

        self._logger = logging.getLogger("itglue_migrate_simple")
        self._logger.setLevel(logging.DEBUG)

        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)

    def _log(self, message: str, level: str = "INFO") -> None:
        """Write to log file if configured."""
        if self._logger:
            log_method = getattr(self._logger, level.lower(), self._logger.info)
            log_method(message)

    def start(self) -> None:
        """Start the migration."""
        self._summary = MigrationSummary()
        self.console.print("[bold blue]IT Glue Migration[/bold blue]")
        self.console.print()

    def stop(self) -> None:
        """Stop the migration."""
        self._summary.end_time = datetime.now()

    def start_phase(self, phase: Phase, total: int) -> None:
        """Start a new phase."""
        self._current_phase = phase
        self._current_phase_index = PHASE_ORDER.index(phase)
        self._current_total = total
        self._current_succeeded = 0
        self._current_failed = 0
        self._current_skipped = 0
        self._current_disabled = 0
        self._phase_start_time = time.monotonic()

        phase_num = self._current_phase_index + 1
        total_phases = len(PHASE_ORDER)
        self.console.print(f"[cyan][{phase_num}/{total_phases}][/cyan] {phase.value} ({total} items)...")

        self._log(f"Starting phase: {phase.value} ({total} items)")

    def update_progress(
        self,
        succeeded: int = 0,
        failed: int = 0,
        skipped: int = 0,
        disabled: int = 0,
        current_item: str = "",
    ) -> None:
        """Update progress."""
        self._current_succeeded += succeeded
        self._current_failed += failed
        self._current_skipped += skipped
        self._current_disabled += disabled

        if self.verbose and current_item:
            self.console.print(f"  [dim]Processing: {current_item}[/dim]")
            self._log(f"Processing: {current_item}")

    def set_current_item(self, item: str) -> None:
        """Set current item."""
        if self.verbose:
            self.console.print(f"  [dim]Processing: {item}[/dim]")

    def complete_phase(self) -> PhaseResult:
        """Complete the current phase."""
        if not self._current_phase:
            raise RuntimeError("No phase in progress")

        duration = time.monotonic() - self._phase_start_time

        result = PhaseResult(
            phase=self._current_phase,
            total=self._current_total,
            succeeded=self._current_succeeded,
            failed=self._current_failed,
            skipped=self._current_skipped,
            disabled=self._current_disabled,
            duration_seconds=duration,
        )

        self._summary.phases.append(result)

        status = "[green]OK[/green]" if result.failed == 0 else f"[yellow]{result.failed} failed[/yellow]"
        disabled_info = f", {result.disabled} disabled" if result.disabled > 0 else ""
        self.console.print(
            f"  Completed: {result.succeeded}/{result.total} {status}{disabled_info} ({format_duration(duration)})"
        )

        self._log(
            f"Completed phase: {self._current_phase.value} - "
            f"{result.succeeded}/{result.total} succeeded"
        )

        self._current_phase = None
        return result

    def warning(self, message: str) -> None:
        """Record a warning."""
        self._summary.warnings.append(message)
        self.console.print(f"  [yellow]Warning: {message}[/yellow]")
        self._log(f"Warning: {message}", level="WARNING")

    def error(self, message: str) -> None:
        """Record an error."""
        self._summary.errors.append(message)
        self.console.print(f"  [red]Error: {message}[/red]")
        self._log(f"Error: {message}", level="ERROR")

    def info(self, message: str) -> None:
        """Record an informational message."""
        self.console.print(f"  [dim]{message}[/dim]")
        self._log(message, level="INFO")

    def get_summary(self) -> MigrationSummary:
        """Get the migration summary."""
        return self._summary

    def print_final_summary(self) -> None:
        """Print final summary."""
        # Delegate to the same summary display
        summary = self._summary

        table = Table(title="Migration Summary", show_header=True, header_style="bold")
        table.add_column("Phase", style="cyan")
        table.add_column("Total", justify="right")
        table.add_column("Succeeded", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Skipped", justify="right", style="yellow")
        table.add_column("Disabled", justify="right", style="dim yellow")
        table.add_column("Duration", justify="right", style="dim")

        for result in summary.phases:
            disabled_str = str(result.disabled) if result.disabled > 0 else "-"
            table.add_row(
                result.phase.value,
                str(result.total),
                str(result.succeeded),
                str(result.failed),
                str(result.skipped),
                disabled_str,
                format_duration(result.duration_seconds),
            )

        total_disabled = sum(p.disabled for p in summary.phases)
        disabled_total_str = str(total_disabled) if total_disabled > 0 else "-"
        table.add_section()
        table.add_row(
            "[bold]Total[/bold]",
            f"[bold]{summary.total_items}[/bold]",
            f"[bold green]{summary.total_succeeded}[/bold green]",
            f"[bold red]{summary.total_failed}[/bold red]",
            f"[bold yellow]{sum(p.skipped for p in summary.phases)}[/bold yellow]",
            f"[bold dim yellow]{disabled_total_str}[/bold dim yellow]",
            f"[bold]{format_duration(summary.total_duration_seconds)}[/bold]",
        )

        self.console.print()
        self.console.print(table)

        if summary.warnings:
            self.console.print()
            self.console.print(f"[yellow bold]Warnings ({len(summary.warnings)}):[/yellow bold]")
            for warning in summary.warnings:
                self.console.print(f"  [yellow]-[/yellow] {warning}")

        if summary.errors:
            self.console.print()
            self.console.print(f"[red bold]Errors ({len(summary.errors)}):[/red bold]")
            for err in summary.errors:
                self.console.print(f"  [red]-[/red] {err}")

        self.console.print()
        if summary.total_failed == 0 and not summary.errors:
            self.console.print("[green bold]Migration completed successfully![/green bold]")
        else:
            self.console.print(
                "[yellow bold]Migration completed with warnings/errors.[/yellow bold]"
            )

    def __enter__(self) -> SimpleProgressReporter:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.stop()


def create_progress_reporter(
    console: Console | None = None,
    log_file: Path | str | None = None,
    verbose: bool = False,
    simple: bool = False,
) -> ProgressReporter | SimpleProgressReporter:
    """Factory function to create a progress reporter.

    Args:
        console: Rich console instance.
        log_file: Optional path to log file.
        verbose: If True, show detailed operation logs.
        simple: If True, use simple reporter without live updates.

    Returns:
        ProgressReporter or SimpleProgressReporter instance.
    """
    if simple:
        return SimpleProgressReporter(console=console, log_file=log_file, verbose=verbose)
    return ProgressReporter(console=console, log_file=log_file, verbose=verbose)
