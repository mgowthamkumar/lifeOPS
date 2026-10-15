from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.decision import Scenario, ScenarioVariable
from app.repositories.base import BaseRepository

class ScenarioRepository(BaseRepository[Scenario]):
    def __init__(self, db: Session):
        super().__init__(Scenario, db)

    def list_by_user(
        self,
        user_id: str,
        decision_id: Optional[str] = None,
    ) -> List[Scenario]:
        query = self.db.query(Scenario).filter(
            (Scenario.user_id == user_id) | (Scenario.user_id.is_(None))
        )
        if decision_id:
            query = query.filter(Scenario.decision_id == decision_id)
        return query.order_by(Scenario.is_baseline.desc(), Scenario.created_at.desc()).all()

    def get_baseline(
        self,
        user_id: str,
        decision_id: Optional[str] = None,
    ) -> Optional[Scenario]:
        query = self.db.query(Scenario).filter(
            (Scenario.user_id == user_id) | (Scenario.user_id.is_(None)),
            Scenario.is_baseline.is_(True),
        )
        if decision_id:
            query = query.filter(Scenario.decision_id == decision_id)
        return query.first()

    def create_scenario(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        is_baseline: bool = False,
        parameters: Optional[Dict[str, Any]] = None,
        decision_id: Optional[str] = None,
    ) -> Scenario:
        scenario = Scenario(
            user_id=user_id,
            decision_id=decision_id,
            name=name,
            description=description,
            is_baseline=is_baseline,
            parameters=parameters or {},
            simulation_result={},
        )
        self.db.add(scenario)
        self.db.commit()
        self.db.refresh(scenario)
        return scenario

    def update_scenario(
        self,
        scenario_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        simulation_result: Optional[Dict[str, Any]] = None,
    ) -> Optional[Scenario]:
        scenario = self.get(scenario_id)
        if not scenario:
            return None
        if name is not None:
            scenario.name = name
        if description is not None:
            scenario.description = description
        if parameters is not None:
            scenario.parameters = parameters
        if simulation_result is not None:
            scenario.simulation_result = simulation_result
        self.db.commit()
        self.db.refresh(scenario)
        return scenario

    def save_simulation_result(
        self,
        scenario_id: str,
        simulation_result: Dict[str, Any],
    ) -> Optional[Scenario]:
        scenario = self.get(scenario_id)
        if not scenario:
            return None
        scenario.simulation_result = simulation_result
        self.db.commit()
        self.db.refresh(scenario)
        return scenario
