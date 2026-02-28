#!/usr/bin/env python3
"""Constants and enumerations for movie media manager."""

# Standard Library
import enum


#============================================
class MediaFileType(enum.Enum):
	"""Enumeration of media file types recognized by the manager."""
	VIDEO = "video"
	VIDEO_EXTRA = "video_extra"
	TRAILER = "trailer"
	SAMPLE = "sample"
	AUDIO = "audio"
	SUBTITLE = "subtitle"
	NFO = "nfo"
	POSTER = "poster"
	FANART = "fanart"
	BANNER = "banner"
	CLEARART = "clearart"
	DISCART = "discart"
	LOGO = "logo"
	THUMB = "thumb"
	SEASON_POSTER = "season_poster"
	EXTRAFANART = "extrafanart"
	EXTRATHUMB = "extrathumb"
	GRAPHIC = "graphic"
	TEXT = "text"
	UNKNOWN = "unknown"


# common video file extensions
VIDEO_EXTENSIONS: frozenset = frozenset({
	".avi", ".mkv", ".mp4", ".m4v", ".mov", ".wmv", ".ogm", ".strm",
	".rm", ".rmvb", ".divx", ".vob", ".ts", ".m2ts", ".mpg", ".mpeg",
	".flv", ".webm", ".3gp",
})

# subtitle file extensions
SUBTITLE_EXTENSIONS: frozenset = frozenset({
	".srt", ".sub", ".smi", ".ssa", ".ass", ".idx", ".sup", ".vtt",
})

# audio file extensions
AUDIO_EXTENSIONS: frozenset = frozenset({
	".mp3", ".flac", ".ogg", ".wav", ".wma", ".aac", ".m4a",
})

# image file extensions
IMAGE_EXTENSIONS: frozenset = frozenset({
	".jpg", ".jpeg", ".png", ".tbn", ".gif", ".bmp", ".webp",
})

# directories to skip during scanning
SKIP_DIRS: frozenset = frozenset({
	"$RECYCLE.BIN", "@eaDir", ".AppleDouble", ".actors", ".DS_Store",
	"extrafanart", "extrathumbs", "extras", "Extras",
	"sample", "Sample", "subs", "Subs", "subtitles", "Subtitles",
	"behind the scenes", "deleted scenes", "featurettes",
	"interviews", "scenes", "shorts", "trailers",
})

# artwork type to possible filenames mapping
ARTWORK_FILENAMES: dict = {
	"poster": ["poster.jpg", "poster.png", "movie.jpg", "movie.png", "folder.jpg"],
	"fanart": ["fanart.jpg", "fanart.png"],
	"banner": ["banner.jpg", "banner.png"],
	"clearart": ["clearart.png"],
	"logo": ["logo.png", "clearlogo.png"],
	"discart": ["disc.png", "discart.png"],
	"thumb": ["thumb.jpg", "thumb.png", "landscape.jpg"],
}

# stopwords for filename parsing (from Java ParserUtils)
STOPWORDS: list = [
	"1080", "1080i", "1080p", "480i", "480p", "576i", "576p",
	"720", "720i", "720p",
	"ac3", "ac3ld", "ac3md", "aoe", "avc", "atmos",
	"bd5", "bdrip", "blueray", "bluray", "brrip",
	"cam", "cd1", "cd2", "cd3", "cd4", "cd5", "cd6", "cd7", "cd8", "cd9",
	"complete", "custom",
	"dc", "disc1", "disc2", "disc3", "disc4", "disc5",
	"disc6", "disc7", "disc8", "disc9",
	"divx", "divx5", "dl", "docu", "dolbyvision",
	"dsr", "dsrip", "dts", "dtv", "dubbed", "dutch",
	"dvd", "dvd1", "dvd2", "dvd3", "dvd4", "dvd5",
	"dvd6", "dvd7", "dvd8", "dvd9",
	"dvdivx", "dvdrip", "dvdscr", "dvdscreener",
	"emule", "etm", "extended",
	"flv", "fragment", "fs",
	"german",
	"h264", "h265", "hddvd", "hdr", "hdr10", "hdrip",
	"hdtv", "hdtvrip", "hevc", "hrhd", "hrhdtv",
	"ind", "internal",
	"ld", "limited",
	"md", "multisubs",
	"nfo", "nfofix", "ntg", "ntsc",
	"ogg", "ogm",
	"pal", "pdtv", "proper", "pso",
	"r3", "r5", "read", "remux", "repack", "rerip",
	"retail", "roor", "rs", "rsvcd",
	"screener", "se", "subbed", "svcd", "swedish",
	"tc", "telecine", "telesync", "truehd", "ts",
	"uhd", "uncut", "unrated",
	"vcf",
	"webdl", "webrip", "workprint", "ws", "www",
	"x264", "x265", "xf", "xvid", "xvidvd", "xxx",
	"2160p", "4k",
]
