

#  Copyright (c) 2025 Keylog Solutions LLC
#
#  ATTRIBUTION NOTICE: This work was conceived and created by Jonathan A. Handler. Large language model(s) and/or many other resources were used to help create this work.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import time

class timer:

    def __init__(self, do_start=True):
        self.start_secs = None
        self.laps = None
        self.total_time_so_far = None
        self.lap_count = None
        self.last_lap_secs = None
        self.is_started = False

        if do_start:
            self.start_or_restart(True)

    def start_or_restart(self, do_reset):
        start = start_time = time.gmtime()
        self.start_secs = time.mktime(start_time)
        if do_reset:
            self.laps = []
            self.total_time_so_far = 0
            self.lap_count = 0
        self.last_lap_secs = self.start_secs
        self.is_started = True

    def lap(self, print_to_stdout=True):
        if not self.is_started:
            print("Cannot log a lap, because timer is stopped.")
            return
        #### Determine and report time required to run the query
        lap_time = time.gmtime()
        lap_secs = time.mktime(lap_time)
        lap_interval_secs = lap_secs - self.last_lap_secs
        self.laps.append(lap_interval_secs)
        self.last_lap_secs = lap_secs

        #### Track overall progress
        self.lap_count += 1
        self.total_time_so_far += lap_interval_secs

        #### Report prn
        if print_to_stdout:
            print(f"Lap {self.lap_count} time in secs: {lap_interval_secs}, total time: {self.total_time_so_far}")

    def stop(self, print_to_stdout=True):
        #### Determine and report time required to run the query
        self.lap(print_to_stdout)
        if print_to_stdout:
            counter = 0
            sum = 0
            lap_count = len(self.laps)
            for lap in self.laps:
                counter += 1
                sum += lap
                print(f"Lap {counter} of {lap_count}: {lap} seconds, total time: {sum} seconds")

