-- Exclude physical record_id; INCLUDE all business identifiers and attributes.
-- All occurrences are flagged; choosing which row to retain is a separate decision.
SELECT 'exact_duplicate' AS category, 'members' AS table_name,
       record_id, 'all_business_fields_identical' AS check_name
FROM (
    SELECT record_id, COUNT(*) OVER (PARTITION BY "member_id", "birth_date") AS repetitions
    FROM members
) repeated WHERE repetitions > 1
UNION ALL
SELECT 'exact_duplicate' AS category, 'providers' AS table_name,
       record_id, 'all_business_fields_identical' AS check_name
FROM (
    SELECT record_id, COUNT(*) OVER (PARTITION BY "provider_id", "provider_type") AS repetitions
    FROM providers
) repeated WHERE repetitions > 1
UNION ALL
SELECT 'exact_duplicate' AS category, 'enrollment' AS table_name,
       record_id, 'all_business_fields_identical' AS check_name
FROM (
    SELECT record_id, COUNT(*) OVER (PARTITION BY "enrollment_id", "member_id", "start_date", "end_date") AS repetitions
    FROM enrollment
) repeated WHERE repetitions > 1
UNION ALL
SELECT 'exact_duplicate' AS category, 'claim_headers' AS table_name,
       record_id, 'all_business_fields_identical' AS check_name
FROM (
    SELECT record_id, COUNT(*) OVER (PARTITION BY "claim_id", "member_id", "provider_id", "service_start", "service_end", "received_date", "paid_date", "billed_cents", "allowed_cents", "paid_cents", "patient_cents") AS repetitions
    FROM claim_headers
) repeated WHERE repetitions > 1
UNION ALL
SELECT 'exact_duplicate' AS category, 'claim_lines' AS table_name,
       record_id, 'all_business_fields_identical' AS check_name
FROM (
    SELECT record_id, COUNT(*) OVER (PARTITION BY "claim_id", "line_number", "provider_id", "service_start", "service_end", "service_code", "modifier", "units", "billed_cents", "allowed_cents", "paid_cents", "patient_cents") AS repetitions
    FROM claim_lines
) repeated WHERE repetitions > 1;
