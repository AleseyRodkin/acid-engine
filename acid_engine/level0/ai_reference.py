"""Ссылочное представление для ИИ (уровень 0)."""
from __future__ import annotations
from typing import Any, Optional, Dict, List
from acid_engine.level2.identity import ContractId

class AIReferenceView:
    """
    Хранит ссылку на атом (ContractId) и умеет собирать контекст.
    В будущем будет обращаться к ContractRegistry.
    """
    def __init__(self, contract_id: ContractId, registry: Optional[Any] = None):
        self.contract_id = contract_id
        self.registry = registry

    def describe(self) -> Dict[str, Any]:
        """Возвращает структурированное описание атома."""
        desc = {
            "contract_id": str(self.contract_id),
            "inputs": {},
            "outputs": {},
            "constraints": {},
            "history": [],
        }
        # Если есть registry, можно дополнить реальными данными
        if self.registry:
            try:
                module = self.registry.resolve(self.contract_id)
                desc["inputs"] = {"type": module.input_type}
                desc["outputs"] = {"type": module.output_type}
                desc["constraints"] = module.specification.policy.to_canonical_dict()
            except Exception:
                pass
        return desc