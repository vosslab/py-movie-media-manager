"""Probe video files for codec, resolution, and audio metadata via pymediainfo."""

# Standard Library
import os
import time

# PIP3 modules
import pymediainfo


# codec name normalization: pymediainfo codec ID -> short label
VIDEO_CODEC_MAP = {
	"avc": "h264",
	"avc1": "h264",
	"h264": "h264",
	"v_mpeg4/iso/avc": "h264",
	"hevc": "hevc",
	"hev1": "hevc",
	"v_mpegh/iso/hevc": "hevc",
	"h265": "hevc",
	"vp9": "vp9",
	"vp8": "vp8",
	"av1": "av1",
	"mpeg4": "mpeg4",
	"mpeg-4 visual": "mpeg4",
	"v_mpeg4/iso/sp": "mpeg4",
	"v_mpeg4/iso/asp": "mpeg4",
	"mpeg2": "mpeg2",
	"mpeg video": "mpeg2",
	"v_mpeg2": "mpeg2",
	"vc-1": "vc1",
	"vc1": "vc1",
}

AUDIO_CODEC_MAP = {
	"aac": "aac",
	"aac lc": "aac",
	"aac lc-sbr": "aac",
	"a_aac": "aac",
	"a_aac-2": "aac",
	"ac-3": "ac3",
	"ac3": "ac3",
	"a_ac3": "ac3",
	"e-ac-3": "eac3",
	"eac3": "eac3",
	"a_eac3": "eac3",
	"dts": "dts",
	"a_dts": "dts",
	"dts-hd ma": "dtshd",
	"dts-hd": "dtshd",
	"truehd": "truehd",
	"a_truehd": "truehd",
	"mlp fba": "truehd",
	"flac": "flac",
	"a_flac": "flac",
	"mp3": "mp3",
	"mpeg audio": "mp3",
	"a_mpeg/l3": "mp3",
	"pcm": "pcm",
	"opus": "opus",
	"vorbis": "vorbis",
}

# channel count -> human-readable label
CHANNEL_LABEL_MAP = {
	1: "1.0",
	2: "2.0",
	3: "2.1",
	6: "5.1",
	7: "6.1",
	8: "7.1",
}


#============================================
def _normalize_video_codec(raw: str) -> str:
	"""Normalize a raw video codec string to a short label.

	Args:
		raw: codec identifier from pymediainfo (e.g. "AVC", "HEVC").

	Returns:
		Short lowercase label like "h264", "hevc", or the original lowered.
	"""
	key = raw.strip().lower()
	label = VIDEO_CODEC_MAP.get(key, key)
	return label


#============================================
def _normalize_audio_codec(raw: str) -> str:
	"""Normalize a raw audio codec string to a short label.

	Args:
		raw: codec identifier from pymediainfo (e.g. "AAC", "AC-3").

	Returns:
		Short lowercase label like "aac", "ac3", or the original lowered.
	"""
	key = raw.strip().lower()
	label = AUDIO_CODEC_MAP.get(key, key)
	return label


#============================================
def _normalize_channels(count) -> str:
	"""Convert a channel count to a human-readable label.

	Args:
		count: number of audio channels (int or string).

	Returns:
		Label like "5.1", "7.1", "2.0", or empty string on failure.
	"""
	if count is None:
		return ""
	# pymediainfo may return int or string
	if isinstance(count, str):
		# handle values like "6" or "8 / 6" (object-based tracks)
		count = count.split("/")[0].strip()
	channel_int = int(count)
	label = CHANNEL_LABEL_MAP.get(channel_int, f"{channel_int}ch")
	return label


