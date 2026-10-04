"""mediainfo: reads just enough of an audio or image file to check it against Roblox's upload limits.

Standard library only. Audio: WAV, FLAC, Ogg (Vorbis or Opus) and MP3. Images: PNG, JPEG, BMP and TGA. Each probe
works on the file's bytes (uploads are capped at 20 MB, so reading the whole file is fine).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass


class ProbeError(ValueError):
    """The file isn't what its extension says, or its headers can't be read."""


@dataclass
class MediaInfo:
    kind: str  # "audio" or "image"
    format: str
    duration: float | None = None  # seconds
    sample_rate: int | None = None  # Hz
    channels: int | None = None
    width: int | None = None  # pixels
    height: int | None = None


# ---------------------------------------------------------------------------------------------------------------
# Audio


def probe_wav(data: bytes) -> MediaInfo:
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ProbeError("not a WAV file")
    pos, rate, channels, byte_rate, size = 12, None, None, None, None
    while pos + 8 <= len(data):
        chunk, length = data[pos:pos + 4], struct.unpack_from("<I", data, pos + 4)[0]
        if chunk == b"fmt " and pos + 24 <= len(data):
            _fmt, channels, rate, byte_rate = struct.unpack_from("<HHII", data, pos + 8)
        elif chunk == b"data":
            size = length
            break
        pos += 8 + length + (length & 1)
    if not rate or not byte_rate or size is None:
        raise ProbeError("WAV file has no fmt or data chunk")
    return MediaInfo("audio", "wav", size / byte_rate, rate, channels)


def probe_flac(data: bytes) -> MediaInfo:
    if data[:4] != b"fLaC" or len(data) < 8 + 18:
        raise ProbeError("not a FLAC file")
    info = data[8:8 + 18]  # STREAMINFO comes first
    rate = (info[10] << 12) | (info[11] << 4) | (info[12] >> 4)
    channels = ((info[12] >> 1) & 0x7) + 1
    samples = ((info[13] & 0x0F) << 32) | struct.unpack_from(">I", info, 14)[0]
    if not rate:
        raise ProbeError("FLAC file has no sample rate")
    return MediaInfo("audio", "flac", samples / rate if samples else None, rate, channels)


def probe_ogg(data: bytes) -> MediaInfo:
    if data[:4] != b"OggS":
        raise ProbeError("not an Ogg file")
    start = 27 + data[26]  # the first packet follows the 27-byte page header and its segment table
    first = data[start:start + 64]
    if first.startswith(b"\x01vorbis"):
        channels, rate = first[11], struct.unpack_from("<I", first, 12)[0]
        fmt, pre_skip = "ogg/vorbis", 0
    elif first.startswith(b"OpusHead"):
        channels, pre_skip = first[9], struct.unpack_from("<H", first, 10)[0]
        rate, fmt = 48_000, "ogg/opus"  # Opus timestamps always count at 48 kHz
    else:
        raise ProbeError("Ogg file isn't Vorbis or Opus")
    last = data.rfind(b"OggS")
    granule = struct.unpack_from("<q", data, last + 6)[0] if last >= 0 and last + 14 <= len(data) else -1
    duration = (granule - pre_skip) / rate if granule > 0 and rate else None
    reported_rate = struct.unpack_from("<I", first, 12)[0] if fmt == "ogg/opus" else rate
    return MediaInfo("audio", fmt, duration, reported_rate or rate, channels)


MP3_BITRATES = {  # (MPEG-1?, layer 3) kbps by index
    True: [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
    False: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
}
MP3_RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}


def probe_mp3(data: bytes) -> MediaInfo:
    pos = 0
    if data[:3] == b"ID3" and len(data) >= 10:
        size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
        pos = 10 + size
    while pos + 4 <= len(data):
        if data[pos] == 0xFF and (data[pos + 1] & 0xE0) == 0xE0:
            break
        pos += 1
    else:
        raise ProbeError("no MP3 audio frames found")
    header = struct.unpack_from(">I", data, pos)[0]
    version = (header >> 19) & 0x3  # 3 = MPEG-1, 2 = MPEG-2, 0 = MPEG-2.5
    layer = (header >> 17) & 0x3  # 1 = layer III
    bitrate_index, rate_index = (header >> 12) & 0xF, (header >> 10) & 0x3
    mode = (header >> 6) & 0x3
    if version == 1 or layer != 1 or rate_index == 3 or bitrate_index in (0, 15):
        raise ProbeError("MP3 file isn't MPEG layer III")
    mpeg1 = version == 3
    rate = MP3_RATES[version][rate_index]
    channels = 1 if mode == 3 else 2
    samples_per_frame = 1152 if mpeg1 else 576
    side = (17 if channels == 1 else 32) if mpeg1 else (9 if channels == 1 else 17)
    xing = pos + 4 + side
    if data[xing:xing + 4] in (b"Xing", b"Info") and data[xing + 7] & 0x1:
        frames = struct.unpack_from(">I", data, xing + 8)[0]
        return MediaInfo("audio", "mp3", frames * samples_per_frame / rate, rate, channels)
    kbps = MP3_BITRATES[mpeg1][bitrate_index]
    return MediaInfo("audio", "mp3", (len(data) - pos) * 8 / (kbps * 1000), rate, channels)  # constant-bitrate estimate


# ---------------------------------------------------------------------------------------------------------------
# Images


def probe_png(data: bytes) -> MediaInfo:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ProbeError("not a PNG file")
    width, height = struct.unpack_from(">II", data, 16)
    return MediaInfo("image", "png", width=width, height=height)


def probe_jpeg(data: bytes) -> MediaInfo:
    if data[:2] != b"\xff\xd8":
        raise ProbeError("not a JPEG file")
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7 or marker == 0xFF:
            pos += 1 if marker == 0xFF else 2
            continue
        length = struct.unpack_from(">H", data, pos + 2)[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC) and pos + 9 <= len(data):
            height, width = struct.unpack_from(">HH", data, pos + 5)
            return MediaInfo("image", "jpeg", width=width, height=height)
        pos += 2 + length
    raise ProbeError("JPEG file has no size")


def probe_bmp(data: bytes) -> MediaInfo:
    if data[:2] != b"BM" or len(data) < 26:
        raise ProbeError("not a BMP file")
    width, height = struct.unpack_from("<ii", data, 18)
    return MediaInfo("image", "bmp", width=abs(width), height=abs(height))


def probe_tga(data: bytes) -> MediaInfo:
    if len(data) < 18 or data[2] not in (1, 2, 3, 9, 10, 11):
        raise ProbeError("not a TGA file")
    width, height = struct.unpack_from("<HH", data, 12)
    return MediaInfo("image", "tga", width=width, height=height)


PROBES = {
    ".wav": probe_wav, ".flac": probe_flac, ".ogg": probe_ogg, ".mp3": probe_mp3,
    ".png": probe_png, ".jpg": probe_jpeg, ".jpeg": probe_jpeg, ".bmp": probe_bmp, ".tga": probe_tga,
}


def probe(data: bytes, extension: str) -> MediaInfo:
    fn = PROBES.get(extension.lower())
    if not fn:
        raise ProbeError(f"{extension} files can't be uploaded")
    try:
        return fn(data)
    except (struct.error, IndexError):
        raise ProbeError(f"the file is cut short or isn't a real {extension} file") from None
