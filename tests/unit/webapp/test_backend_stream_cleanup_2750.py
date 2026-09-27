"""Backend stream readers must stop with their own process (#2750)."""

import asyncio
import logging

import pytest

from argumentation_analysis.webapp import orchestrator


class PendingStream:
    def __init__(self, startup=False):
        self.startup = startup
        self.reading = asyncio.Event()

    def at_eof(self):
        return False

    async def readline(self):
        if self.startup:
            self.startup = False
            return b"Application startup complete\n"
        self.reading.set()
        await asyncio.Event().wait()


class FakeProcess:
    def __init__(self):
        self.pid = 12345
        self.returncode = None
        self.stdout = PendingStream(startup=True)
        self.stderr = PendingStream()
        self.terminated = False

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    async def wait(self):
        return self.returncode


@pytest.mark.parametrize("health_ok", [True, False])
async def test_backend_readers_finish_on_stop_or_failed_health(monkeypatch, health_ok):
    process = FakeProcess()

    async def launch(**kwargs):
        return process

    monkeypatch.setattr(orchestrator, "run_in_activated_env_async", launch)
    manager = orchestrator.MinimalBackendManager({}, logging.getLogger(__name__))
    readers = []

    async def check(url):
        await process.stdout.reading.wait()
        await process.stderr.reading.wait()
        readers.extend(manager._log_tasks)
        return health_ok

    monkeypatch.setattr(manager, "health_check", check)
    result = await asyncio.wait_for(manager.start(port_override=19430), timeout=2)
    assert result["success"] is health_ok
    assert len(readers) == 2
    if health_ok:
        await asyncio.wait_for(manager.stop(), timeout=2)

    assert process.terminated
    assert all(task.done() for task in readers)
    assert manager._log_tasks == []
    assert manager.process is None


async def test_failed_port_readers_finish_before_next_port(monkeypatch):
    processes = [FakeProcess(), FakeProcess()]
    manager = orchestrator.MinimalBackendManager({}, logging.getLogger(__name__))
    readers_by_attempt = []

    async def launch(**kwargs):
        return processes.pop(0)

    async def check(url):
        process = manager.process
        await process.stdout.reading.wait()
        await process.stderr.reading.wait()
        readers_by_attempt.append(list(manager._log_tasks))
        return len(readers_by_attempt) == 2

    monkeypatch.setattr(orchestrator, "run_in_activated_env_async", launch)
    monkeypatch.setattr(manager, "health_check", check)

    first = await asyncio.wait_for(manager.start(port_override=19430), timeout=2)
    assert not first["success"]
    assert all(task.done() for task in readers_by_attempt[0])
    assert manager.process is None

    second = await asyncio.wait_for(manager.start(port_override=19431), timeout=2)
    assert second["success"]
    assert all(not task.done() for task in readers_by_attempt[1])
    await asyncio.wait_for(manager.stop(), timeout=2)
    assert all(task.done() for task in readers_by_attempt[1])


async def test_stop_cancels_readers_after_process_already_exited():
    manager = orchestrator.MinimalBackendManager({}, logging.getLogger(__name__))
    process = FakeProcess()
    process.returncode = 1
    process.stdout.startup = False
    manager.process = process
    readers = [
        asyncio.create_task(process.stdout.readline()),
        asyncio.create_task(process.stderr.readline()),
    ]
    manager._log_tasks = readers
    await process.stdout.reading.wait()
    await process.stderr.reading.wait()

    await asyncio.wait_for(manager.stop(), timeout=2)

    assert all(task.cancelled() for task in readers)
    assert manager._log_tasks == []
    assert manager.process is None
    assert not process.terminated
