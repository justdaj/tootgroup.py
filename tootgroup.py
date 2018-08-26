## coding: utf-8
##
## tootgroup.py
## Version 0.2
##
##
## Andreas Schreiner
## @andis@chaos.social
## andreas.schreiner@sonnenmulde.at
##
## License: General Public License Version 3
## See attached LICENSE file.
##

import os
import re
import requests
from mastodon import Mastodon


#
# Configuration Variables
#
# CHANGE HERE for your mastodon instance (e.g. https://mastodon.social)
my_mastodon_instance='https://chaos.social'

accept_DMs = True
accept_retoots = True


## ONLY FOR FIRST RUN - this sets up app credentials for tootgroup.py
## UNCOMMENT ONCE FOR SETUP
#import sys
#
## Register app - only once!
#Mastodon.create_app(
#     'tootgroup.py',
#     api_base_url = my_mastodon_instance,
#     to_file = 'tootgroup_clientcred.secret'
#)
#
## Log in - either every time, or use persisted
#mastodon = Mastodon(
#    client_id = 'tootgroup_clientcred.secret',
#    api_base_url = my_mastodon_instance
#)
#
#mastodon.log_in(
#    input("Username (e-Mail): "),
#    input("Password: "),
#    to_file = 'tootgroup_usercred.secret'
#)
#sys.exit(0)
## END OF SETUP BLOCK



#
# Functions
#

def media_toot_again(orig_media_dict):
    """Re-upload media files to Mastodon for use in another toot.
    
    Mastodon does not allow the re-use of already uploaded media files (images, videos) in a new toot. This
    function downloads all media files from a toot and uploads them again. It returns a dict formatted in
    a proper way to be used with the Mastodon.status_post() function."""
    new_media_dict = []
    for media in orig_media_dict:
        media_data = requests.get(media.url).content
        # TODO: temporary file maganement needed here
        filename = os.path.basename(media.url)
        with open(filename, "wb") as handler: # use "wb" instead of "w" to enable binary mode (needed on Windows)
            handler.write(media_data)
        new_media_dict.append(mastodon.media_post(filename, description=media.description))
        os.remove(filename)
    return(new_media_dict)



#
# Execution starts here
#

# Create API instance
mastodon = Mastodon(
    client_id = 'tootgroup_clientcred.secret',
    access_token = 'tootgroup_usercred.secret',
    api_base_url = my_mastodon_instance
)


# Get the tootgroups account ID and use it to fetch the IDs
# of all users that are followed by  it.
my_account_username = mastodon.account_verify_credentials().username
my_account_id = mastodon.account_verify_credentials().id
my_group_members = mastodon.account_following(my_account_id)
my_group_member_ids = []
for member in my_group_members:
    my_group_member_ids.append(member.id)


# Get the time of the latest (re)toot from the group. Using it we
# can determine which messages are new since last run.
my_last_toot_time = mastodon.account_statuses(my_account_id)[0].created_at


# Get all notifications and filter for group toots.
#
# TODO: check for pagination should the list become too long
my_notifications = mastodon.notifications()
my_retoots = []
my_dm_reposts = []
for notification in my_notifications:
    # Only consider notifications that happened after the groups last toot
    # We have to use the time of notification and not the "status" directly since
    # not all notification types do have a status.
    if notification.created_at > my_last_toot_time:
        
        # Is retooting of public mentions configured?
        if accept_retoots:
            if notification.type == "mention" and notification.status.visibility == "public":
                # Only from group members (which means people that are followed by this group)
                if notification.account.id in my_group_member_ids:
                    # Only if the mention was preceeded by an "!". To check this, html tags have to be removed first.
                    repost_indicator = "!@" + my_account_username
                    status = re.sub("<.*?>", "", notification.status.content)
                    if repost_indicator in status:
                        my_retoots.append(notification)

        # Is reposting of direct messages configured? - if yes then:
        # Look for direct messages
        if accept_DMs:
            if notification.type == "mention" and notification.status.visibility == "direct":
                # Only from group members (which means people that are followed by this group)
                if notification.account.id in my_group_member_ids:
                    my_dm_reposts.append(notification)


# For retooting of public mentions
for retoot in my_retoots:
    mastodon.status_reblog(retoot.status.id)


# For reposting of direct messages
# Assemble new group toots and post them to the group timeline
for repost in my_dm_reposts:
    # Remove html tags from the status content
    status = re.sub("<.*?>", "", repost.status.content)
    # Remove @metafunk from the text as well as the double spaces that are left
    status = re.sub("@metafunk", "", status)
    in_reply_to_id = None
    # Get media files and prepare them for re-use in new toot
    media_ids = media_toot_again(repost.status.media_attachments)
    sensitivity = repost.status.sensitive
    visibility = "public"
    spoiler_text = repost.status.spoiler_text
    idempotency_key = None
    mastodon.status_post(status, in_reply_to_id, media_ids, sensitivity, visibility, spoiler_text, idempotency_key)
