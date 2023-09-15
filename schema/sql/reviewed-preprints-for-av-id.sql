--\timing
--EXPLAIN ANALYSE

-- very similar to external relationships, except we have a join with a table of unique reviewed-preprints.
-- while external citations can be duplicates, rpps cannot

SELECT
    rpp.content

FROM
    publisher_reviewedpreprint rpp,
    publisher_articleversionreviewedpreprintrelation avrpp

WHERE
    rpp.id = avrpp.reviewedpreprint_id

AND
    avrpp.articleversion_id = %s
