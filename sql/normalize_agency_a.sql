-- Agency A: everything arrives as text. Prices look like '2.900 €', areas like '93 m2'.
-- TRY_CAST gives NULL instead of an error when the text is not a number (for example 'sur demande').
SELECT
    run_date,
    'agency_a'                                                        AS source,
    ref                                                               AS source_id,
    title,
    description,
    lower(type)                                                       AS property_type,
    city                                                              AS commune,
    lower(replace(address, ',', ''))                                  AS address,
    TRY_CAST(replace(replace(price, '.', ''), ' €', '') AS INTEGER)   AS price_eur,
    TRY_CAST(replace(surface, ' m2', '') AS INTEGER)                  AS area_m2,
    -- Agency A leaves bedrooms empty for studios.
    coalesce(TRY_CAST(bedrooms AS INTEGER), CASE WHEN lower(type) = 'studio' THEN 0 END) AS bedrooms,
    list_sort(string_split(features, '; '))                           AS features
FROM raw.agency_a
WHERE run_date = $run_date::DATE
