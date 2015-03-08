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

#include <stdio.h>

#include "rappor.h"

namespace rappor {

Encoder::Encoder(
    const std::string& metric_name, int cohort, const rappor::Params& params)
  : params_(params) {
}

bool Encoder::Encode(const std::string& value) {
  printf("encoding\n");
}

}  // namespace rappor
