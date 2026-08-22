-- Bind immutable release review to the strict acceptance/governance system.

ALTER TABLE immutable_releases_v2
    ADD COLUMN acceptance_contract_id TEXT REFERENCES acceptance_contracts_v2(id);
ALTER TABLE immutable_releases_v2
    ADD COLUMN acceptance_decision_id TEXT REFERENCES acceptance_decisions_v2(id);
ALTER TABLE release_reviews_v2
    ADD COLUMN acceptance_decision_id TEXT REFERENCES acceptance_decisions_v2(id);

CREATE INDEX IF NOT EXISTS idx_immutable_releases_acceptance
    ON immutable_releases_v2(acceptance_contract_id,acceptance_decision_id,status);
