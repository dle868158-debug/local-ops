import os
import sys

os.environ.setdefault("CONTAINER_ENV", "1")
os.environ.setdefault("CONSOLE_HOST", "0.0.0.0")

import server

# Run the server
if __name__ == "__main__":
    preferred_port = None
    if "--preferred-port" in sys.argv:
        idx = sys.argv.index("--preferred-port")
        try:
            preferred_port = int(sys.argv[idx + 1])
        except (ValueError, IndexError):
            pass
    server.main(preferred_port=preferred_port, open_browser=False, log_to_file=True)
