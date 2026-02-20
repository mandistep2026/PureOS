"""
PureOS Cron/Scheduler
Simple cron-like job scheduler for running commands at specified intervals.
Uses only Python standard library.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum


class CronJobState(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"


@dataclass
class CronJob:
    """Represents a scheduled job."""
    job_id: int
    name: str
    command: str
    interval: float          # seconds between runs
    next_run: float          # epoch time of next execution
    state: CronJobState = CronJobState.ACTIVE
    run_count: int = 0
    last_run: Optional[float] = None
    last_exit_code: Optional[int] = None
    max_runs: Optional[int] = None   # None = run forever
    created_at: float = field(default_factory=time.time)

    def is_due(self) -> bool:
        return self.state == CronJobState.ACTIVE and time.time() >= self.next_run

    def schedule_next(self) -> None:
        self.next_run = time.time() + self.interval
        self.run_count += 1
        self.last_run = time.time()
        if self.max_runs is not None and self.run_count >= self.max_runs:
            self.state = CronJobState.EXPIRED

    def __str__(self) -> str:
        interval_str = _fmt_interval(self.interval)
        next_str = time.strftime('%H:%M:%S', time.localtime(self.next_run))
        last_str = time.strftime('%H:%M:%S', time.localtime(self.last_run)) if self.last_run else "never"
        return (f"[{self.job_id}] {self.name:<20} every {interval_str:<10} "
                f"runs={self.run_count} last={last_str} next={next_str} "
                f"state={self.state.value}")


def _fmt_interval(seconds: float) -> str:
    """Format interval as human-readable string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    return f"{int(seconds // 3600)}h"


class CronScheduler:
    """Manages and runs scheduled cron jobs."""

    def __init__(self, shell=None):
        self.shell = shell
        self.jobs: Dict[int, CronJob] = {}
        self.next_id = 1
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        """Start the cron scheduler background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the cron scheduler."""
        self._running = False

    def add_job(self, name: str, command: str, interval: float,
                max_runs: Optional[int] = None, delay: float = 0.0) -> CronJob:
        """Add a new cron job.

        Args:
            name: Human-readable job name.
            command: Shell command string to execute.
            interval: Seconds between runs.
            max_runs: Maximum number of executions (None = unlimited).
            delay: Seconds to wait before first run (0 = run at interval from now).
        """
        with self._lock:
            job_id = self.next_id
            self.next_id += 1
            first_run = time.time() + (delay if delay > 0 else interval)
            job = CronJob(
                job_id=job_id,
                name=name,
                command=command,
                interval=interval,
                next_run=first_run,
                max_runs=max_runs,
            )
            self.jobs[job_id] = job
            return job

    def remove_job(self, job_id: int) -> bool:
        with self._lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                return True
            return False

    def pause_job(self, job_id: int) -> bool:
        with self._lock:
            job = self.jobs.get(job_id)
            if job and job.state == CronJobState.ACTIVE:
                job.state = CronJobState.PAUSED
                return True
            return False

    def resume_job(self, job_id: int) -> bool:
        with self._lock:
            job = self.jobs.get(job_id)
            if job and job.state == CronJobState.PAUSED:
                job.state = CronJobState.ACTIVE
                job.next_run = time.time() + job.interval
                return True
            return False

    def list_jobs(self) -> List[CronJob]:
        with self._lock:
            return list(self.jobs.values())

    def get_job(self, job_id: int) -> Optional[CronJob]:
        return self.jobs.get(job_id)

    def _loop(self) -> None:
        """Main scheduler loop — runs every second."""
        while self._running:
            due: List[CronJob] = []
            with self._lock:
                for job in list(self.jobs.values()):
                    if job.is_due():
                        due.append(job)
                        job.schedule_next()

            for job in due:
                self._run_job(job)

            time.sleep(1.0)

    def _run_job(self, job: CronJob) -> None:
        """Execute a cron job in a background thread."""
        def _execute():
            if self.shell is not None:
                try:
                    rc = self.shell.execute(job.command, save_to_history=False)
                    with self._lock:
                        if job.job_id in self.jobs:
                            self.jobs[job.job_id].last_exit_code = rc
                except Exception:
                    with self._lock:
                        if job.job_id in self.jobs:
                            self.jobs[job.job_id].last_exit_code = 1

        t = threading.Thread(target=_execute, daemon=True)
        t.start()
