from collections import defaultdict
import requests
from urllib.parse import urlparse

from fabric.api import task


STUDIO_URL = 'https://studio.learningequality.org'
API_PUBLIC_ENDPOINT = '/api/public/v1/channels'

CATALOG_URL = "https://catalog.learningequality.org"
API_CATALOG_ENDPOINT = "/api/catalog?page_size=200&public=true&published=true"

CATALOG_DEMO_SERVERS = {
    'ar': 'https://kolibri-catalog-ar.learningequality.org',
    'en': 'https://kolibri-catalog-en.learningequality.org',
    'es': 'https://kolibri-catalog-es.learningequality.org',
    'fr': 'https://kolibri-catalog-fr.learningequality.org',
    'hi': 'https://kolibri-catalog-hi.learningequality.org',
    'other': 'https://kolibri-demo.learningequality.org',
}


# CATALOG SERVER CHECKS
################################################################################

@task
def check_catalog_channels():
    """
    Obtain the list of public channels on Kolibri Studio and compare with the
    list of channels imported on the catalog demo servers. Prints the following:
      - list channels that are not present on any demo servers
      - list channels that are oudated (studio version > version on demo server)
      - list channels with missing or broken demo_server_url
    """
    # 1. Get Studio channels
    studio_channels = requests.get(STUDIO_URL + API_PUBLIC_ENDPOINT).json()
    studio_channels_by_id = dict((ch['id'], ch) for ch in studio_channels)
    print('Found', len(studio_channels_by_id), 'PUBLIC channels on Studio.')

    # 2. Get Catalog channels
    catalog_data = requests.get(CATALOG_URL + API_CATALOG_ENDPOINT).json()
    catalog_channels = catalog_data['results']
    catalog_channels_by_id = dict((ch['id'], ch) for ch in catalog_channels)
    print('Found', len(studio_channels_by_id), 'PUBLIC channels in Catalog.')

    # 3. Get Catalog demo server channels
    demoserver_channels = []
    for lang, demoserver in CATALOG_DEMO_SERVERS.items():
        # print('   - getting channel list from the', lang, 'demoserver...')
        channels = requests.get(demoserver + API_PUBLIC_ENDPOINT).json()
        for channel in channels:
            channel['demoserver'] = demoserver
            channel['lang'] = lang
            demoserver_channels.append(channel)
    # group all channels found by `channel_id`
    demoserver_channels_by_id = defaultdict(list)
    for ch in demoserver_channels:
        ch_id = ch['id']
        demoserver_channels_by_id[ch_id].append(ch)
    print('Found', len(demoserver_channels_by_id), 'channels on demoservers.')

    # Sanity check: Studio channels and Catalog channels should be identical
    studio_ids = set(studio_channels_by_id.keys())
    catalog_ids = set(catalog_channels_by_id.keys())
    if studio_ids != catalog_ids:
        print('WARNING: Studio PUBCLIC channels and Catalog channels differ!')


    # REPORT A: PUBLIC channels must be imported on at least one demoserver
    print('\n\nREPORT A: Check no channels missing from catalog demoservers:')
    for ch_id, studio_ch in studio_channels_by_id.items():
        if ch_id not in demoserver_channels_by_id:
            print(' - Cannot find', ch_id, studio_ch['name'])

    # REPORT B: Catalog demoservers must have the latest version of the channel
    print('\n\nREPORT B: Check channel versions on catalog demoservers:')
    for ch_id, studio_ch in studio_channels_by_id.items():
        latest_version = studio_ch["version"]
        if ch_id in demoserver_channels_by_id:
            demoserver_channels = demoserver_channels_by_id[ch_id]
            for channel in demoserver_channels:
                if channel["version"] < latest_version:
                    print(' - Channel', ch_id, studio_ch['name'], 'needs to be updated on', channel['demoserver'])

    # REPORT C: Catalog demoservers links must point to an existing channel
    print('\n\nREPORT C: Check the demo_server_url links in Catalog are good:')
    for ch_id, catalog_ch in catalog_channels_by_id.items():
        demo_server_url = catalog_ch["demo_server_url"]
        if demo_server_url:
            if ch_id not in demo_server_url:
                print(' - ERROR: demo_server_url', demo_server_url, 'does not contain', ch_id)
            parsed_url_obj = urlparse(demo_server_url)
            catalog_demoserver = parsed_url_obj.scheme + '://' + parsed_url_obj.netloc
            if ch_id in demoserver_channels_by_id:
                found = False
                demoserver_channels = demoserver_channels_by_id[ch_id]
                for channel in demoserver_channels:
                    if channel['demoserver'] == catalog_demoserver:
                        found = True
                if not found:
                    print(' - Channel', ch_id, catalog_ch['name'], 'has demo_server_url',
                        demo_server_url, 'but it is not present on that server')
        else:
            print(' - Channel', ch_id, catalog_ch['name'], 'does not have a demo_server_url')
