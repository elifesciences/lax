#!/bin/bash
# complexity checker
#  -a <str>, --max-average <str>
#                        Threshold for the average complexity
#  -m <str>, --max-modules <str>
#                        Threshold for modules complexity
#  -b <str>, --max-absolute <str>
#                        Absolute threshold for block complexity

# ejp_ingestor and ajson_ingestor have different rules applied to them

set -e

echo "[-] .cc-check.sh"

xenon src/ \
	--max-absolute B \
	--max-modules A \
	--max-average A \
	--exclude '*eif_ingestor.py,*ajson_ingestor.py' || {

    echo "use 'radon cc path/to/file.py' for more detail" > /dev/stderr
    exit 1
}

# slightly more lenient rules for the ingestors
xenon src/ \
	--max-absolute C \
	--max-modules B \
	--max-average B

echo "[✓] .cc-check.sh"
