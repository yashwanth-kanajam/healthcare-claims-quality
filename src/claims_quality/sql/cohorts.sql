-- Age is frozen at 2024-01-01. This is a descriptive synthetic grouping, not risk adjustment.
WITH member_cohort AS (
 SELECT member_id, CASE WHEN date_diff('year',birth_date,DATE '2024-01-01') < 55
   THEN 'Under 55' ELSE '55 and over' END AS cohort FROM members
), member_months AS (
 SELECT DISTINCT m.member_id, m.cohort, i
 FROM member_cohort m CROSS JOIN range(12) t(i)
 WHERE EXISTS (SELECT 1 FROM enrollment e WHERE e.member_id=m.member_id
   AND e.start_date <= last_day(CAST(DATE '2024-01-01'+i*INTERVAL '1 month' AS DATE))
   AND e.end_date >= CAST(DATE '2024-01-01'+i*INTERVAL '1 month' AS DATE))
), denominators AS (
 SELECT cohort, COUNT(DISTINCT member_id) AS members, COUNT(*) AS member_months
 FROM member_months GROUP BY cohort
), numerators AS (
 SELECT m.cohort, COUNT(*) AS claims, SUM(h.paid_cents) AS paid_cents
 FROM claim_headers h JOIN member_cohort m ON m.member_id=h.member_id
 WHERE h.service_start >= DATE '2024-01-01' AND h.service_start < DATE '2025-01-01'
 AND EXISTS (SELECT 1 FROM enrollment e WHERE e.member_id=h.member_id
   AND e.start_date<=h.service_start AND e.end_date>=h.service_end)
 GROUP BY m.cohort
)
SELECT d.cohort,d.members,d.member_months,COALESCE(n.claims,0) AS claims,
 COALESCE(n.paid_cents,0) AS paid_cents,
 COALESCE(n.paid_cents,0)/100.0/NULLIF(d.member_months,0) AS paid_per_member_month,
 COALESCE(n.claims,0)*1000.0/NULLIF(d.member_months,0) AS claims_per_1000_member_months
FROM denominators d LEFT JOIN numerators n ON n.cohort=d.cohort ORDER BY d.cohort;
