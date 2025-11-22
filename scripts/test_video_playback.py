"""
Quick test script to verify moviepy can open the video and extract a frame.
This script is bundle-aware via a small `resource_path` helper similar to the
one used in `game.py` so it works when frozen with PyInstaller.
"""
import sys
import os
from moviepy import VideoFileClip


def resource_path(relative_path: str) -> str:
    """Resolve path for bundled assets when frozen with PyInstaller.
    Falls back to an absolute path in development.
    """
    try:
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
    except Exception:
        pass
    return os.path.abspath(relative_path)


VIDEO = resource_path('assets/videos/enterence_video.mp4')


try:
    clip = VideoFileClip(VIDEO)
    print('Loaded clip:', VIDEO, 'duration=', clip.duration)
    frame = clip.get_frame(min(0.5, max(0.01, clip.duration/2 if clip.duration>0 else 0.5)))
    # Save a single frame as an image to confirm decoding
    from PIL import Image
    import numpy as np
    arr = (frame * 255).astype('uint8') if frame.max() <= 1.0 else frame.astype('uint8')
    img = Image.fromarray(arr)
    out = 'test_frame_out.png'
    img.save(out)
    print('Saved test frame to', out)
    clip.close()
    sys.exit(0)
except Exception as e:
    print('ERROR during video test:', e)
    sys.exit(2)
