-- Preserve historical live-comparator receipts while binding successor receipts
-- to the exact accepted parity basis that authorized comparator retirement.

ALTER TABLE librsi_cutover_receipts_v2
    ADD COLUMN parity_basis_root TEXT NOT NULL
    DEFAULT '2e61a80eeb847a33297dbf73921f08349f8ab90dc58a9f72623eb053fdace644';

CREATE INDEX IF NOT EXISTS idx_librsi_cutover_parity_basis
    ON librsi_cutover_receipts_v2(parity_basis_root,authority_posture,created_at);
