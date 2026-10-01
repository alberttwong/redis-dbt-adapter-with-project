#!/usr/bin/env bash
# Build the Redis ADBC driver and copy it to ./driver/.
# Requires Go 1.26+ and a C toolchain (cgo).
set -euo pipefail

DRIVER_REPO="${DRIVER_REPO:-https://github.com/alberttwong/redis-adbc-driver.git}"
DRIVER_VERSION="${DRIVER_VERSION:-v0.0.6}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/build/redis-adbc-driver"

case "$(uname -s)" in
  Darwin) EXT=dylib ;;
  MINGW* | MSYS* | CYGWIN*) EXT=dll ;;
  *) EXT=so ;;
esac

if [ -d "${SRC}/.git" ]; then
  git -C "${SRC}" fetch --tags --quiet origin
else
  git clone --quiet "${DRIVER_REPO}" "${SRC}"
fi
git -C "${SRC}" checkout --quiet "${DRIVER_VERSION}"

make -C "${SRC}/go" build VERSION="${DRIVER_VERSION}"

mkdir -p "${ROOT}/driver"
cp "${SRC}/go/build/libadbc_driver_redis.${EXT}" "${ROOT}/driver/"
echo "Built ${ROOT}/driver/libadbc_driver_redis.${EXT} (${DRIVER_VERSION})"
