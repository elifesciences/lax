#!/bin/bash
# complexity checker
#  -a <str>, --max-average <str>
#                        Threshold for the average complexity
#  -m <str>, --max-modules <str>
#                        Threshold for modules complexity
#  -b <str>, --max-absolute <str>
#                        Absolute threshold for block complexity

xenon src/ \
	--max-absolute B \
	--max-modules A \
	--max-average A \
	--exclude '*eif_ingestor.py,*check_article.py'
