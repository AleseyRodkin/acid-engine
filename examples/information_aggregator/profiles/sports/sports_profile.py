"""Sports Profile для Information Aggregator."""
from __future__ import annotations

from examples.information_aggregator.contracts.base_contracts import (
    SourceContract, ArticleContract, NormalizationContract,
    StorageContract, ObservationContract, AnalysisContract,
)
from acid_engine.level2.identity import ContractId


def create_sports_profile() -> dict:
    """Создаёт профиль для сбора спортивных новостей."""
    return {
        "sources": [
            SourceContract(
                contract_id=ContractId("sports", "espn_rss"),
                source_type="rss",
                endpoint="https://www.espn.com/espn/rss/news",
            ),
        ],
        "articles": [
            ArticleContract(
                contract_id=ContractId("sports", "news_article"),
                fields=("title", "body", "source", "url", "published_at", "sport", "team"),
            ),
        ],
        "normalizers": [
            NormalizationContract(
                contract_id=ContractId("sports", "html_cleaner"),
                input_format="html",
                output_format="plain_text",
            ),
        ],
        "storages": [
            StorageContract(
                contract_id=ContractId("sports", "atomic_store"),
                storage_type="atomic",
            ),
        ],
        "observers": [
            ObservationContract(
                contract_id=ContractId("sports", "metrics"),
                metrics=("latency", "success_rate", "article_count"),
            ),
        ],
        "analyzers": [
            AnalysisContract(
                contract_id=ContractId("sports", "entity_extractor"),
                analysis_type="entity_extraction",
            ),
        ],
    }