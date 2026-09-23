-- Run on the verified clean baseline. Raw dirty tables are not safe KPI inputs.
-- A one-to-many header/line join repeats the header amount once per line.
WITH incorrect AS (
    SELECT SUM(h.paid_cents) AS cents
    FROM claim_headers h JOIN claim_lines l ON h.claim_id=l.claim_id
), header_grain AS (
    SELECT SUM(paid_cents) AS cents FROM claim_headers
), line_grain AS (
    SELECT SUM(paid_cents) AS cents FROM claim_lines
), lines_per_claim AS (
    SELECT claim_id, SUM(paid_cents) AS paid_cents FROM claim_lines GROUP BY claim_id
), corrected_join AS (
    SELECT SUM(l.paid_cents) AS cents
    FROM claim_headers h JOIN lines_per_claim l ON h.claim_id=l.claim_id
)
SELECT incorrect.cents AS incorrect_join_paid_cents,
       header_grain.cents AS correct_header_paid_cents,
       line_grain.cents AS correct_line_paid_cents,
       corrected_join.cents AS correct_preaggregated_join_paid_cents,
       incorrect.cents-header_grain.cents AS overstatement_cents,
       incorrect.cents<>line_grain.cents AS reconciliation_catches_error
FROM incorrect, header_grain, line_grain, corrected_join;
