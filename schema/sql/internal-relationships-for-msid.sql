
--\timing

--EXPLAIN ANALYSE

-- find the article version details of all the internal relationships for the most recent version of the given manuscript-id
-- note: the most recent article version may have a different set of relationships than previous versions of the article.
-- with the test fixture this should return 3 articles, 20162, 877, 1

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
    -- join article
    av.article_id = a.id 
AND
    a.id = (
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
                    av2.version = (
                        -- max versions only
                        SELECT
                            max(av3.version) 
                        FROM
                            publisher_articleversion av3
                        WHERE
                            av3.article_id = av2.article_id
                        -- do not consider unpublished article versions
                        %s
                        GROUP BY
                            av3.article_id
                    )
                AND
                    --a2.manuscript_id = 9560
                    a2.manuscript_id = %s
            )
    )

-- of the article versions we're selecting, only use the max versions 
-- (just like how we only consider the relationships of the max version of the given manuscript id)
AND
    av.version = (
        -- max versions only
        SELECT
            max(av4.version) 
        FROM
            publisher_articleversion av4
        WHERE
            av4.article_id = av.article_id
        -- of the article versions we're selecting, do not consider unpublished article versions
        %s
        GROUP BY
            av4.article_id
    )

ORDER BY
    av.id ASC
