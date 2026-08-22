#!/usr/bin/env python3
# Docker entry point wrapper - modifies server binding for container environments

import sys
import os

# For Docker compatibility, we need to patch the server to listen on 0.0.0.0
# instead of 127.0.0.1 when running in a container
if os.getenv('CONTAINER_ENV'):
    # Monkey-patch the HOST constant before importing server
    import server as server_module
    server_module.HOST = '0.0.0.0'
    print("Console will bind to 0.0.0.0 for Docker container access")

# Run the server
if __name__ == "__main__":
    if '--launcher' in sys.argv:
        from server import launcher_main
        launcher_main()
    else:
        from server import main
        preferred_port = None
        if "--preferred-port" in sys.argv:
            idx = sys.argv.index("--preferred-port")
            try:
                preferred_port = int(sys.argv[idx + 1])
            except (ValueError, IndexError):
                pass
        main(
            preferred_port=preferred_port,
            open_browser="--no-browser" in sys.argv or os.getenv('CONTAINER_ENV'),
            log_to_file=os.getenv('CONTAINER_ENV') is not None
        )
