"""Validate saved setup using real client, folder and browser bridge state."""
from pathlib import Path
import tempfile
from app import db
from app.core import downloads,source_bridge
from app.core.chrome_bridge import origin


def checks(test_source=False,cancelled=lambda:False):
    config=downloads.settings();result={}
    try: result['engine']=downloads.test_connection(config)
    except Exception as error: result['engine']='Failed: '+str(error)
    try:
        folder=Path(config['destination'])
        if not folder.is_absolute(): raise ValueError('Choose an absolute download folder.')
        folder.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryFile(dir=folder) as probe: probe.write(b'Anime Vault folder check');probe.flush()
        result['folder']='Ready: '+str(folder)
    except (OSError,ValueError) as error: result['folder']='Failed: '+str(error)
    bridge=source_bridge.connection()
    result['extension']='Connected' if bridge['connected'] and bridge.get('enabled') else 'Needs attention: Open Chrome and enable the extension for your source.'
    try:
        downloads.search_url(config['source'],'connection test')
        result['source']='URL valid'
        if not bridge['connected'] or not bridge.get('enabled') or bridge.get('site')!=origin(config['source']):
            result['source']='Needs attention: Enable this source in the Chrome popup.'
        elif test_source:
            request=source_bridge.enqueue(downloads.search_url(config['source'],'Anime Vault connection test'),'Setup test')
            rows=source_bridge.wait(request,cancelled)
            result['source']=f'Connected: source returned {len(rows)} readable releases (zero is valid for a test query).'
    except Exception as error: result['source']='Failed: '+str(error)
    result['preferences']='Saved: '+config['group']+' / '+config['quality']
    db.set_state('download_setup.checks',__import__('json').dumps(result))
    return result
