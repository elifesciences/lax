
--\timing

--EXPLAIN ANALYSE

-- find the latest article version details, of all the articles pointing to (related_to) the given manuscript-id
-- with the test fixture article (a.67147), we should get no articles.


select 
    --av.id,
    --av.version,
    --a0.id as article_id,
    --a0.manuscript_id as article_msid
    av.article_json_v1_snippet

from
    publisher_articleversion av,
    publisher_article a0

where
    av.article_id = a0.id
    
and

    -- max article versions only
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

    av.id in (

        -- find all article versions pointing to (related_to) the given article's manuscript id

        select distinct
            avr.articleversion_id

        from 
            publisher_article a,
            publisher_articleversionrelation avr

        where
            a.id = avr.related_to_id

        and
            --a.manuscript_id = 9560
            a.manuscript_id = %s
    )

order by
    av.id asc
