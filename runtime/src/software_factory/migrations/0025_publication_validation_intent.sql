-- Bind each integration publication to one exact post-publication validation policy.

ALTER TABLE integration_candidates_v2
    ADD COLUMN post_validation_command_json TEXT;

-- Historical successful publications without a post validator retain the empty
-- policy. When the prior terminal evidence contains an exact post-validation
-- command, preserve that command as the idempotency identity.
UPDATE integration_candidates_v2
SET post_validation_command_json =
    CASE
        WHEN status != 'published' THEN post_validation_command_json
        WHEN validation_result_json IS NULL OR json_valid(validation_result_json) != 1 THEN '[]'
        WHEN json_extract(validation_result_json, '$.phase') = 'post_publish'
             AND json_type(validation_result_json, '$.command') = 'array'
            THEN json_extract(validation_result_json, '$.command')
        ELSE '[]'
    END;
