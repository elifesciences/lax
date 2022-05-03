
--\timing

--EXPLAIN ANALYSE

-- find the *external* relationships for the given article version ID and return just the citation
-- (used to be more complex :)

SELECT 
    aver.citation

FROM
    publisher_articleversion av,
    publisher_articleversionextrelation aver
    
WHERE
    av.id = aver.articleversion_id

AND
    av.id = %s
