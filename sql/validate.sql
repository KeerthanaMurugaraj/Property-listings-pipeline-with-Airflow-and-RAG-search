-- One rule per line. The first rule that matches becomes the reject_reason.
-- A row with no reason is valid.
SELECT
    *,
    CASE
        WHEN price_eur IS NULL                      THEN 'price missing or not a number'
        WHEN price_eur NOT BETWEEN 300 AND 20000    THEN 'price out of range'
        WHEN area_m2 IS NULL                        THEN 'area missing or not a number'
        WHEN area_m2 NOT BETWEEN 10 AND 1000        THEN 'area out of range'
        WHEN bedrooms IS NULL                       THEN 'bedrooms missing'
        WHEN property_type IS NULL
          OR property_type NOT IN ('apartment', 'house', 'studio') THEN 'unknown property type'
        WHEN property_type = 'studio' AND area_m2 > 60 THEN 'studio larger than 60 m2'
        WHEN commune IS NULL OR address IS NULL     THEN 'location missing'
    END AS reject_reason
FROM staging.normalized
WHERE run_date = $run_date::DATE
