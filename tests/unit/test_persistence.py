import sys
from pathlib import Path
import tempfile
import os

# Add backend directory to sys.path
backend_dir = (Path(__file__).resolve().parents[2] / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models import (
    User,
    Collection,
    Document,
    DocumentVersion,
    DocumentChunk,
    Goal,
    Task,
    Decision,
    DecisionOption,
    Scenario,
    ScenarioVariable,
    Evidence,
    AnalysisResult,
    ActivityLog,
)
from app.repositories import (
    UserRepository,
    CollectionRepository,
    DocumentRepository,
    GoalRepository,
    TaskRepository,
    DecisionRepository,
    EvidenceRepository,
    ActivityLogRepository,
)

@pytest.fixture
def temp_db_path():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_lifeops.db")
    yield db_file
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

def test_full_crud_and_models(temp_db_path):
    # 1. Setup engine and tables
    db_url = f"sqlite:///{Path(temp_db_path).as_posix()}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    # 2. Test User CRUD
    user_repo = UserRepository(session)
    user = user_repo.create(
        email="alex@lifeops.ai",
        full_name="Alex Mercer",
        preferences={"theme": "dark"},
        context={"skills": ["Python", "Machine Learning"], "hours_per_day": 3},
    )
    assert user.id is not None
    assert user.email == "alex@lifeops.ai"

    # Read user
    fetched_user = user_repo.get_by_email("alex@lifeops.ai")
    assert fetched_user is not None
    assert fetched_user.full_name == "Alex Mercer"

    # Update user context
    updated_user = user_repo.update(
        user.id,
        context={"skills": ["Python", "Machine Learning", "FastAPI"], "hours_per_day": 4},
    )
    assert "FastAPI" in updated_user.context["skills"]

    # 3. Test Collection CRUD
    col_repo = CollectionRepository(session)
    col = col_repo.create(
        user_id=user.id,
        name="Career Planning",
        description="Documents related to AI career and internships",
    )
    assert col.id is not None
    assert col.name == "Career Planning"
    assert len(col_repo.list_by_user(user.id)) == 1

    # 4. Test Document, Version, and Chunk CRUD
    doc_repo = DocumentRepository(session)
    doc = doc_repo.create(
        collection_id=col.id,
        filename="ai_internship_requirements.pdf",
        file_type="pdf",
        file_size=102400,
        storage_path="/data/uploads/ai_internship_requirements.pdf",
        content_hash="hash_abc123",
        current_version=1,
        status="PROCESSED",
    )
    assert doc.id is not None
    assert doc.status == "PROCESSED"

    # Add Document Version
    version = doc_repo.add_version(
        document_id=doc.id,
        version_number=1,
        file_size=102400,
        content_hash="hash_abc123",
        storage_path="/data/uploads/ai_internship_requirements.pdf",
    )
    assert version.id is not None
    assert version.is_active is True

    # Add Document Chunk
    chunks = doc_repo.add_chunks([
        {
            "document_id": doc.id,
            "version_id": version.id,
            "collection_id": col.id,
            "chunk_index": 0,
            "page_number": 1,
            "content": "Requires strong proficiency in Python and modern ML frameworks.",
            "token_count": 12,
            "vector_id": f"{col.id}_{doc.id}_v1_0",
            "metadata_json": {"source": "ai_internship_requirements.pdf", "page": 1},
        }
    ])
    assert len(chunks) == 1
    assert chunks[0].vector_id == f"{col.id}_{doc.id}_v1_0"

    # 5. Test Goal and Task CRUD
    goal_repo = GoalRepository(session)
    goal = goal_repo.create(
        user_id=user.id,
        title="Secure AI Internship",
        description="Land an AI engineering internship for Summer 2026",
        importance="HIGH",
        status="ACTIVE",
        progress=25.0,
    )
    assert goal.id is not None
    assert goal.progress == 25.0

    task_repo = TaskRepository(session)
    task1 = task_repo.create(
        user_id=user.id,
        goal_id=goal.id,
        title="Build RAG project portfolio",
        priority="HIGH",
        estimated_duration_minutes=180,
        status="IN_PROGRESS",
    )
    assert task1.id is not None
    assert task1.goal_id == goal.id

    # Update Task status
    updated_task = task_repo.update(task1.id, status="COMPLETED")
    assert updated_task.status == "COMPLETED"

    # 6. Test Decision, Options, Scenarios, and Variables CRUD
    dec_repo = DecisionRepository(session)
    decision = dec_repo.create(
        user_id=user.id,
        title="Choose AI Role Specialization",
        question="Which AI career path should I focus on given 3 months available?",
        context_description="Intermediate Python skills, wanting production engineering focus",
        status="DRAFT",
    )
    assert decision.id is not None

    opt_a = dec_repo.add_option(
        decision_id=decision.id,
        title="AI Engineer",
        description="Focus on RAG, agentic frameworks, and LLM applications",
        match_score=85.0,
        effort_estimate="3 months",
    )
    opt_b = dec_repo.add_option(
        decision_id=decision.id,
        title="Data Scientist",
        description="Focus on statistics, EDA, and tabular modeling",
        match_score=68.0,
        effort_estimate="4 months",
    )
    options = dec_repo.list_options(decision.id)
    assert len(options) == 2

    # Scenarios & Variables
    baseline_scenario = dec_repo.create_scenario(
        decision_id=decision.id,
        name="Baseline: 2h daily",
        is_baseline=True,
    )
    whatif_scenario = dec_repo.create_scenario(
        decision_id=decision.id,
        name="What-If: 4h daily",
        is_baseline=False,
    )
    var_baseline = dec_repo.add_scenario_variable(
        scenario_id=baseline_scenario.id,
        name="study_time_hours_per_day",
        value="2",
        variable_type="number",
    )
    var_whatif = dec_repo.add_scenario_variable(
        scenario_id=whatif_scenario.id,
        name="study_time_hours_per_day",
        value="4",
        variable_type="number",
    )
    assert var_baseline.value == "2"
    assert var_whatif.value == "4"

    # Analysis Result
    analysis = dec_repo.add_analysis_result(
        decision_id=decision.id,
        scenario_id=baseline_scenario.id,
        recommendation="AI Engineer is the strongest match.",
        confidence="HIGH",
        reasoning_summary="Candidate demonstrates core Python skills matching the retrieved requirements.",
        details_json={"skill_gaps": ["Deployment", "Docker"], "evidence_count": 3},
    )
    assert analysis.id is not None
    assert analysis.confidence == "HIGH"

    # 7. Test Evidence and ActivityLog CRUD
    evidence_repo = EvidenceRepository(session)
    evidence = evidence_repo.create(
        document_id=doc.id,
        chunk_id=chunks[0].id,
        claim="Role requires proficiency in Python frameworks.",
        extracted_text="Requires strong proficiency in Python and modern ML frameworks.",
        source_filename="ai_internship_requirements.pdf",
        page_number=1,
        relevance_score=0.92,
    )
    assert evidence.id is not None
    assert evidence.relevance_score == 0.92

    log_repo = ActivityLogRepository(session)
    log = log_repo.log_activity(
        entity_type="DECISION",
        action="CREATED",
        entity_id=decision.id,
        user_id=user.id,
        details="Created decision: Choose AI Role Specialization",
    )
    assert log.id is not None
    assert len(log_repo.list_recent(user_id=user.id)) == 1

    # 8. Test Delete Operations
    # Delete task
    task_deleted = task_repo.delete(task1.id)
    assert task_deleted is True
    assert task_repo.get(task1.id) is None

    session.close()
    engine.dispose()

def test_persistence_after_restart(temp_db_path):
    """Verifies that committed database state persists across complete engine restarts."""
    db_url = f"sqlite:///{Path(temp_db_path).as_posix()}"

    # Initial session: create and commit entities
    engine1 = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine1)
    Session1 = sessionmaker(bind=engine1)
    session1 = Session1()

    user_repo1 = UserRepository(session1)
    user = user_repo1.create(email="persist_test@lifeops.ai", full_name="Persist User")
    user_id = user.id

    goal_repo1 = GoalRepository(session1)
    goal = goal_repo1.create(user_id=user_id, title="Persist Goal", importance="CRITICAL", progress=50.0)
    goal_id = goal.id

    session1.close()
    engine1.dispose()  # COMPLETE DISPOSE / ENGINE RESTART

    # New session: simulate system restart
    engine2 = create_engine(db_url, connect_args={"check_same_thread": False})
    Session2 = sessionmaker(bind=engine2)
    session2 = Session2()

    user_repo2 = UserRepository(session2)
    reloaded_user = user_repo2.get(user_id)
    assert reloaded_user is not None
    assert reloaded_user.email == "persist_test@lifeops.ai"

    goal_repo2 = GoalRepository(session2)
    reloaded_goal = goal_repo2.get(goal_id)
    assert reloaded_goal is not None
    assert reloaded_goal.title == "Persist Goal"
    assert reloaded_goal.progress == 50.0

    session2.close()
    engine2.dispose()
