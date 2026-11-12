"""Chrome native-host entry point: stdout contains framed JSON only."""
# AUDIT-START
import os
if os.environ.get('APP_PROFILE') == '1':
    from app.audit_profile import bootstrap
    bootstrap()
# AUDIT-END
from app.core.chrome_bridge import run

if __name__=='__main__':
    raise SystemExit(run())
