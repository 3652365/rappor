#!/bin/bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

setup() {
  # need libprotobuf-dev for headers to compile against.
  sudo apt-get install protobuf-compiler libprotobuf-dev
}

rappor-test() {
  make _tmp/rappor_test
  _tmp/rappor_test "$@"
}

rappor-encode() {
  seq 10 | rappor-test 5 
}

empty-input() {
  echo -n '' | rappor-test 5 
}

hmac-drbg-test() {
  make _tmp/hmac_drbg_test
  _tmp/hmac_drbg_test
}

hmac-openssl-test() {
  make _tmp/hmac_openssl_test
  _tmp/hmac_openssl_test
}

get() {
  wget --no-clobber --directory _tmp "$@"
}

download() {
  get https://chromium.googlesource.com/chromium/src/+archive/master/components/rappor.tar.gz
  get https://chromium.googlesource.com/chromium/src/+archive/master/crypto.tar.gz
}

extract() {
  mkdir -p _tmp/chrome _tmp/crypto

  pushd _tmp/chrome
  tar xvf ../rappor.tar.gz
  popd

  pushd _tmp/crypto
  tar xvf ../crypto.tar.gz
  popd
}

copy() {
  #cp -v _tmp/chrome/byte_vector_utils* .
  #cp -v _tmp/crypto/{hmac.h,hmac_openssl.cc} .
  cp -v _tmp/crypto/hmac.cc .
}

count() {
  wc -l hmac* byte_vector_utils*
}

test-hmac-sha256() {
  #echo -n foo | sha256sum
  python -c '
import hashlib
import hmac
import sys

secret = sys.argv[1]
body = sys.argv[2]
m = hmac.new(secret, body, digestmod=hashlib.sha256)
print m.hexdigest()
' "key" "value"
}

test-md5() {
  echo -n value | md5sum
}

"$@"
