#!/usr/bin/env bash
# Capture the GUI as docs/screenshots/main_window.webp; pass GUI arguments through.
set -eo pipefail

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
	echo "Usage: bash devel/open_and_take_screenshot.sh [GUI arguments]"
	echo "Example: bash devel/open_and_take_screenshot.sh --directory /path/to/movies"
	echo "Requires macOS Screen Recording access, easy-screenshot, ImageMagick, and cwebp."
	exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
for tool in magick cwebp; do
	command -v "$tool" >/dev/null || { echo "Missing capture tool: $tool" >&2; exit 1; }
done
if command -v screenshot >/dev/null; then
	capture=(screenshot)
else
	capture=("$HOME/nsh/easy-screenshot/run.sh")
	[[ -x "${capture[0]}" ]] || { echo "Install easy-screenshot first." >&2; exit 1; }
fi

capture_dir="$(mktemp -d /tmp/movie_screenshot.XXXXXX)"
app_pid=""
cleanup() {
	if [[ -n "$app_pid" ]]; then
		kill "$app_pid" 2>/dev/null || true
		wait "$app_pid" 2>/dev/null || true
	fi
	rm -rf "$capture_dir"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

(
	source ./source_me.sh
	exec python3 movie_organizer_gui.py "$@"
) >"$capture_dir/app.log" 2>&1 &
app_pid=$!

for attempt in {1..30}; do
	if ! kill -0 "$app_pid" 2>/dev/null; then
		cat "$capture_dir/app.log" >&2
		exit 1
	fi
	if "${capture[@]}" -A Python -t "Movie Media Manager" \
		-f "$capture_dir/main_window.png" >"$capture_dir/capture.log" 2>&1; then
		break
	fi
	sleep 1
done
if [[ ! -s "$capture_dir/main_window.png" ]]; then
	cat "$capture_dir/capture.log" >&2
	echo "No Movie Media Manager window captured within 30 attempts." >&2
	exit 1
fi

# Resize only the launched app; Accessibility permission may be unavailable.
if ! osascript \
	-e 'with timeout of 5 seconds' \
	-e "tell application \"System Events\" to tell (first process whose unix id is $app_pid) to set size of front window to {1440, 900}" \
	-e 'end timeout' >"$capture_dir/resize.log" 2>&1; then
	echo "Window sizing unavailable; preserving the app's current dimensions." >&2
fi
sleep 1
"${capture[@]}" -A Python -t "Movie Media Manager" -f "$capture_dir/main_window.png"

magick "$capture_dir/main_window.png" -resize '1920x1920>' "$capture_dir/main_window.png"
cwebp -quiet -q 90 "$capture_dir/main_window.png" -o "$capture_dir/main_window.webp"
mkdir -p docs/screenshots
cp "$capture_dir/main_window.webp" docs/screenshots/main_window.webp
echo "Captured $(date -u '+%Y-%m-%dT%H:%M:%SZ'): docs/screenshots/main_window.webp"
