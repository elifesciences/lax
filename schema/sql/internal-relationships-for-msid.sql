--\timing
--EXPLAIN ANALYSE

-- find the article version details of all the internal relationships for the most recent version of the given manuscript-id.
-- note: the most recent article version may have a different set of relationships than previous versions of the article.

-- lax=# select * from publisher_articleversionrelation where articleversion_id = 2520;
--  id   | articleversion_id | related_to_id 
-- -------+-------------------+---------------
--  41577 |              2520 |           877
-- (1 row)

-- lax=# select a.id as article_id, a.manuscript_id, av.id as av_id, av.version as av_version 
--       from publisher_articleversion av, publisher_article a
--       where av.article_id = a.id and a.id = 877;
--  article_id | manuscript_id | av_id | av_version 
-- ------------+---------------+-------+------------
--        877 |          9561 |  2092 |          1


SELECT
    av.article_json_v1_snippet
FROM
    publisher_articleversion av, 
    publisher_article a  
WHERE
    av.article_id = a.id 
AND
    -- find all article ids (not manuscript ids) that other articles are pointing at for the given articleversion id.
    a.id in (
        SELECT
            related_to_id 
        FROM
            publisher_articleversionrelation avr 
        WHERE
            articleversion_id = (
                SELECT
                    av2.id 
                FROM
                    publisher_articleversion av2, 
                    publisher_article a2 
                WHERE
                    av2.article_id = a2.id 
                AND
                    av2.id = %s
            )
    )

-- of the article versions we're selecting, only use the max versions.
AND
    av.version = (
        SELECT
            max(av4.version) 
        FROM
            publisher_articleversion av4
        WHERE
            av4.article_id = av.article_id
        -- of the article versions we're selecting, do not consider unpublished article versions.
        %s
        GROUP BY
            av4.article_id
    )

ORDER BY
    av.id ASC
