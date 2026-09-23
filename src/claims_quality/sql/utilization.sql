-- Clean baseline, calendar 2024; numerator anchored on service_start month.
-- A member-month is counted once if any covered day overlaps that month.
-- A claim is eligible only when its whole service window fits one enrollment span.
WITH months AS (
 SELECT CAST(DATE '2024-01-01' + i * INTERVAL '1 month' AS DATE) AS month
 FROM range(12) t(i)
), eligible_months AS (
 SELECT DISTINCT m.member_id, d.month
 FROM members m CROSS JOIN months d
 WHERE EXISTS (SELECT 1 FROM enrollment e WHERE e.member_id=m.member_id
   AND e.start_date <= last_day(d.month) AND e.end_date >= d.month)
), denominators AS (
 SELECT month, COUNT(*) AS member_months FROM eligible_months GROUP BY month
), line_counts AS (
 SELECT claim_id, COUNT(*) AS line_count, SUM(units) AS units
 FROM claim_lines GROUP BY claim_id
), numerators AS (
 SELECT CAST(date_trunc('month',h.service_start) AS DATE) AS month,
 COUNT(*) AS claims, SUM(h.paid_cents) AS paid_cents,
 SUM(l.line_count) AS lines, SUM(l.units) AS units
 FROM claim_headers h JOIN line_counts l ON l.claim_id=h.claim_id
 WHERE h.service_start >= DATE '2024-01-01' AND h.service_start < DATE '2025-01-01'
 AND EXISTS (SELECT 1 FROM enrollment e WHERE e.member_id=h.member_id
   AND e.start_date <= h.service_start AND e.end_date >= h.service_end)
 GROUP BY 1
)
SELECT CAST(m.month AS VARCHAR) AS month, COALESCE(d.member_months,0) AS member_months,
 COALESCE(n.claims,0) AS claims, COALESCE(n.lines,0) AS lines,
 COALESCE(n.units,0) AS units, COALESCE(n.paid_cents,0) AS paid_cents,
 COALESCE(n.paid_cents,0)/100.0/NULLIF(d.member_months,0) AS paid_per_member_month,
 COALESCE(n.claims,0)*1000.0/NULLIF(d.member_months,0) AS claims_per_1000_member_months
FROM months m LEFT JOIN denominators d ON d.month=m.month
LEFT JOIN numerators n ON n.month=m.month ORDER BY m.month;
