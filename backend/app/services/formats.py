"""Resolution limits shared by member and guest video downloads."""


def limit_video_quality(ydl, quality: str | None) -> None:
    """Treat 720p as 1280x720 landscape or 720x1280 portrait.

    Filter first, then let yt-dlp select and merge its preferred video/audio.
    Unknown video dimensions are excluded rather than bypassing the limit.
    """
    if not quality:
        return
    limit = int(quality)
    select_best = ydl.build_format_selector("bv*+ba/b")

    def select(context):
        def allowed(fmt):
            if fmt.get("vcodec") == "none":
                return True  # Audio streams have no video resolution.
            dimensions = [fmt[key] for key in ("width", "height") if fmt.get(key) and fmt[key] > 0]
            return bool(dimensions) and min(dimensions) <= limit

        return select_best({
            **context,
            "formats": [fmt for fmt in context["formats"] if allowed(fmt)],
        })

    ydl.format_selector = select
