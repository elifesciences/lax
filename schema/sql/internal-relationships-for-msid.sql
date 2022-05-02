
--\timing

--EXPLAIN ANALYSE

-- find the article version details of all the internal relationships for the most recent version of the given manuscript-id
-- with the test fixture this should return 3 articles, 20162, 877, 1

-- lax=# select * from publisher_articleversionrelation where articleversion_id = 2520;
--  id   | articleversion_id | related_to_id 
-- -------+-------------------+---------------
--  41577 |              2520 |           877
-- (1 row)

-- lax=# select a.id as article_id, a.manuscript_id, av.id as av_id, av.version as av_version from publisher_articleversion av, publisher_article a  where av.article_id = a.id and a.id = 877;
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
                    publisher_articleversion av2, publisher_article a2 
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
                        -- exclude unpublished article versions
                        %s
                        GROUP BY
                            av3.article_id
                    )
                AND
                    a2.manuscript_id = %s
            )
    )

