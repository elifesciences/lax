
\timing

--EXPLAIN ANALYSE

-- find the article version details of all the internal relationships for the most recent version of the given manuscript-id

select 
    av0.id,
    av0.article_id,
    av0.version,
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

                            group by 
                                av2.article_id
                        )

                        --and
                            -- 7546 has three interal relations and one version
                            -- 7454 has many article versions and no relations
                            -- 9560 is homo naledi, has one version and one relation
                            --a.manuscript_id in (7454, 7546, 9560)
                        
                        and
                            --a.manuscript_id = 7546
                            a.manuscript_id = %s

                        and
                            av.article_id = a.id
                )
    )
%s
