#!/usr/bin/env python3

## This script is for legacy users only
## Please use find_posts.py instead

import os
import sys

ACCESS_TOKEN = sys.argv[1]
SERVER = sys.argv[2]
REPLY_INTERVAL_IN_HOURS = int(sys.argv[3])
MAX_HOME_TIMELINE_LENGTH = int(sys.argv[4])
if len(sys.argv) > 5:
    MAX_FOLLOWINGS = int(sys.argv[5])
else:
    MAX_FOLLOWINGS = 0

if len(sys.argv) > 6:
    BACKFILL_FOLLOWINGS_FOR_USER = sys.argv[6]
else:
    BACKFILL_FOLLOWINGS_FOR_USER = ''

if len(sys.argv) > 7:
    MAX_FOLLOWERS = int(sys.argv[7])
else:
    MAX_FOLLOWERS = 0

os.system(f"python find_posts.py --server={SERVER} --access-token={ACCESS_TOKEN} --reply-interval-in-hours={REPLY_INTERVAL_IN_HOURS} --home-timeline-length={MAX_HOME_TIMELINE_LENGTH} --user={BACKFILL_FOLLOWINGS_FOR_USER} --max-followings={MAX_FOLLOWINGS} --max-followers={MAX_FOLLOWERS}")