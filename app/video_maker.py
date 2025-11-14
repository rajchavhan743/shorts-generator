import os
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, TextClip
)
import math
from pydub.utils import mediainfo

# Config
WIDTH = 1080
HEIGHT = 1920
FPS = 25
READING_WPS = 3.0  # words per second approximate for timing (180 wpm)

def get_audio_duration(path):
    # fallback using moviepy AudioFileClip
    return AudioFileClip(path).duration

def split_text_to_subs(full_text, audio_duration, max_words_per_chunk=8):
    """
    Splits text into subtitle segments and computes start/end times scaled to audio duration.
    """
    words = full_text.strip().split()
    if not words:
        return []

    # naive chunking by words
    chunks = []
    i = 0
    n = len(words)
    while i < n:
        j = min(n, i + max_words_per_chunk)
        chunks.append(" ".join(words[i:j]))
        i = j

    # compute approximate duration per chunk using reading speed
    durations = [max(0.5, len(c.split()) / READING_WPS) for c in chunks]
    total_estimated = sum(durations)
    if total_estimated <= 0:
        total_estimated = len(durations) * 1.0

    # scale durations so they sum to audio_duration
    scale = audio_duration / total_estimated if total_estimated > 0 else 1.0
    durations = [d * scale for d in durations]

    # build list of (start, end, text)
    subs = []
    cursor = 0.0
    for d, text in zip(durations, chunks):
        subs.append((cursor, cursor + d, text))
        cursor += d
    # last end might be slightly less than audio_duration due to rounding; ensure final end == audio_duration
    if subs:
        start, end, text = subs[-1]
        subs[-1] = (start, audio_duration, text)
    return subs

def make_vertical_clip_from_image(path, duration, zoom_speed=0.05):
    """
    Creates a clip sized to (WIDTH, HEIGHT) from an image applying slow zoom-in.
    zoom_speed: fractional per second (e.g., 0.05 => 5% scale increase per second)
    """
    img = ImageClip(path).set_duration(duration)

    # initial scale so smaller side fits inside canvas
    img = img.resize(width=WIDTH) if img.w < img.h else img.resize(height=HEIGHT)
    # apply a dynamic resize (zoom in)
    def dynamic_resize(get_frame, t):
        factor = 1 + zoom_speed * t
        return get_frame(t)  # MoviePy supports .fl_time/fl but simpler to use .resize with lambda

    # MoviePy lambda resize:
    zoomed = img.fx(lambda clip: clip.resize(lambda t: 1 + zoom_speed * t))
    # place in center and composite on black background canvas
    comp = CompositeVideoClip([zoomed.set_position("center")], size=(WIDTH, HEIGHT)).set_duration(duration)
    comp = comp.set_fps(FPS)
    return comp

def burn_subtitles_on_clip(base_clip, subtitles, font="Arial-Bold", fontsize=48, color="white"):
    """
    subtitles: list of (start, end, text)
    Returns CompositeVideoClip with TextClips placed at bottom overlayed at start times.
    """
    subs_clips = []
    for start, end, text in subtitles:
        txt_clip = TextClip(
            text,
            fontsize=fontsize,
            font=font,
            color=color,
            method="caption",
            size=(WIDTH - 200, None)  # wrap width
        ).set_start(start).set_duration(end - start).set_position(("center", HEIGHT - 200))
        # add subtle background strip for readability
        # MoviePy TextClip doesn't have background param: create a semi-transparent box via TextClip with bg_color could be heavy.
        subs_clips.append(txt_clip)
    return CompositeVideoClip([base_clip, *subs_clips], size=(WIDTH, HEIGHT)).set_duration(base_clip.duration)

def build_video(image_paths, audio_path, subtitle_text, output_path, zoom_speed=0.03):
    """
    Main function:
    - split audio length across image durations evenly
    - make each image clip (slow zoom-in)
    - concatenate, overlay subtitles split from text
    - set audio
    - write output
    """
    audio_dur = get_audio_duration(audio_path)
    n_images = max(1, len(image_paths))
    # allocate durations: split audio across images evenly
    per_image = audio_dur / n_images

    image_clips = []
    for img in image_paths:
        clip = make_vertical_clip_from_image(img, duration=per_image, zoom_speed=zoom_speed)
        image_clips.append(clip)

    # concatenate images
    video = concatenate_videoclips(image_clips, method="compose")
    # subtitles
    subs = split_text_to_subs(subtitle_text, audio_dur)
    final = burn_subtitles_on_clip(video, subs)

    # set audio
    audio = AudioFileClip(audio_path)
    final = final.set_audio(audio)

    # write
    tmp_out = output_path
    final.write_videofile(tmp_out, codec="libx264", audio_codec="aac", fps=FPS, threads=0, preset="medium")
    return tmp_out
