-- Every SELECT emits (category, table_name, record_id, check_name).
-- EXISTS avoids multiplying results when a parent itself has duplicate records.
SELECT 'broken_foreign_key' AS category, 'enrollment' AS table_name, record_id,
       'enrollment_member_exists' AS check_name
FROM enrollment e WHERE NOT EXISTS (SELECT 1 FROM members m WHERE m.member_id=e.member_id)
UNION ALL
SELECT 'broken_foreign_key', 'claim_headers', record_id, 'header_member_exists'
FROM claim_headers h WHERE NOT EXISTS (SELECT 1 FROM members m WHERE m.member_id=h.member_id)
UNION ALL
SELECT 'broken_foreign_key', 'claim_headers', record_id, 'header_provider_exists'
FROM claim_headers h WHERE NOT EXISTS (SELECT 1 FROM providers p WHERE p.provider_id=h.provider_id)
UNION ALL
SELECT 'broken_foreign_key', 'claim_lines', record_id, 'line_header_exists'
FROM claim_lines l WHERE NOT EXISTS (SELECT 1 FROM claim_headers h WHERE h.claim_id=l.claim_id)
UNION ALL
SELECT 'broken_foreign_key', 'claim_lines', record_id, 'line_provider_exists'
FROM claim_lines l WHERE NOT EXISTS (SELECT 1 FROM providers p WHERE p.provider_id=l.provider_id)
UNION ALL
SELECT 'invalid_date_sequence', 'enrollment', record_id, 'enrollment_dates_ordered'
FROM enrollment WHERE start_date > end_date
UNION ALL
SELECT 'invalid_date_sequence', 'claim_headers', record_id, 'header_dates_ordered'
FROM claim_headers WHERE service_start > service_end OR service_end > received_date OR received_date > paid_date
UNION ALL
SELECT 'invalid_date_sequence', 'claim_headers', h.record_id, 'service_not_before_birth'
FROM claim_headers h WHERE EXISTS (SELECT 1 FROM members m WHERE m.member_id=h.member_id AND m.birth_date > h.service_start)
UNION ALL
SELECT 'invalid_date_sequence', 'claim_lines', record_id, 'line_dates_ordered'
FROM claim_lines WHERE service_start > service_end
UNION ALL
SELECT 'invalid_date_sequence', 'claim_lines', l.record_id, 'line_within_header_dates'
FROM claim_lines l WHERE EXISTS (
    SELECT 1 FROM claim_headers h WHERE h.claim_id=l.claim_id
    AND (l.service_start < h.service_start OR l.service_end > h.service_end)
)
UNION ALL
SELECT 'financial_reconciliation', 'claim_lines', record_id, 'line_amount_contract'
FROM claim_lines WHERE billed_cents < 0 OR allowed_cents < 0 OR paid_cents < 0 OR patient_cents < 0
    OR billed_cents < allowed_cents OR allowed_cents <> paid_cents + patient_cents
UNION ALL
SELECT 'financial_reconciliation', 'claim_headers', record_id, 'header_amount_contract'
FROM claim_headers WHERE billed_cents < 0 OR allowed_cents < 0 OR paid_cents < 0 OR patient_cents < 0
    OR billed_cents < allowed_cents OR allowed_cents <> paid_cents + patient_cents
UNION ALL
SELECT 'financial_reconciliation', 'claim_headers', h.record_id, 'header_line_totals'
FROM claim_headers h
LEFT JOIN (
    SELECT claim_id, COUNT(*) AS line_count, SUM(billed_cents) AS billed,
           SUM(allowed_cents) AS allowed, SUM(paid_cents) AS paid, SUM(patient_cents) AS patient
    FROM claim_lines GROUP BY claim_id
) l ON h.claim_id=l.claim_id
WHERE l.line_count IS NULL OR h.billed_cents <> l.billed OR h.allowed_cents <> l.allowed
    OR h.paid_cents <> l.paid OR h.patient_cents <> l.patient;
