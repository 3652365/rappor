// Copyright 2014 Google Inc. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <iostream>
#include <stdio.h>

#include "rappor.pb.h"
#include "rappor.h"
#include "libc_rand.h"
#include "openssl_impl.h"

// TODO: Params as flags?

int main(int argc, char** argv) {
  if (argc != 2) {
    rappor::log("Usage: rappor_encode <cohort>");
    exit(1);
  }
  int cohort = atoi(argv[1]);
  if (cohort == 0) {
    rappor::log("Cohort must be an integer greater than 0.");
    exit(1);
  }

  rappor::ReportList reports;

  rappor::Params params;
  params.set_num_bits(16);
  params.set_num_hashes(2);

  rappor::LibcRandGlobalInit();  // seed
  rappor::LibcRand libc_rand(params.num_bits(), 0.50 /*p*/, 0.75 /*q*/);

  const char* client_secret = "secret";

  const char* metric_name = "home-page";
  rappor::Encoder encoder(
      metric_name, cohort, params,
      0.50 /* prob_f */, rappor::Md5, rappor::Hmac, client_secret, 
      libc_rand);

  assert(encoder.IsValid());  // bad instantiation

  // maybe have rappor_encode and rappor_demo
  // demo shows how to encode multiple metrics

  std::string line;
  while (true) {
    std::getline(std::cin, line);  // no trailing newline
    if (line.empty()) {
      break;
    }
    std::cout << "!" << line << std::endl;

    std::string out;
    bool ok = encoder.Encode(line, &out);

    // NOTE: Are there really encoding errors?
    if (!ok) {
      rappor::log("Error encoding string %s", line.c_str());
      break;
    }
    reports.add_report(out);
  }

  rappor::ReportListHeader* header = reports.mutable_header();
  // client params?
  header->set_metric_name(metric_name);
  header->set_cohort(cohort);
  header->mutable_params()->CopyFrom(params);

  rappor::log("report list %s", reports.DebugString().c_str());
}
