-- Agency B: nested JSON. location, rent and rooms are structs, read with a dot.
SELECT
    run_date,
    'agency_b'                  AS source,
    id                          AS source_id,
    headline                    AS title,
    "text"                      AS description,
    lower(propertyType)         AS property_type,
    location.commune            AS commune,
    lower(location.street)      AS address,
    rent.amount::INTEGER        AS price_eur,
    livingArea::INTEGER         AS area_m2,
    rooms.bedrooms::INTEGER     AS bedrooms,
    list_sort(amenities)        AS features
FROM raw.agency_b
WHERE run_date = $run_date::DATE
