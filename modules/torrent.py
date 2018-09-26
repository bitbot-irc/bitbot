#--ignore

import tempfile, time
import libtorrent

def magnet(magnet):
    #log.info("Opening session for link %s", url)

    session = libtorrent.session()
    session.add_extension('ut_metadata')
    session.add_extension('ut_pex')
    session.add_extension('metadata_transfer')
    session.add_dht_router("router.utorrent.com", 6881)
    session.add_dht_router("router.bittorrent.com", 6881)
    session.add_dht_router("dht.transmissionbt.com", 6881)
    session.add_dht_router("dht.aelitis.com", 6881)
    session.start_dht()
    session.start_lsd()
    session.start_upnp()
    session.start_natpmp()

    params = {'save_path': "/dev/null", 'duplicate_is_error': True,
        'storage_mode': libtorrent.storage_mode_t(2), 'paused': False,
        'auto_managed': True}
    handle = libtorrent.add_magnet_uri(session, magnet, params)

    #log.info("Waiting metadata")
    has_metadata = False
    for i in range(10):
        if handle.has_metadata():
            print("yes!")
            has_metadata = True
            break
        else:
            time.sleep(1)
    if not has_metadata:
        print("no!")
        #event["stderr"].write("Timed out getting magnet info")
        return
    session.pause()

    #log.info("Metadata retrieved")
    torrent_info = handle.get_torrent_info()
    print(dir(torrent_info))

    session.remove_torrent(handle)
    #log.info("Torrent file saved to %s", file_path)

magnet("magnet:?xt=urn:btih:ea5938cbb6176a675a3e71682faf9801b5b6116f")
