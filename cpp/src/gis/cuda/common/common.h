// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

#pragma once
#ifdef __CUDACC__
#define DEVICE_RUNNABLE __host__ __device__
#else
#define DEVICE_RUNNABLE
using std::min;
using std::max;
#endif

#include <cuda_runtime.h>
#include <cudart_platform.h>
#include <device_launch_parameters.h>

#include <cmath>

#include "gis/cuda/common/kernel_config.h"
