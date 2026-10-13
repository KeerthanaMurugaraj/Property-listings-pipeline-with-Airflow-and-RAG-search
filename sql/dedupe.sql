-- The same property can be listed by two agencies. After normalizing, both rows have
-- the same commune and address, so that pair is the key: one output row per property per day.
SELECT
    run_date,
    substr(md5(lower(commune) || '|' || address), 1, 12)   AS listing_id,
    -- arg_min(x, source) takes x from the alphabetically first agency, so the choice is always the same.
    arg_min(title, source)          AS title,
    arg_min(description, source)    AS description,
    arg_min(property_type, source)  AS property_type,
    commune,
    address,
    min(price_eur)                  AS price_eur,   -- if agencies disagree, show the lowest price
    arg_min(area_m2, source)        AS area_m2,
    arg_min(bedrooms, source)       AS bedrooms,
    arg_min(features, source)       AS features,
    list(source ORDER BY source)    AS sources,
    list(source_id ORDER BY source) AS source_ids
FROM staging.valid
WHERE run_date = $run_date::DATE
GROUP BY run_date, commune, address
