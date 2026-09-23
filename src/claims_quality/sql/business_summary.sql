-- Clean baseline only: preserve claim grain and use a unique provider dimension.
SELECT p.provider_type, COUNT(*) AS claim_count,
       COUNT(DISTINCT h.member_id) AS distinct_members,
       SUM(h.paid_cents) AS paid_cents,
       SUM(h.patient_cents) AS patient_cents,
       ROUND(AVG(date_diff('day', h.received_date, h.paid_date)), 2) AS mean_receipt_to_payment_days
FROM claim_headers h JOIN providers p ON h.provider_id=p.provider_id
GROUP BY p.provider_type ORDER BY p.provider_type;
