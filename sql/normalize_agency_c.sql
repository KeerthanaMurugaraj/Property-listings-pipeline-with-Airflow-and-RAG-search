-- Agency C: French labels, and the area is sometimes in square feet.
SELECT
    run_date,
    'agency_c'                                  AS source,
    id                                          AS source_id,
    titre                                       AS title,
    description,
    CASE type
        WHEN 'Appartement' THEN 'apartment'
        WHEN 'Maison'      THEN 'house'
        WHEN 'Studio'      THEN 'studio'
    END                                         AS property_type,
    ville                                       AS commune,
    lower(replace(adresse, ',', ''))            AS address,
    TRY_CAST(loyer AS INTEGER)                  AS price_eur,
    CASE unite
        WHEN 'm2'   THEN TRY_CAST(surface AS INTEGER)
        WHEN 'sqft' THEN round(TRY_CAST(surface AS DOUBLE) / 10.764)::INTEGER
    END                                         AS area_m2,
    TRY_CAST(chambres AS INTEGER)               AS bedrooms,
    list_sort(list_transform(equipements, lambda e:
        CASE e
            WHEN 'balcon'    THEN 'balcony'
            WHEN 'jardin'    THEN 'garden'
            WHEN 'ascenseur' THEN 'lift'
            WHEN 'meublé'    THEN 'furnished'
            WHEN 'cave'      THEN 'cellar'
            ELSE e
        END
    ))                                          AS features
FROM raw.agency_c
WHERE run_date = $run_date::DATE
