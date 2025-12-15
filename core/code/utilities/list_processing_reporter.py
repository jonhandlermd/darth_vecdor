

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

from app_source.public_repo.core.code.utilities.timer import timer as tim
import app_source.public_repo.core.code.utilities.debug as debug

d = debug.default_d

def eta_rounded(eta_secs:float) -> str:
    """
    This takes a number of seconds and returns a rounded string representing that time in seconds, minutes, hours, or days.
    :param eta_secs:
    :return:
    """
    if eta_secs < 60.0:
        eta = f"{round(eta_secs, 1)} secs"
    elif eta_secs < 60.0 * 60.0:
        eta = f"{round(eta_secs / 60.0, 1)} mins"
    elif eta_secs < 60.0 * 60.0 * 24.0:
        eta = f"{round(eta_secs / (60.0 * 60.0), 1)} hours"
    else:
        eta = f"{round(eta_secs / (60.0 * 60.0 * 24.0), 1)} days"
    return eta


class list_processing_reporter_class:

    def __init__(self, name:str, list_length:int, report_increment:int=1000, show_progress:bool=False, status_report_functions=None, show_laps:bool=d):
        """
        This object will report progress through a list at intervals whenever the report_progress function is called.
        :param list_length: How many total items are being procssed
        :param report_increment: How often (every "report_increment" count of items) should progress be reported, default is 1000.
        :param show_progress: Show the progress in stdout, or do nothing, default is False (progress will not be shown).
        """

        if status_report_functions is None:
            status_report_functions = [print]
        self.report_increment = report_increment
        self.show_progress = show_progress
        self.list_length = list_length
        self.timer = tim()
        self.timer.start_or_restart(True)
        self.name = name
        self.status_report_functions = status_report_functions
        self.current_report = self.timer.total_time_so_far
        self.last_report = self.current_report
        self.show_laps = show_laps
        self.skip_count = 0
        self.last_skip_count = 0


    def report_progress(self, counter:int) -> None:
        """
        This shows in stdout the progress through the list so far, including how many have been processed out of total, time passed so far, and time since last report.
        :param counter: what number item is this in list being processed
        :return: None
        """


        if not self.show_progress:
            return

        if counter % self.report_increment != 0:
            return

        # calculate time to completion
        if counter > 0:
            num_remaining = self.list_length - counter
            self.current_report = self.timer.total_time_so_far
            secs_since_last_report = self.current_report - self.last_report
            skips_since_last_report = self.skip_count - self.last_skip_count
            self.last_skip_count = self.skip_count
            self.last_report = self.current_report

            num_done_since_last_report = self.report_increment - skips_since_last_report
            if num_done_since_last_report > 0:
                time_per_item = (1.0000 * secs_since_last_report) / (1.0000 * num_done_since_last_report)
                eta_secs = time_per_item * (num_remaining * 1.0000)
            else:
                eta_secs = 0.0

            num_done_since_start = counter - self.skip_count
            if num_done_since_start > 0:
                time_per_item_since_start = (1.0000 * self.current_report) / (1.0000 * num_done_since_start)
                eta_secs_based_on_start = time_per_item_since_start * (num_remaining * 1.0000)
            else:
                eta_secs_based_on_start = 0.0

            # time_per_item = (1.0000 * self.timer.total_time_so_far)/(1.0000 * counter)
            # total_expected_time = time_per_item * (1.0000 * self.list_length)
            # eta_secs = total_expected_time - self.timer.total_time_so_far
            eta = f"{eta_rounded(eta_secs)} (based on recent), {eta_rounded(eta_secs_based_on_start)} (based on start)"
        else:
            eta = "ETA: Unsure yet"

        msg = f'''
-----
LIST NAME: {self.name}
Processed: {counter} of {self.list_length}
Estimated Time Remaining: {eta}
Skipped: {self.skip_count} items so far.
-----
            '''
        for fxn in self.status_report_functions:
            fxn(msg)

        self.timer.lap(self.show_laps)
        return

    def report_completion(self) -> None:
        """
        If the object is set to show progress, this will show a report saying the list is completed, and the total time to complete processing the list.
        :return: None
        """
        if self.show_progress:
            msg = "Completed processing of list."
            for fxn in self.status_report_functions:
                fxn(msg)

            self.timer.stop(self.show_progress)
        return








