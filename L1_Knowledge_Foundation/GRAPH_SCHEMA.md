# GraphRAG Schema (L1)
**Version:** 1.0  
**Status:** DRAFT – pending review  
**Last Updated:** 2026-04-29  
**Owner:** Data / Knowledge Team  

> This schema defines the entity graph, relationship graph, and document corpus for the professional services knowledge base.  
> **Why GraphRAG?** Corporate services require traversing ownership chains, jurisdiction rules, and conflict‑of‑interest paths – flat vector search cannot answer these correctly.

---

## 1. Entity Types (10)

| # | Entity Type | Properties (required) | Properties (optional) | Source System | Uniqueness Key | Update Trigger |
|---|-------------|----------------------|----------------------|---------------|----------------|----------------|
| 1.0 | **Client** | `client_id`, `full_legal_name`, `incorporation_date`, `jurisdiction_of_incorp` | `trade_name`, `parent_entity_id`, `industry_code`, `risk_rating` | CRM / Salesforce | `client_id` | On onboarding or KYC refresh |
| 2.0 | **Individual** | `individual_id`, `full_name`, `nationality`, `date_of_birth`, `passport_number` | `tax_id`, `PEP_flag`, `sanction_flag`, `address_current` | KYC system | `individual_id` | On onboarding or AML review |
| 3.0 | **Jurisdiction** | `jurisdiction_code` (ISO 3166), `full_name`, `legal_system_type` | `tax_treaty_list`, `FATF_status`, `substance_requirements` | Regulatory feed / manual | `jurisdiction_code` | On regulatory change |
| 4.0 | **Legal_Entity** | `entity_id`, `entity_type` (LLC/Ltd/Foundation etc), `registered_name`, `registered_number` | `registered_address`, `filing_status`, `share_capital` | Registry APIs / CRM | `registered_number` + `jurisdiction_code` | On incorporation or change |
| 5.0 | **Service_Mandate** | `mandate_id`, `service_type`, `start_date`, `status` | `end_date`, `renewal_date`, `fee_schedule_id`, `assigned_officer` | CRM | `mandate_id` | On engagement or status change |
| 6.0 | **Service_Type** | `service_code`, `service_name`, `category` | `required_jurisdictions`, `typical_timeline`, `compliance_requirements` | Internal product catalog | `service_code` | On product change |
| 7.0 | **Regulator** | `regulator_id`, `name`, `jurisdiction_code`, `authority_type` | `contact_portal`, `reporting_deadlines`, `key_regulations` | Manual / regulatory feed | `regulator_id` | Annual review |
| 8.0 | **Document** | `doc_id`, `doc_type`, `issue_date`, `issuing_authority` | `expiry_date`, `related_entity_id`, `file_ref` | DMS / Drive | `doc_id` | On document upload or expiry |
| 9.0 | **Bank_Account** | `account_id`, `bank_name`, `jurisdiction_code`, `account_type`, `status` | `currency`, `iban`, `swift`, `opening_date` | Banking intro CRM | `account_id` | On account open/close |
| 10.0 | **Officer** | `officer_id`, `name`, `role_type` (director/secretary/nominee) | `effective_date`, `resignation_date`, `entity_id` | Registry / CRM | `officer_id` + `entity_id` | On appointment/change |

---

## 2. Relationship Types (10)

