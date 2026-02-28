#!/usr/bin/env python3
"""Data model for a single media file (video, subtitle, artwork, etc.)."""

# Standard Library
import dataclasses

# local repo modules
import moviemanager.core.constants


#============================================
@dataclasses.dataclass
class MediaFile:
	"""Represents a single media file (video, subtitle, artwork, etc.).

	Attributes:
		path: Full path to the file on disk.
		filename: Base filename without directory.
		filesize: Size in bytes.
		file_type: Categorization of the media file.
		video_codec: Video codec name (e.g. h264, hevc).
		video_width: Horizontal resolution in pixels.
		video_height: Vertical resolution in pixels.
		aspect_ratio: Display aspect ratio as a float.
		duration: Duration in seconds.
		audio_codec: Audio codec name (e.g. ac3, aac).
		audio_channels: Channel layout string (e.g. "5.1").
		audio_language: Language of the audio track.
		subtitle_language: Language of the subtitle track.
		container_format: Container format (e.g. mkv, mp4).
		video_3d: Whether the file contains 3D video.
	"""

	# file identity
	path: str = ""
	filename: str = ""
	filesize: int = 0
	file_type: moviemanager.core.constants.MediaFileType = (
		moviemanager.core.constants.MediaFileType.UNKNOWN
	)
	# video info
	video_codec: str = ""
	video_width: int = 0
	video_height: int = 0
	aspect_ratio: float = 0.0
	duration: int = 0
	# audio info
	audio_codec: str = ""
	audio_channels: str = ""
	audio_language: str = ""
	# subtitle info
	subtitle_language: str = ""
	# container
	container_format: str = ""
	# 3d
	video_3d: bool = False

	#============================================
	@property
	def resolution_label(self) -> str:
		"""Return a human-readable resolution label based on video height.

		Returns:
			One of "4K", "1080p", "720p", or "SD".
		"""
		if self.video_height >= 2160:
			return "4K"
		if self.video_height >= 1080:
			return "1080p"
		if self.video_height >= 720:
			return "720p"
		return "SD"
