# This script is a sample script that you can schedule 
# to run every 10 minutes from your cron job.
# Supply any other arguments, as you see fit.


# In this script, FediFetcher will fetch remote replies for multiple 
# users on your instance

# TOKEN1, TOKEN2, and TOKEN3 belong to 3 different users here.


# Sample schedule:
# */10 * * * * /usr/bin/bash /path/to/FediFetcher.sh

###################### IMPORTANT ######################
#                                                     #
#  YOU SHOULD RUN THIS SCRIPT MANUALLY AT LEAST ONCE  #
#   WITH YOUR CHOSEN ARGUMENTS, TO AVOID CONCURRENT   #
#             EXECUTIONS OF FEDIFETCHER!              #
#                                                     #
###################### IMPORTANT ######################


cd /path/to/FediFetcher
python3 find_posts.py \
 --access-token=TOKEN1 \
 --access-token=TOKEN2 \
 --access-token=TOKEN3 \
 --server=your.server.social \
 --home-timeline-length=200 \
 --max-followings=80 \
 --from-notifications=1 \
 --lock-hours=1 