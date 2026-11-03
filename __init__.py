"""Motion Verdict for ComfyUI: is the clip really animated, or only a camera move over a still picture?"""

from .motion_verdict.node import MotionVerdict
from .motion_verdict.store import PREVIEWS

WEB_DIRECTORY = "./web"
PREVIEW_ROUTE = "/motion_verdict/preview/{token}"


def _register_route():
    try:
        from server import PromptServer
    except ImportError:  # imported outside ComfyUI (tests)
        return
    if getattr(PromptServer, "instance", None) is None:
        return
    from aiohttp import web

    @PromptServer.instance.routes.get(PREVIEW_ROUTE)
    async def motion_verdict_preview(request):
        data = PREVIEWS.get(request.match_info["token"])
        if data is None:
            return web.Response(status=404, text="Preview no longer in memory; run the node again.")
        return web.Response(body=data, content_type="video/mp4", headers={"Cache-Control": "no-store"})


_register_route()

NODE_CLASS_MAPPINGS = {"MotionVerdict": MotionVerdict}
NODE_DISPLAY_NAME_MAPPINGS = {"MotionVerdict": "Motion Verdict (animated / camera-only / still)"}
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
