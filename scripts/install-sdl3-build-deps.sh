#!/usr/bin/env bash
# System headers the sdl3 vcpkg port builds its X11 and Wayland support against, exactly as the port's portfile lists
# them. SDL loads the client libraries at run time, so only a build needs these. One list, called by every workflow
# that builds liara-platform on Linux, so the callers cannot drift apart. Expects `apt-get update` to have run.
set -euo pipefail

sudo apt-get install -y --no-install-recommends \
    libx11-dev libxft-dev libxext-dev \
    libwayland-dev libxkbcommon-dev libegl1-mesa-dev
