"""
conftest.py
─────────────────────────────────────────────────────────────────────
Pytest shared fixtures for VeriDrive regression test suite.

Key design decisions:
  1. Firebase is mocked out entirely in CI — tests must not require a
     live Firestore connection. The mock is injected at import time via
     monkeypatch before any test module imports firebase_service.

  2. The RiskScoringEngine is loaded ONCE at session scope. Loading two
     sklearn models per test would make the suite ~10× slower and adds
     no isolation benefit (models are read-only during inference).

  3. Model paths are configurable via CLI options so the same suite can
     be run against both the current model and a candidate new model:
       pytest --tox-model=toxicity_model_v3.pkl
       pytest --tox-model=toxicity_model_candidate.pkl
"""

import os
import sys
import pytest

# ══════════════════════════════════════════════════════════════════════
# CLI OPTIONS
# ══════════════════════════════════════════════════════════════════════

def pytest_addoption(parser):
    parser.addoption(
        "--tox-model",
        action="store",
        default="toxicity_model_v3.pkl",
        help="Path to toxicity model .pkl to validate (default: toxicity_model_v3.pkl)"
    )
    parser.addoption(
        "--sent-model",
        action="store",
        default=os.path.join("models", "sentiment_model.joblib"),
        help="Path to sentiment model .joblib"
    )
    parser.addoption(
        "--sent-vec",
        action="store",
        default=os.path.join("models", "sentiment_vectorizer.joblib"),
        help="Path to sentiment vectorizer .joblib"
    )


# ══════════════════════════════════════════════════════════════════════
# FIREBASE ISOLATION
# ══════════════════════════════════════════════════════════════════════
# In CI there is no Firebase project. We mock the entire firebase_service
# module before it is imported by main3.py or any test module.

class _MockFirestore:
    """Null-object implementation of all firebase_service functions."""

    @staticmethod
    def create_analysis_record(data): return "mock-record-id"

    @staticmethod
    def get_all_records(): return []

    @staticmethod
    def get_record(record_id): return None

    @staticmethod
    def update_record(record_id, updates): return True

    @staticmethod
    def get_user_records(user_id): return []

    @staticmethod
    def create_notification(data): return "mock-notif-id"

    @staticmethod
    def get_user_notifications(user_id): return []

    @staticmethod
    def mark_notification_read(notification_id): return True

    @staticmethod
    def get_unread_count(user_id): return 0


def _install_firebase_mock():
    """
    Inject a mock firebase_service module into sys.modules before any
    test file imports it. This ensures Firebase SDK is never initialised
    in CI where no credentials exist.
    """
    import types
    mock_module = types.ModuleType("firebase_service")
    fs = _MockFirestore()
    mock_module.create_analysis_record  = fs.create_analysis_record
    mock_module.get_all_records         = fs.get_all_records
    mock_module.get_record              = fs.get_record
    mock_module.update_record           = fs.update_record
    mock_module.get_user_records        = fs.get_user_records
    mock_module.create_notification     = fs.create_notification
    mock_module.get_user_notifications  = fs.get_user_notifications
    mock_module.mark_notification_read  = fs.mark_notification_read
    mock_module.get_unread_count        = fs.get_unread_count
    sys.modules["firebase_service"]     = mock_module
    sys.modules["firebase_admin"]       = types.ModuleType("firebase_admin")

# Install mock immediately when conftest.py is collected
_install_firebase_mock()


# ══════════════════════════════════════════════════════════════════════
# SESSION-SCOPED ENGINE FIXTURE
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def tox_model_path(request):
    return request.config.getoption("--tox-model")

@pytest.fixture(scope="session")
def sent_model_path(request):
    return request.config.getoption("--sent-model")

@pytest.fixture(scope="session")
def sent_vec_path(request):
    return request.config.getoption("--sent-vec")


@pytest.fixture(scope="session")
def engine(tox_model_path, sent_model_path, sent_vec_path):
    """
    Load RiskScoringEngine once for the entire test session.
    Fails fast with a clear error if model files are missing — this
    surfaces the real problem (artifact not available) rather than a
    confusing ImportError downstream.
    """
    missing = [p for p in [tox_model_path, sent_model_path, sent_vec_path]
               if not os.path.exists(p)]
    if missing:
        pytest.fail(
            f"Model artifact(s) not found: {missing}\n"
            "In CI, ensure the artifact download step ran before pytest.\n"
            "Locally, run model1.py and train_sentiment.py first."
        )

    from risk_engine import RiskScoringEngine
    return RiskScoringEngine(tox_model_path, sent_model_path, sent_vec_path)