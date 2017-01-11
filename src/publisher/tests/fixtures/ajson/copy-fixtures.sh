#!/bin/bash
set -xuv
for fname in elife-16695- patched/elife-01968- patched/elife-20125- patched/elife-20105-v1 patched/elife-12215-v1
do
   cp "/home/luke/dev/python/bot-lax-adaptor/article-json/$fname"* ./
done

