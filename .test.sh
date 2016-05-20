#!/bin/bash
# called by test.sh
rm -f xml/junit.xml
coverage run --source='src/' --omit='*/tests/*,*/migrations/*' src/manage.py test src/
echo "* passed tests"
