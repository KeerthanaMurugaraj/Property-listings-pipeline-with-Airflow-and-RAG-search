-- One text per active listing: this is what gets embedded and searched.
-- The text is built from the cleaned columns, not from the agencies' own wording,
-- so a property gives the same text whichever agency lists it.
WITH documents AS (
    SELECT
        listing_id,
        commune,
        property_type,
        price_eur,
        bedrooms,
        concat(
            CASE WHEN property_type = 'studio' THEN 'Studio'
                 ELSE bedrooms || '-bedroom ' || property_type END,
            ' for rent in ', commune, ', ', address, '. ',
            area_m2, ' m2, ', price_eur, ' EUR per month. ',
            CASE WHEN len(features) > 0 THEN 'Features: ' || array_to_string(features, ', ') || '.'
                 ELSE 'No listed features.' END
        ) AS text
    FROM core.listings
    WHERE status = 'active'
)
-- The fingerprint changes exactly when the text changes. Comparing fingerprints
-- tells us which listings need a new embedding.
SELECT *, md5(text) AS fingerprint
FROM documents
