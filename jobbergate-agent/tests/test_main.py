import logging

import jobbergate_agent.main as main_mod


def test_main_logs_and_handles_exceptions(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    # Patch dependencies
    monkeypatch.setattr(main_mod, "init_sentry", lambda: None)
    # Patch run_scheduler to avoid actually starting the scheduler
    monkeypatch.setattr(main_mod, "run_scheduler", lambda: "fake-coro")

    # Patch asyncio.Runner
    class DummyRunner:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def run(self, coro):
            raise KeyboardInterrupt()

    monkeypatch.setattr(main_mod.asyncio, "Runner", lambda: DummyRunner())
    main_mod.main()
    assert "Starting Jobbergate-agent" in caplog.text
    assert "Jobbergate-agent is shutting down" in caplog.text
    assert "Jobbergate-agent has been stopped" in caplog.text
