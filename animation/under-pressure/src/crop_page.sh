#!/usr/bin/env bash
# Rebuild the panel crops, title strip and caption from the page (1024x1536),
# then the title/caption cards used by cut_v1. Run from this folder.
set -euo pipefail
P=19-under-pressure.png
c(){ ffmpeg -y -loglevel error -i "$P" -vf "crop=$3:$4:$1:$2" "$5"; }
c 14  90  492 418 p1_caffeine.png
c 522 90  488 418 p2_plumber.png
c 14  524 492 456 p3_bubble_house.png
c 522 524 488 456 p4_four_hours.png
c 14  992 492 534 p5_one_push.png
c 522 992 488 534 p6_smell.png
c 0   0   1024 84 title_strip.png
c 524 526 200 40  caption_four_hours.png
mkdir -p ../cards
ffmpeg -y -loglevel error -f lavfi -i "color=c=0xEDE3C8:s=1920x1080" -i title_strip.png \
  -filter_complex "[1]scale=1700:-1[t];[0][t]overlay=(W-w)/2:(H-h)/2" -frames:v 1 ../cards/title.png
ffmpeg -y -loglevel error -f lavfi -i "color=c=0xEDE3C8:s=1920x1080" -i caption_four_hours.png \
  -filter_complex "[1]scale=900:-1:flags=lanczos[t];[0][t]overlay=(W-w)/2:(H-h)/2" -frames:v 1 ../cards/four_hours.png
