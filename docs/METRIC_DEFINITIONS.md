# Spending, utilization and cohort definitions

All measures refer to self-generated synthetic calendar-2024 data, baseline seed 17. These are demonstration metrics, not clinical recommendations or estimates for a real population.

| Metric | Definition |
|---|---|
| Claim | One unique claim_id at header grain; not a count of visits, episodes or people |
| Line | One claim_id + line_number entry; not necessarily a distinct service encounter |
| Paid | Sum of integer header paid_cents; agrees with summed lines on the validated baseline |
| Enrolled member-month | One distinct member/calendar-month with at least one day of overlapping enrollment |
| Eligible claim | Service start in 2024 and the entire service window contained within one enrollment span |
| Monthly assignment | Eligible claim attributed wholly to its service-start month; no cross-month proration |
| Paid per member-month | Eligible paid cents / 100 / enrolled member-months |
| Claims per 1,000 member-months | Eligible claim count × 1,000 / enrolled member-months; not annualized |
| Cohort | Age below 55 versus 55+ on 2024-01-01; all synthetic birthdays are Jan 1 |

The monthly calendar includes all 12 months, even without claims. Covered months with no claims have zero utilization/payment rates. Months with no enrolled members have undefined rates (SQL NULL), never an invented zero. Overlapping enrollment spans cannot double-count member-months because membership is determined with EXISTS and DISTINCT. The numerator requires a single containing span; merging consecutive coverage intervals is not implemented.

Cohort totals use the same eligibility contract and reconcile with monthly totals. Cohort rates must be recalculated as sum(numerator)/sum(denominator), never summed or averaged without weights. The Tableau sheet shows each cohort separately rather than an unweighted combined rate.

The generator intentionally ends services before November and fixes receipt/payment lags. Apparent seasonality, age differences or provider differences are generator artifacts, not evidence of healthcare behavior. Claims are not visits; these outputs should never be renamed visit counts.

Analytics run only on an independently verified, SQL-clean baseline. Dirty scenario data is for validation evaluation and does not feed spending/utilization KPIs. SQL source: utilization.sql and cohorts.sql under src/claims_quality/sql/.
