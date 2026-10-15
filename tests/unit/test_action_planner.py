import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

backend_dir = (Path(__file__).resolve().parents[2] / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from app.models.task_goal import Task, Goal
from app.services.action_planner import ActionPlanner

def test_deterministic_scoring_urgency_and_goal_importance():
    planner = ActionPlanner()
    now = datetime.now(timezone.utc)

    critical_goal = Goal(title="Launch Product", importance="CRITICAL", progress=10.0)
    low_goal = Goal(title="Minor Cleanup", importance="LOW", progress=50.0)

    # Task 1: Overdue, under CRITICAL goal, URGENT priority
    task_urgent = Task(
        title="Fix Security Breach",
        priority="URGENT",
        deadline=now - timedelta(hours=2),
        estimated_duration_minutes=60,
    )

    # Task 2: Due next week, under LOW goal, LOW priority
    task_low = Task(
        title="Sort desktop icons",
        priority="LOW",
        deadline=now + timedelta(days=5),
        estimated_duration_minutes=30,
    )

    score_urgent = planner._calculate_task_score(
        task=task_urgent,
        parent_goal=critical_goal,
        now=now,
        focus_areas=[],
        has_evidence=True,
    )

    score_low = planner._calculate_task_score(
        task=task_low,
        parent_goal=low_goal,
        now=now,
        focus_areas=[],
        has_evidence=False,
    )

    # Assert deterministic ranking: urgent task score >> low task score
    # Score for urgent: 100 (overdue) + 45 (CRITICAL) + 40 (URGENT) + 15 (evidence) = 200
    # Score for low: 50 (due week) + 5 (LOW) + 5 (LOW) + 0 = 60
    assert score_urgent > score_low
    assert score_urgent == 200.0
    assert score_low == 60.0

def test_deterministic_scoring_reproducibility():
    """Ensure that running scoring multiple times produces identical values without randomness."""
    planner = ActionPlanner()
    now = datetime.now(timezone.utc)
    goal = Goal(title="Alpha Goal", importance="HIGH")
    task = Task(title="Code Architecture", priority="HIGH", deadline=now + timedelta(hours=12))

    scores = [
        planner._calculate_task_score(task, goal, now, ["Backend"], has_evidence=True)
        for _ in range(10)
    ]
    # All scores must be strictly identical (zero randomness)
    assert len(set(scores)) == 1
    # 90 (due today) + 30 (HIGH goal) + 25 (HIGH task) + 15 (evidence) = 160
    assert scores[0] == 160.0

def test_constraints_and_focus_area_weighting():
    planner = ActionPlanner()
    now = datetime.now(timezone.utc)
    goal = Goal(title="Strategic Target", importance="MEDIUM")

    task_in_focus = Task(title="Build Pipeline", priority="MEDIUM", category="Engineering")
    task_out_focus = Task(title="Admin paperwork", priority="MEDIUM", category="Admin")

    score_in = planner._calculate_task_score(
        task_in_focus, goal, now, focus_areas=["Engineering"], has_evidence=False
    )
    score_out = planner._calculate_task_score(
        task_out_focus, goal, now, focus_areas=["Engineering"], has_evidence=False
    )

    # Focus area adds 10 points
    assert score_in == score_out + 10.0
