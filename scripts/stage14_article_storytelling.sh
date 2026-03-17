#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

uv run python -m unittest discover -s tests -v
python3 -m compileall src tests
uv run llm-computer-article-story

export PATH="/Users/lijie/.nvm/versions/node/v24.10.0/bin:$PATH"
export GOOGLE_CHROME_BIN="${GOOGLE_CHROME_BIN:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

npm install --prefix visuals/remotion

render_still() {
  local composition_id="$1"
  local output_path="$2"
  npx --prefix visuals/remotion remotion still visuals/remotion/src/index.jsx "$composition_id" "$output_path" --concurrency=1 --browser-executable="$GOOGLE_CHROME_BIN"
}

npx --prefix visuals/remotion remotion still visuals/remotion/src/index.jsx five-implementations-poster docs/assets/five-implementation-overview.png --concurrency=1 --browser-executable="$GOOGLE_CHROME_BIN"
render_still five-implementation-ladder-figure docs/assets/five-implementation-ladder.png
render_still five-implementation-paths-figure docs/assets/five-implementation-paths.png
render_still five-implementation-latency-figure docs/assets/five-implementation-latency.png
render_still article-example-results-figure docs/assets/article-example-results.png
render_still sudoku-prefix-validation-figure docs/assets/sudoku-prefix-validation.png
render_still five-implementation-validation-matrix-figure docs/assets/five-implementation-validation-matrix.png
npx --prefix visuals/remotion remotion render visuals/remotion/src/index.jsx five-implementations-overview docs/assets/five-implementation-overview.mp4 --codec=h264 --crf=21 --concurrency=1 --browser-executable="$GOOGLE_CHROME_BIN"
ffmpeg -y -i docs/assets/five-implementation-overview.mp4 -vf "fps=10,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" docs/assets/five-implementation-overview.gif
