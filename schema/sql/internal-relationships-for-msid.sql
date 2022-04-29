
--\timing

--EXPLAIN ANALYSE

-- find the article version details of all the internal relationships for the most recent version of the given manuscript-id
-- with the test fixture this should return 3 articles, 20162, 877, 1

select 
    av0.article_json_v1_snippet

from 
    publisher_articleversion av0

where
    av0.id in 
    (
        -- find all internal relationships for the most recent version of the given manuscript-id
    
        select 
            related_to_id
        from 
            publisher_articleversionrelation avr

        where
            avr.articleversion_id = 
                (
                    -- find the most recent version of the given manuscript-id
                    select
                        av.id

                    from 
                        publisher_articleversion av,
                        publisher_article a

                    where
                        av.version = (
                            select 
                                max(av2.version) 
                            from 
                                publisher_articleversion av2
                            where 
                                av2.article_id = av.article_id

                            -- we want to exclude *unpublished* article versions typically
                            %s -- AND datetime_published IS NOT NULL

                            group by 
                                av2.article_id
                        )
                        
                        and
                            --a.manuscript_id = 7546
                            --a.manuscript_id = 9560
                            --a.manuscript_id = 1234567890
                            a.manuscript_id = %s

                        and
                            av.article_id = a.id
                )
    )

order by
    av0.id asc
