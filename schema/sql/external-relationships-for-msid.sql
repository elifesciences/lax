
--\timing

--EXPLAIN ANALYSE

-- find the *external* relationships for the *most recent version* of an article and return it's citation

SELECT 
    aver0.citation

FROM
    publisher_articleversion av0,
    publisher_articleversionextrelation aver0
    
WHERE
    av0.id = aver0.articleversion_id

AND
    av0.id IN
    (
        -- find all external relationships for the most recent version of the given manuscript-id

        SELECT
            articleversion_id
        FROM
            publisher_articleversionextrelation aver1

        WHERE
            aver1.articleversion_id = 
                (
                    -- find the most recent version of the given manuscript-id
                    
                    SELECT
                        av.id

                    FROM
                        publisher_articleversion av,
                        publisher_article a

                    WHERE
                        av.version = (
                                                
                            SELECT
                                max(av2.version) 
                            FROM
                                publisher_articleversion av2

                            WHERE
                                av2.article_id = av.article_id

                            -- exclude *unpublished* article versions
                            %s -- AND datetime_published IS NOT NULL

                            GROUP BY
                                av2.article_id
                        )

                        AND
                            a.manuscript_id = %s

                        AND
                            av.article_id = a.id
                )
    )
