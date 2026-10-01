#!/usr/bin/env bash
# Download the prebuilt Redis ADBC driver from its GitHub release into
# ./driver/, after checking the release's SHA-256.
#
# Releases have builds for macOS arm64, Linux x86-64 and Linux arm64. When
# there's none for this platform or version (another OS, or DRIVER_VERSION set
# to a commit), this builds the driver from source instead
# (scripts/build_driver.sh, which needs Go 1.26+ and a C toolchain).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DRIVER_RELEASES="${DRIVER_RELEASES:-https://github.com/alberttwong/redis-adbc-driver/releases/download}"
DRIVER_VERSION="${DRIVER_VERSION:-$(cat "${ROOT}/scripts/driver-version")}"

build_instead() {
  echo "$1; building it from source instead." >&2
  exec "${ROOT}/scripts/build_driver.sh"
}

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) PLATFORM=darwin-arm64 EXT=dylib ;;
  Linux-x86_64 | Linux-amd64) PLATFORM=linux-amd64 EXT=so ;;
  Linux-aarch64 | Linux-arm64) PLATFORM=linux-arm64 EXT=so ;;
  *) build_instead "No prebuilt driver for $(uname -s) $(uname -m)" ;;
esac

NAME="adbc_driver_redis-${DRIVER_VERSION}-${PLATFORM}"
URL="${DRIVER_RELEASES}/${DRIVER_VERSION}/${NAME}.tar.gz"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

# A 404 means the release (or this platform's build) doesn't exist: build
# instead. Any other failure stops here.
status="$(curl -sSL -o "${TMP}/${NAME}.tar.gz" -w '%{http_code}' "${URL}")"
case "${status}" in
  200) ;;
  404) build_instead "No prebuilt driver ${NAME} (is ${DRIVER_VERSION} a release?)" ;;
  *) echo "Downloading ${URL} failed: HTTP ${status}" >&2; exit 1 ;;
esac
curl -fsSL -o "${TMP}/${NAME}.tar.gz.sha256" "${URL}.sha256"

if command -v sha256sum >/dev/null; then
  (cd "${TMP}" && sha256sum --check --quiet "${NAME}.tar.gz.sha256")
else
  (cd "${TMP}" && shasum -a 256 --check --quiet "${NAME}.tar.gz.sha256")
fi

tar -xzf "${TMP}/${NAME}.tar.gz" -C "${TMP}"
mkdir -p "${ROOT}/driver"
cp "${TMP}/${NAME}/libadbc_driver_redis.${EXT}" "${ROOT}/driver/"
echo "Downloaded ${ROOT}/driver/libadbc_driver_redis.${EXT} (${DRIVER_VERSION}, ${PLATFORM})"
