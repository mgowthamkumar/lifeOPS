from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.decision import Decision, DecisionOption, Scenario, ScenarioVariable
from app.models.evidence_analysis import AnalysisResult
from app.repositories.base import BaseRepository

class DecisionRepository(BaseRepository[Decision]):
    def __init__(self, db: Session):
        super().__init__(Decision, db)

    def list_by_user(self, user_id: str) -> List[Decision]:
        return self.db.query(Decision).filter(Decision.user_id == user_id).all()

    def add_option(self, decision_id: str, title: str, description: Optional[str] = None, match_score: Optional[float] = None, effort_estimate: Optional[str] = None) -> DecisionOption:
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
        return self.db.query(DecisionOption).filter(DecisionOption.decision_id == decision_id).all()

    def create_scenario(self, decision_id: str, name: str, is_baseline: bool = False, description: Optional[str] = None) -> Scenario:
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

    def add_scenario_variable(self, scenario_id: str, name: str, value: str, variable_type: str = "string") -> ScenarioVariable:
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

    def add_analysis_result(self, decision_id: str, recommendation: str, confidence: str, reasoning_summary: str, details_json: dict, scenario_id: Optional[str] = None) -> AnalysisResult:
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
