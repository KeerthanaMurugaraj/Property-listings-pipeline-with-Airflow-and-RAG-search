-- The table the website would read: one row per property, with its current state.
-- It is rebuilt from every day in staging.deduped, so it does not matter in which
-- order the days were processed or how often a day was re-run.
WITH latest AS (
    SELECT max(run_date) AS run_date FROM staging.deduped
)
SELECT
    listing_id,
    -- arg_max(x, run_date) takes x from the most recent day the property was listed.
    arg_max(title, run_date)            AS title,
    arg_max(description, run_date)      AS description,
    arg_max(property_type, run_date)    AS property_type,
    arg_max(commune, run_date)          AS commune,
    arg_max(address, run_date)          AS address,
    arg_max(price_eur, run_date)        AS price_eur,
    arg_min(price_eur, run_date)        AS first_price_eur,
    arg_max(area_m2, run_date)          AS area_m2,
    arg_max(bedrooms, run_date)         AS bedrooms,
    arg_max(features, run_date)         AS features,
    arg_max(sources, run_date)          AS sources,
    min(run_date)                       AS first_seen,
    max(run_date)                       AS last_seen,
    CASE WHEN max(run_date) = (SELECT run_date FROM latest) THEN 'active' ELSE 'removed' END AS status
FROM staging.deduped
GROUP BY listing_id
