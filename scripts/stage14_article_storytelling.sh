#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

uv run python -m unittest discover -s tests -v
python3 -m compileall src tests
uv run llm-computer-article-story

export PATH="/Users/lijie/.nvm/versions/node/v24.10.0/bin:$PATH"
export GOOGLE_CHROME_BIN="${GOOGLE_CHROME_BIN:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

npm install --prefix visuals/remotion
npx --prefix visuals/remotion remotion still visuals/remotion/src/index.jsx five-implementations-poster docs/assets/five-implementation-overview.png --concurrency=1 --browser-executable="$GOOGLE_CHROME_BIN"
npx --prefix visuals/remotion remotion render visuals/remotion/src/index.jsx five-implementations-overview docs/assets/five-implementation-overview.mp4 --codec=h264 --crf=21 --concurrency=1 --browser-executable="$GOOGLE_CHROME_BIN"
ffmpeg -y -i docs/assets/five-implementation-overview.mp4 -vf "fps=10,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" docs/assets/five-implementation-overview.gif
