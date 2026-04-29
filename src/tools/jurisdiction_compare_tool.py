from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, List

class JurisdictionCompareInput(BaseModel):
    """Input schema for JurisdictionCompareTool."""
    jurisdictions: List[str] = Field(..., description="List of ISO 3166 jurisdiction codes (e.g., ['VG', 'KY']).")

class JurisdictionCompareTool(BaseTool):
    name: str = "jurisdiction_compare"
    description: str = (
        "Compares two or more jurisdictions across cost, tax, timeline, substance, and compliance dimensions. "
        "Queries the Neo4j GraphRAG database to retrieve this information."
    )
    args_schema: Type[BaseModel] = JurisdictionCompareInput

    def _run(self, jurisdictions: List[str]) -> str:
        # MVP Mock implementation - in Phase 0/1 this connects to Neo4j via Cypher
        # neo4j_driver.execute_query("MATCH (j:Jurisdiction)...")
        
        if len(jurisdictions) < 2:
            return '{"error": "ERR_INSUFFICIENT_JURISDICTIONS", "message": "Need at least 2 jurisdictions to compare."}'
            
        mock_data = {
            "VG": {"cost": "$2,500", "tax": "0% Corporate", "timeline": "3-5 days"},
            "KY": {"cost": "$4,500", "tax": "0% Corporate", "timeline": "5-7 days"},
            "SG": {"cost": "$3,000", "tax": "17% Corporate", "timeline": "1-2 days"}
        }
        
        results = {}
        for j in jurisdictions:
            if j in mock_data:
                results[j] = mock_data[j]
            else:
                results[j] = {"error": "Jurisdiction not found in knowledge graph"}
                
        return str({
            "comparison_data": results,
            "confidence_level": "HIGH",
            "data_freshness": "2026-04-29"
        })
