#!/bin/bash
set -xuv
for fname in elife-16695- elife-01968- valid/dummyelife-20125- valid/dummyelife-20105-
do
   cp "/home/luke/dev/python/bot-lax-adaptor/article-json/$fname"* ./
done

