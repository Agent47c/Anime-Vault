"""Small explicit API checks, run by a UI worker rather than on tab changes."""
import requests
from app import config


def check_services():
    services={};messages=[]
    for name in ('AniList','Jikan'):
        try:
            if name=='AniList':
                response=requests.post(config.ANILIST_GRAPHQL_URL,json={'query':'query { __typename }'},timeout=(3,3))
                response.raise_for_status();payload=response.json()
                ok=bool(isinstance(payload,dict) and (payload.get('data') or {}).get('__typename') and not payload.get('errors'))
            else:
                response=requests.get(config.JIKAN_BASE_URL.rstrip('/')+'/anime',params={'limit':1},timeout=(3,3))
                response.raise_for_status();payload=response.json()
                ok=bool(isinstance(payload,dict) and isinstance(payload.get('data'),list))
            services[name]=ok
            messages.append(name+(': Connected and checked' if ok else ': API response could not be verified'))
        except (requests.RequestException,ValueError,TypeError,AttributeError):
            services[name]=False;messages.append(name+': Unavailable or request failed')
    # Keep the pre-existing metadata offline gate consistent with its own API.
    config._is_offline=not services['AniList']
    return dict(services=services,description='\n'.join(messages))
