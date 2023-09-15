--\timing
--EXPLAIN ANALYSE

-- find the *external* relationships for the given article version ID and return just the citation.

SELECT 
    avext.citation

FROM
    publisher_articleversion av,
    publisher_articleversionextrelation avext

WHERE
    av.id = avext.articleversion_id

AND
    av.id = %s
