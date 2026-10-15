from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from app.models.decision import Decision, DecisionOption, Scenario, ScenarioVariable
from app.models.evidence_analysis import AnalysisResult
from app.models.task_goal import Goal
from app.repositories.base import BaseRepository

class DecisionRepository(BaseRepository[Decision]):
    def __init__(self, db: Session):
        super().__init__(Decision, db)

    def list_by_user(self, user_id: str, status_filter: Optional[str] = None) -> List[Decision]:
        query = (
            self.db.query(Decision)
            .options(
                joinedload(Decision.options),
                joinedload(Decision.goals),
                joinedload(Decision.analysis_results),
            )
            .filter(Decision.user_id == user_id)
        )
        if status_filter:
            query = query.filter(Decision.status == status_filter)
        return query.order_by(Decision.created_at.desc()).all()

    def get_with_relations(self, decision_id: str, user_id: Optional[str] = None) -> Optional[Decision]:
        query = (
            self.db.query(Decision)
            .options(
                joinedload(Decision.options),
                joinedload(Decision.goals),
                joinedload(Decision.analysis_results),
            )
            .filter(Decision.id == decision_id)
        )
        if user_id:
            query = query.filter(Decision.user_id == user_id)
        return query.first()

    def set_goals(self, decision: Decision, goal_ids: List[str]) -> Decision:
        if not goal_ids:
            decision.goals = []
        else:
            goals = self.db.query(Goal).filter(Goal.id.in_(goal_ids)).all()
            decision.goals = goals
        self.db.commit()
        self.db.refresh(decision)
        return decision

    def add_option(
        self,
        decision_id: str,
        title: str,
        description: Optional[str] = None,
        match_score: Optional[float] = None,
        effort_estimate: Optional[str] = None,
    ) -> DecisionOption:
        option = DecisionOption(
            decision_id=decision_id,
            title=title,
            description=description,
            match_score=match_score,
            effort_estimate=effort_estimate,
        )
        self.db.add(option)
        self.db.commit()
        self.db.refresh(option)
        return option

    def list_options(self, decision_id: str) -> List[DecisionOption]:
        return (
            self.db.query(DecisionOption)
            .filter(DecisionOption.decision_id == decision_id)
            .order_by(DecisionOption.created_at.asc())
            .all()
        )

    def delete_option(self, option_id: str) -> bool:
        opt = self.db.query(DecisionOption).filter(DecisionOption.id == option_id).first()
        if opt:
            self.db.delete(opt)
            self.db.commit()
            return True
        return False

    def create_scenario(
        self,
        decision_id: str,
        name: str,
        is_baseline: bool = False,
        description: Optional[str] = None,
    ) -> Scenario:
        scenario = Scenario(
            decision_id=decision_id,
            name=name,
            is_baseline=is_baseline,
            description=description,
        )
        self.db.add(scenario)
        self.db.commit()
        self.db.refresh(scenario)
        return scenario

    def list_scenarios(self, decision_id: str) -> List[Scenario]:
        return self.db.query(Scenario).filter(Scenario.decision_id == decision_id).all()

    def add_scenario_variable(
        self,
        scenario_id: str,
        name: str,
        value: str,
        variable_type: str = "string",
    ) -> ScenarioVariable:
        var = ScenarioVariable(
            scenario_id=scenario_id,
            name=name,
            value=value,
            variable_type=variable_type,
        )
        self.db.add(var)
        self.db.commit()
        self.db.refresh(var)
        return var

    def add_analysis_result(
        self,
        decision_id: str,
        recommendation: str,
        confidence: str,
        reasoning_summary: str,
        details_json: dict,
        scenario_id: Optional[str] = None,
    ) -> AnalysisResult:
        result = AnalysisResult(
            decision_id=decision_id,
            scenario_id=scenario_id,
            recommendation=recommendation,
            confidence=confidence,
            reasoning_summary=reasoning_summary,
            details_json=details_json,
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def save_decision_analysis(
        self,
        decision: Decision,
        recommendation: str,
        confidence: str,
        reasoning_summary: str,
        details_json: dict,
        options_scores: Optional[Dict[str, float]] = None,
    ) -> AnalysisResult:
        # 1. Add AnalysisResult
        result = AnalysisResult(
            decision_id=decision.id,
            recommendation=recommendation,
            confidence=confidence,
            reasoning_summary=reasoning_summary,
            details_json=details_json,
        )
        self.db.add(result)

        # 2. Update match scores on decision options if provided
        if options_scores:
            for opt in decision.options:
                if opt.id in options_scores:
                    opt.match_score = options_scores[opt.id]

        # 3. Transition decision status to ANALYZED
        decision.status = "ANALYZED"
        self.db.commit()
        self.db.refresh(result)
        self.db.refresh(decision)
        return result
