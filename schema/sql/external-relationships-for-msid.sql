
--\timing

--EXPLAIN ANALYSE

-- find the *external* relationships for the *most recent version* of an article and return it's citation

SELECT 
    aver.citation

FROM
    publisher_articleversion av,
    publisher_articleversionextrelation aver
    
WHERE
    av.id = aver.articleversion_id

AND
    av.id IN
    (
        -- find all external relationships for the most recent version of the given manuscript-id

        SELECT
            articleversion_id
        FROM
            publisher_articleversionextrelation aver2

        WHERE
            aver2.articleversion_id = 
                (
                    -- find the most recent version of the given manuscript-id
                    
                    SELECT
                        av2.id

                    FROM
                        publisher_articleversion av2,
                        publisher_article a

                    WHERE
                        av2.version = (
                                                
                            SELECT
                                max(av3.version) 
                            FROM
                                publisher_articleversion av3

                            WHERE
                                av3.article_id = av2.article_id

                            -- exclude *unpublished* article versions
                            %s -- AND datetime_published IS NOT NULL

                            GROUP BY
                                av3.article_id
                        )

                        AND
                            a.manuscript_id = %s

                        AND
                            av2.article_id = a.id
                )
    )
