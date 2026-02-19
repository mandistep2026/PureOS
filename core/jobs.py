"""
PureOS Job Control
Manage background and stopped jobs.
Uses only Python standard library.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class JobState(Enum):
    RUNNING = "Running"
    STOPPED = "Stopped"
    DONE = "Done"


@dataclass
class Job:
    """Represents a background or stopped job."""
    job_id: int
    pid: int
    name: str
    state: JobState
    command: str
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    exit_code: Optional[int] = None
    output: List[str] = field(default_factory=list)
    thread: Optional[threading.Thread] = None
    process: Any = None
    
    def __str__(self) -> str:
        """Format job for display."""
        status = self.state.value
        if self.state == JobState.DONE:
            if self.exit_code == 0:
                status = "Done"
            else:
                status = f"Done(exit:{self.exit_code})"
        return f"[{self.job_id}]  {status:12}  {self.command}"


class JobManager:
    """Manages background and stopped jobs."""
    
    def __init__(self, kernel=None):
        self.kernel = kernel
        self.jobs: Dict[int, Job] = {}
        self.next_job_id = 1
        self.current_job: Optional[int] = None
        self.previous_job: Optional[int] = None
        self._lock = threading.Lock()
        self._output_lock = threading.Lock()
    
    def create_job(self, pid: int, name: str, command: str, 
                   thread: Optional[threading.Thread] = None,
                   process: Any = None) -> Job:
        """Create a new job and return it."""
        with self._lock:
            job_id = self.next_job_id
            self.next_job_id += 1
            
            job = Job(
                job_id=job_id,
                pid=pid,
                name=name,
                state=JobState.RUNNING,
                command=command,
                thread=thread,
                process=process
            )
            
            self.jobs[job_id] = job
            self._update_current_previous(job_id)
            
            return job
    
    def _update_current_previous(self, new_job_id: int) -> None:
        """Update current and previous job pointers."""
        if self.current_job != new_job_id:
            self.previous_job = self.current_job
            self.current_job = new_job_id
    
    def get_job(self, job_id: int) -> Optional[Job]:
        """Get a job by its ID."""
        return self.jobs.get(job_id)
    
    def get_job_by_pid(self, pid: int) -> Optional[Job]:
        """Get a job by its PID."""
        for job in self.jobs.values():
            if job.pid == pid:
                return job
        return None
    
    def list_jobs(self, include_done: bool = False) -> List[Job]:
        """List all jobs, optionally including completed ones."""
        with self._lock:
            jobs = []
            for job in sorted(self.jobs.values(), key=lambda j: j.job_id):
                if include_done or job.state != JobState.DONE:
                    jobs.append(job)
            return jobs
    
    def stop_job(self, job_id: int) -> bool:
        """Stop (suspend) a running job."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
            
            if job.state != JobState.RUNNING:
                return False
            
            job.state = JobState.STOPPED
            
            if self.kernel and job.pid:
                self.kernel.suspend_process(job.pid)
            
            self._update_current_previous(job_id)
            return True
    
    def continue_job(self, job_id: int, background: bool = False) -> bool:
        """Continue a stopped job."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
            
            if job.state != JobState.STOPPED:
                return False
            
            job.state = JobState.RUNNING
            
            if self.kernel and job.pid:
                self.kernel.resume_process(job.pid)
            
            if not background:
                self._update_current_previous(job_id)
            
            return True
    
    def finish_job(self, job_id: int, exit_code: int = 0) -> None:
        """Mark a job as finished."""
        with self._lock:
            job = self.jobs.get(job_id)
            if job:
                job.state = JobState.DONE
                job.finished_at = time.time()
                job.exit_code = exit_code
                
                if self.current_job == job_id:
                    self.current_job = self.previous_job
    
    def remove_job(self, job_id: int) -> bool:
        """Remove a job from the job table."""
        with self._lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                if self.current_job == job_id:
                    self.current_job = self._find_new_current()
                return True
            return False
    
    def _find_new_current(self) -> Optional[int]:
        """Find a new current job after removal."""
        stopped_jobs = [j for j in self.jobs.values() if j.state == JobState.STOPPED]
        if stopped_jobs:
            return max(stopped_jobs, key=lambda j: j.job_id).job_id
        running_jobs = [j for j in self.jobs.values() if j.state == JobState.RUNNING]
        if running_jobs:
            return max(running_jobs, key=lambda j: j.job_id).job_id
        return None
    
    def add_output(self, job_id: int, output: str) -> None:
        """Add output to a job's buffer."""
        with self._lock:
            job = self.jobs.get(job_id)
            if job:
                with self._output_lock:
                    job.output.append(output)
    
    def get_output(self, job_id: int) -> str:
        """Get all output from a job."""
        with self._lock:
            job = self.jobs.get(job_id)
            if job:
                with self._output_lock:
                    return ''.join(job.output)
            return ""
    
    def get_current_job(self) -> Optional[Job]:
        """Get the current job (marked with +)."""
        if self.current_job:
            return self.jobs.get(self.current_job)
        return None
    
    def get_previous_job(self) -> Optional[Job]:
        """Get the previous job (marked with -)."""
        if self.previous_job:
            return self.jobs.get(self.previous_job)
        return None
    
    def format_jobs_list(self, show_pid: bool = False) -> List[str]:
        """Format jobs list for display."""
        lines = []
        current = self.current_job
        previous = self.previous_job
        
        for job in self.list_jobs():
            marker = " "
            if job.job_id == current:
                marker = "+"
            elif job.job_id == previous:
                marker = "-"
            
            if show_pid:
                lines.append(f"[{job.job_id}]{marker}  {job.pid:>6}  {job.state.value:12}  {job.command}")
            else:
                lines.append(f"[{job.job_id}]{marker}  {job.state.value:12}  {job.command}")
        
        return lines
    
    def parse_job_spec(self, spec: str) -> Optional[Job]:
        """Parse a job specification like %1, %+, %- or %%."""
        if not spec:
            return self.get_current_job()
        
        if not spec.startswith('%'):
            return None
        
        spec = spec[1:]
        
        if spec == '' or spec == '+':
            return self.get_current_job()
        
        if spec == '-':
            return self.get_previous_job()
        
        if spec == '%':
            return self.get_current_job()
        
        try:
            job_id = int(spec)
            return self.get_job(job_id)
        except ValueError:
            pass
        
        for job in self.jobs.values():
            if job.name == spec or job.command.startswith(spec):
                return job
        
        return None
    
    def cleanup_finished(self) -> List[Job]:
        """Remove finished jobs and return list of removed jobs."""
        removed = []
        with self._lock:
            to_remove = [jid for jid, job in self.jobs.items() 
                        if job.state == JobState.DONE]
            for jid in to_remove:
                removed.append(self.jobs[jid])
                del self.jobs[jid]
        return removed
    
    def notify_completed(self) -> List[str]:
        """Check for completed jobs and return notification messages."""
        notifications = []
        
        with self._lock:
            for job in list(self.jobs.values()):
                if job.thread and not job.thread.is_alive():
                    if job.state == JobState.RUNNING:
                        job.state = JobState.DONE
                        job.finished_at = time.time()
                        job.exit_code = 0
                        notifications.append(f"\n[{job.job_id}]+  Done                    {job.command}")
        
        return notifications
