# Runtime hook: ensure bundled ffmpeg is discoverable and executable when frozen
import os
import sys
import stat

def _set_ffmpeg_env():
    if not getattr(sys, 'frozen', False):
        return
    meipass = getattr(sys, '_MEIPASS', None)
    if not meipass:
        return

    ff_bin = None
    # Common candidate locations inside the extracted bundle
    candidates = [
        os.path.join(meipass, 'ffmpeg'),
        os.path.join(meipass, 'ffmpeg', 'ffmpeg-macos-aarch64-v7.1'),
        os.path.join(meipass, 'Frameworks', 'ffmpeg'),
        os.path.join(meipass, 'Frameworks', 'ffmpeg', 'ffmpeg-macos-aarch64-v7.1'),
    ]

    for c in candidates:
        if os.path.isfile(c):
            ff_bin = c
            break
        if os.path.isdir(c):
            # pick the first regular file inside
            try:
                for name in os.listdir(c):
                    p = os.path.join(c, name)
                    if os.path.isfile(p):
                        ff_bin = p
                        break
            except Exception:
                continue
            if ff_bin:
                break

    if not ff_bin:
        return

    # Report and make sure it's executable
    try:
        st = os.stat(ff_bin).st_mode
        exec_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        if not (st & exec_bits):
            os.chmod(ff_bin, st | exec_bits)
    except Exception:
        # best-effort; don't fail the app start if chmod fails
        pass

    # Only set if not already provided by environment
    os.environ.setdefault('IMAGEIO_FFMPEG_EXE', ff_bin)


# Execute on import (PyInstaller will import runtime hooks at startup)
_set_ffmpeg_env()