#============================================
def probe_media_file(path: str) -> dict:
	"""Extract codec, resolution, and audio metadata from a video file.

	Uses pymediainfo to parse the file and returns a dict with
	normalized values for video codec, audio codec, resolution,
	channels, and container format.

	Args:
		path: full path to the video file.

	Returns:
		Dict with keys: video_codec, video_width, video_height,
		audio_codec, audio_channels, container_format.
		Empty-string defaults if parsing fails.
	"""
	# default result with empty values
	result = {
		"video_codec": "",
		"video_width": 0,
		"video_height": 0,
		"duration_seconds": 0,
		"audio_codec": "",
		"audio_channels": "",
		"container_format": "",
	}
	# bail out if file does not exist
	if not os.path.isfile(path):
		return result

	# parse the media file
	media_info = pymediainfo.MediaInfo.parse(path)

	for track in media_info.tracks:
		if track.track_type == "General" and not result["container_format"]:
			# extract container format from general track
			fmt = track.format or ""
			result["container_format"] = fmt.strip().lower()
			# extract duration in seconds from general track
			dur_ms = track.duration
			if dur_ms is not None:
				result["duration_seconds"] = int(float(dur_ms) / 1000)

		elif track.track_type == "Video" and not result["video_codec"]:
			# extract video codec and resolution from first video track
			codec_id = track.codec_id or track.format or ""
			result["video_codec"] = _normalize_video_codec(codec_id)
			result["video_width"] = int(track.width or 0)
			result["video_height"] = int(track.height or 0)

		elif track.track_type == "Audio" and not result["audio_codec"]:
			# extract audio codec and channels from first audio track
			codec_id = track.codec_id or track.format or ""
			result["audio_codec"] = _normalize_audio_codec(codec_id)
			# get channel count
			channels_raw = track.channel_s
			if channels_raw is not None:
				result["audio_channels"] = _normalize_channels(
					channels_raw
				)

	return result


#============================================
def probe_movie_list(movies: list, progress_callback=None) -> None:
	"""Probe all video MediaFiles in a list of movies for codec metadata.

	Iterates through each movie's media files, finds VIDEO-type files,
	and calls probe_media_file() to populate codec/resolution fields
	in-place. Skips files that already have video_codec set.

	Args:
		movies: List of Movie objects to probe.
		progress_callback: Optional callable(current, total, message)
			for status bar updates.
	"""
	# local repo modules
	import moviemanager.core.constants
	import moviemanager.core.nfo.writer

	# collect (movie, media_file) pairs for all video files
	video_pairs = []
	for movie in movies:
		for mf in movie.media_files:
			if mf.file_type == moviemanager.core.constants.MediaFileType.VIDEO:
				video_pairs.append((movie, mf))

	total = len(video_pairs)
	probed_count = 0
	skipped_count = 0
	probe_start = time.monotonic()
	for i, (movie, mf) in enumerate(video_pairs):
		# skip files already probed
		if mf.video_codec:
			skipped_count += 1
			if progress_callback:
				progress_callback(i + 1, total, f"Skipping: {mf.filename}")
			continue
		# report progress before probing
		if progress_callback:
			progress_callback(i + 1, total, f"Probing: {mf.filename}")
		# probe and populate fields in-place
		probed_count += 1
		probe_data = probe_media_file(mf.path)
		mf.video_codec = probe_data["video_codec"]
		mf.video_width = probe_data["video_width"]
		mf.video_height = probe_data["video_height"]
		mf.duration = probe_data["duration_seconds"]
		mf.audio_codec = probe_data["audio_codec"]
		mf.audio_channels = probe_data["audio_channels"]
		mf.container_format = probe_data["container_format"]
		# set movie runtime from probe if not already set by NFO
		if movie.runtime == 0 and mf.duration > 0:
			movie.runtime = round(mf.duration / 60)
		# auto-save probe results to NFO if an NFO file exists
		if movie.nfo_path and os.path.isfile(movie.nfo_path):
			moviemanager.core.nfo.writer.write_nfo(movie, movie.nfo_path)

	# summary timing for the full probe pass
	probe_ms = (time.monotonic() - probe_start) * 1000
	if probed_count > 0:
		avg_ms = probe_ms / probed_count
		print(
			f"[probe] {probed_count} probed, {skipped_count} skipped, "
			f"{probe_ms:.0f}ms total, {avg_ms:.0f}ms/file"
		)
	else:
		print(f"[probe] {skipped_count} skipped, nothing to probe")
