"""Mobile-friendly "run a saved workflow" page served at /phone.

The page lives outside WEB_DIRECTORY on purpose: every .js under web/ is
loaded into the main frontend as an extension.
"""

import os

PHONE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phone")

try:
    from aiohttp import web
    from server import PromptServer

    @PromptServer.instance.routes.get("/phone")
    async def _phone_route(request):
        return web.FileResponse(
            os.path.join(PHONE_DIR, "index.html"),
            headers={"Cache-Control": "no-cache"},
        )
except (ImportError, AttributeError):
    pass  # not running inside ComfyUI