| # | Relationship | From → To | Cardinality | Properties | Business Meaning | Example Cypher Query |
|---|--------------|-----------|-------------|------------|------------------|----------------------|
| 1.0 | **OWNS** | Individual / Legal_Entity → Legal_Entity | Many‑to‑many (with ownership %) | `ownership_pct`, `share_class`, `effective_date` | Shareholding / UBO chain – traverse to find ultimate beneficial owner | `MATCH (i:Individual)-[:OWNS*1..5]->(e:Legal_Entity {id:'X'}) RETURN i` |
| 2.0 | **IS_DIRECTOR_OF** | Individual → Legal_Entity | Many‑to‑many | `role`, `appointment_date`, `resignation_date` | Directorship – used for conflict‑of‑interest checks | `MATCH (i:Individual {id:'Y'})-[:IS_DIRECTOR_OF]->(le) RETURN le` |
| 3.0 | **IS_UBO_OF** | Individual → Legal_Entity | Many‑to‑many (threshold ≥25%) | `beneficial_pct`, `declaration_date` | Ultimate beneficial ownership – direct or derived via OWNS chain | `MATCH (i)-[:IS_UBO_OF]->(e) WHERE e.risk_rating='HIGH'` |
| 4.0 | **INCORPORATED_IN** | Legal_Entity → Jurisdiction | Many‑to‑one | `incorporation_date`, `registration_number` | Links entity to its home jurisdiction and its regulator | `MATCH (le:Legal_Entity)-[:INCORPORATED_IN]->(j:Jurisdiction {code:'BVI'})` |
| 5.0 | **HAS_MANDATE** | Client → Service_Mandate | One‑to‑many | `signed_date`, `fee`, `currency` | Active service engagements | `MATCH (c:Client)-[:HAS_MANDATE]->(sm:Service_Mandate {status:'active'})` |
| 6.0 | **HOLDS_ACCOUNT_AT** | Legal_Entity → Bank_Account | One‑to‑many | `opening_date`, `primary_flag` | Bank relationship – for compliance reporting | `MATCH (le)-[:HOLDS_ACCOUNT_AT]->(ba) WHERE ba.status != 'active'` |
| 7.0 | **GOVERNED_BY** | Legal_Entity / Service_Type → Regulator | Many‑to‑many | `regulation_ref`, `effective_date` | Compliance jurisdiction mapping | `MATCH (le)-[:GOVERNED_BY]->(r:Regulator {name:'MAS'})` |
| 8.0 | **CONFLICTS_WITH** | Individual / Legal_Entity ↔ Individual / Legal_Entity | Many‑to‑many | `conflict_type`, `identified_date`, `resolution_status` | Conflict of interest – blocks new mandates | `MATCH (i1:Individual)-[:CONFLICTS_WITH]-(i2:Individual) RETURN i1,i2` |
| 9.0 | **RELATED_DOCUMENT** | Any entity → Document | Many‑to‑many | `doc_role` (e.g. cert_of_incorp, bank_letter) | Links entities to supporting documents | `MATCH (c:Client)-[:RELATED_DOCUMENT]->(d:Document) WHERE d.expiry_date < date() RETURN c` |
| 10.0 | **REFERS_TO** | Document → Jurisdiction / Regulator / Service_Type | Many‑to‑many | `reference_type`, `section` | Connects regulatory documents to governed entities | `MATCH (d:Document)-[:REFERS_TO]->(r:Regulator {name:'FATF'})` |

---

## 3. Canonical Query Patterns (with “Why Vanilla RAG Fails”)

