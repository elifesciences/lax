#!/bin/bash
# called by test.sh
coverage run --source='src/' --omit='*/tests/*,*/migrations/*' src/manage.py test src/
echo "* passed tests"
