"""Chrome native-host entry point: stdout contains framed JSON only."""
from app.core.chrome_bridge import run

if __name__=='__main__':
    raise SystemExit(run())