| # | Business Question | Entities Traversed | Relationship Path | Output | **Why Vanilla RAG Fails** | Priority | Agent |
|---|------------------|--------------------|-------------------|--------|---------------------------|----------|-------|
| 1.0 | Who is the Ultimate Beneficial Owner of Client X? | Client → Legal_Entity → Individual | OWNS (multi‑hop, up to 5 levels) | Individual(s) with ≥25% ownership | Ownership chain is spread across multiple incorporation documents and registers; flat search cannot “walk” from one entity to the next. | CRITICAL | Compliance |
| 2.0 | Does Individual Y appear in any existing client structure before onboarding? | Individual → Legal_Entity → Client | IS_DIRECTOR_OF / IS_UBO_OF / OWNS | Existing client connections + conflict flag | The same individual may be named differently across documents; graph resolves via entity ID, while vector search does fuzzy matching and misses exact matches. | CRITICAL | Compliance |
| 3.0 | Which mandates are due for renewal in the next 90 days? | Client → Service_Mandate | HAS_MANDATE (filter on renewal_date) | Mandate list with client name, service type, officer | Renewal dates are stored in CRM fields and inside unstructured notes; flat search cannot reliably extract dates from mixed sources. | HIGH | Orchestrator + Operations |
| 4.0 | Which jurisdiction rules apply to a Singapore‑incorporated fund selling to EU investors? | Jurisdiction → Regulator → Document | INCORPORATED_IN + GOVERNED_BY + REFERS_TO | Regulation list per jurisdiction pair | Answering requires joining three different document sets (SG company law, EU fund regs, cross‑border rules) – no single chunk contains the full answer. | HIGH | Research |
| 5.0 | Find all entities where Document X (passport) is expiring within 30 days | Document → Individual → Legal_Entity / Officer | RELATED_DOCUMENT (filter expiry_date) | Entity list + contact details + responsible officer | Expiry info is buried in unstructured PDFs; vector search cannot apply a “≤30 days” numeric filter to text‑extracted dates. | HIGH | Compliance |
| 6.0 | What banking options exist for a UAE‑resident setting up a BVI company? | Jurisdiction → Bank_Account → Legal_Entity | INCORPORATED_IN + HOLDS_ACCOUNT_AT | Bank shortlist + historical success rate | Requires combining jurisdiction rules (BVI vs UAE) with historical mandate outcomes – scattered across regulatory documents and internal CRM notes. | MEDIUM | Research |
| 7.0 | Generate a group structure chart for Client X | Client → Legal_Entity (all layers) → Individual | OWNS + IS_DIRECTOR_OF + IS_UBO_OF (full subgraph) | Hierarchical ownership diagram data | The structure spans multiple certificates of incorporation, annual returns, and board minutes – no single document contains the full hierarchy. | HIGH | Drafting |

---

## 4. JSON Schema (for validation)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "GraphRAG Knowledge Graph Schema",
  "version": "1.0",
  "entityTypes": {
    "Client": {
      "required": ["client_id", "full_legal_name", "incorporation_date", "jurisdiction_of_incorp"],
      "properties": {
        "client_id": {"type": "string", "pattern": "^CLI-[A-Z0-9]{8}$"},
        "full_legal_name": {"type": "string", "maxLength": 200},
        "incorporation_date": {"type": "string", "format": "date"},
        "jurisdiction_of_incorp": {"type": "string", "enum": ["BVI", "CAYMAN", "SG", "HK", "UAE"]},
        "risk_rating": {"type": "string", "enum": ["LOW","MEDIUM","HIGH","CRITICAL"], "default": "LOW"}
      }
    },
    "Individual": {
      "required": ["individual_id", "full_name", "date_of_birth", "passport_number"],
      "properties": {
        "individual_id": {"type": "string", "pattern": "^IND-[A-Z0-9]{8}$"},
        "full_name": {"type": "string"},
        "PEP_flag": {"type": "boolean", "default": false},
        "sanction_flag": {"type": "boolean", "default": false}
      }
    }
    // Additional entity schemas follow the same pattern (omitted for brevity, but present in implementation)
  },
  "relationshipTypes": {
    "OWNS": {
      "from": ["Individual", "Legal_Entity"],
      "to": ["Legal_Entity"],
      "cardinality": "many_to_many",
      "requiredProperties": ["ownership_pct", "effective_date"],
      "properties": {
        "ownership_pct": {"type": "number", "minimum": 0, "maximum": 100},
        "effective_date": {"type": "string", "format": "date"}
      }
    },
    "IS_DIRECTOR_OF": {
      "from": ["Individual"],
      "to": ["Legal_Entity"],
      "cardinality": "many_to_many",
      "requiredProperties": ["role", "appointment_date"]
    }
    // All 10 relationships defined in full schema document
  }
}