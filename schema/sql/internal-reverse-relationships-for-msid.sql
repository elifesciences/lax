--\timing
--EXPLAIN ANALYSE

-- find the latest article version details, of all the articles pointing to (related_to) the given manuscript-id.

-- lax=# select * from publisher_articleversionrelation where related_to_id = 1
--   id   | articleversion_id | related_to_id 
-- -------+-------------------+---------------
--  41097 |              6072 |             1
--  41101 |              6102 |             1
--  41105 |              6129 |             1
--  41555 |               302 |             1

SELECT
    av.article_json_v1_snippet
FROM
    publisher_articleversion av,
    publisher_article a
WHERE
    av.article_id = a.id
AND
    -- max article versions only
    av.version = (           
        SELECT
            max(av2.version) 
        FROM
            publisher_articleversion av2
        WHERE
            av2.article_id = av.article_id
        -- exclude unpublished article versions
        %s
        GROUP BY
            av2.article_id
    )
AND
    av.id IN (
        -- find all article versions pointing to (related_to) the given article's manuscript id
        SELECT DISTINCT
            avr.articleversion_id
        FROM
            publisher_article a2,
            publisher_articleversionrelation avr
        WHERE
            a2.id = avr.related_to_id
        AND
            a2.manuscript_id = %s
    )
ORDER BY
    av.id ASC
