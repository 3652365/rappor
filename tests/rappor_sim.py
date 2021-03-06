#!/usr/bin/python
#
# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tool to run RAPPOR on simulated client input.

It takes a 3-column CSV file as generated by gen_sim_data.py, and outputs 4
files:

  - out: 3 column CSV of RAPPOR'd data.
  - params: RAPPOR parameters, needed to recover distributions from the output
  - true inputs: Can be used to "cheat" and construct candidate strings
  - hist: histogram of actual input values.  Compare this with the histogram
    the RAPPOR analysis infers from the first 3 values.

Input columns: client,true_value
Ouput coumns: client,cohort,rappor

See http://google.github.io/rappor/doc/data-flow.html for details.
"""

import csv
import collections
import optparse
import os
import random
import sys
import time

import rappor  # client library
try:
  import fastrand
except ImportError:
  print >>sys.stderr, (
      "Native fastrand module not imported; see README for speedups")
  fastrand = None


def log(msg, *args):
  if args:
    msg = msg % args
  print >>sys.stderr, msg


def CreateOptionsParser():
  p = optparse.OptionParser()

  # We are taking a path, and not using stdin, because we read it twice.
  p.add_option(
      '-i', dest='infile', metavar='PATH', type='str', default='',
      help='CSV input path.  Header is "client,true_value"')
  p.add_option(
      '--out-prefix', dest='out_prefix', metavar='PATH', type='str',
      default='',
      help='Output prefix.')

  p.add_option(
      '--num-bits', type='int', metavar='INT', dest='num_bits', default=16,
      help='Number of bloom filter bits.')
  p.add_option(
      '--num-hashes', type='int', metavar='INT', dest='num_hashes', default=2,
      help='Number of hashes.')
  p.add_option(
      '--num-cohorts', type='int', metavar='INT', dest='num_cohorts',
      default=64, help='Number of cohorts.')

  p.add_option(
      '-p', type='float', metavar='FLOAT', dest='prob_p', default=1,
      help='Probability p')
  p.add_option(
      '-q', type='float', metavar='FLOAT', dest='prob_q', default=1,
      help='Probability q')
  p.add_option(
      '-f', type='float', metavar='FLOAT', dest='prob_f', default=1,
      help='Probability f')

  p.add_option(
      '--oneprr', dest='oneprr', action='store_true', default=False,
      help='Use a consistent PRR.')

  choices = ['simple', 'fast']
  p.add_option(
      '-r', type='choice', metavar='STR',
      dest='random_mode', default='fast', choices=choices,
      help='Random algorithm (%s)' % '|'.join(choices))

  return p


def make_histogram(csv_in):
  """Make a histogram of the simulated input file."""
  # TODO: It would be better to share parsing with rappor_encode()
  counter = collections.Counter()
  for (_, word) in csv_in:
    counter[word] += 1
  return dict(counter.most_common())


def print_histogram(word_hist, histfile):
  """Write histogram of values to histfile."""
  # Print histograms of distributions
  sorted_words = sorted(word_hist.iteritems(), key=lambda pair: pair[1],
                        reverse=True)
  fmt = "%s,%s"
  print >>histfile, fmt % ("string", "count")
  for pair in sorted_words:
    print >>histfile, fmt % pair


def bit_string(irr, num_bloombits):
  """Like bin(), but uses leading zeroes, and no '0b'."""
  s = ''
  bits = []
  for bit_num in xrange(num_bloombits):
    if irr & (1 << bit_num):
      bits.append('1')
    else:
      bits.append('0')
  return ''.join(reversed(bits))


def main(argv):
  (opts, argv) = CreateOptionsParser().parse_args(argv)
  if not opts.infile:
    raise RuntimeError('-i is required')
  if not opts.out_prefix:
    raise RuntimeError('--out-prefix is required')

  # Copy flags into params
  params = rappor.Params()
  params.num_bloombits = opts.num_bits
  params.num_hashes = opts.num_hashes
  params.num_cohorts = opts.num_cohorts
  params.prob_p = opts.prob_p
  params.prob_q = opts.prob_q
  params.prob_f = opts.prob_f
  params.flag_oneprr = opts.oneprr

  prefix = opts.out_prefix

  outfile = prefix + "_out.csv"
  histfile = prefix + "_hist.csv"

  with open(opts.infile) as f:
    csv_in = csv.reader(f)
    word_hist = make_histogram(csv_in)

  # Print true histograms.
  with open(histfile, 'w') as f:
    print_histogram(word_hist, f)

  all_words = sorted(word_hist)  # unique words

  rand = random.Random()  # default Mersenne Twister randomness
  #rand = random.SystemRandom()  # cryptographic randomness from OS

  rand.seed()  # Default: seed with sys time

  if opts.random_mode == 'simple':
    rand_funcs = rappor.SimpleRandFuncs(params, rand)
  elif opts.random_mode == 'fast':
    if fastrand:
      log('Using fastrand extension')
      # NOTE: This doesn't take 'rand'
      rand_funcs = fastrand.FastRandFuncs(params)
    else:
      log('Warning: fastrand module not importable; see README for build '
          'instructions.  Falling back to simple randomness.')
      rand_funcs = rappor.SimpleRandFuncs(params, rand)
  else:
    raise AssertionError

  # Do RAPPOR transformation.
  with open(opts.infile) as f_in, open(outfile, 'w') as f_out:
    csv_in = csv.reader(f_in)
    csv_out = csv.writer(f_out)

    header = ('client', 'cohort', 'rappor')
    csv_out.writerow(header)

    cur_client = None  # current client

    start_time = time.time()

    for i, (client, true_value) in enumerate(csv_in):
      if i % 10000 == 0:
        elapsed = time.time() - start_time
        log('Processed %d inputs in %.2f seconds', i, elapsed)

      # New encoder instance for each client.
      if client != cur_client:
        cur_client = client
        e = rappor.Encoder(params, cur_client, rand_funcs=rand_funcs)

      cohort, irr = e.encode(true_value)

      # encoded is a list of (cohort, rappor) pairs
      out_row = (client, cohort, bit_string(irr, params.num_bloombits))
      csv_out.writerow(out_row)


if __name__ == "__main__":
  try:
    main(sys.argv)
  except RuntimeError, e:
    log('rappor_sim.py: FATAL: %s', e)
