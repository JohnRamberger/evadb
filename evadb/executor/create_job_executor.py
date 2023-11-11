# coding=utf-8
# Copyright 2018-2023 EvaDB
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
import pandas as pd
import re

from datetime import datetime

from evadb.database import EvaDBDatabase
from evadb.executor.abstract_executor import AbstractExecutor
from evadb.executor.executor_utils import ExecutorError
from evadb.models.storage.batch import Batch
from evadb.parser.create_statement import CreateJobStatement
from evadb.third_party.databases.interface import get_database_handler
from evadb.utils.logging_manager import logger


class CreateJobExecutor(AbstractExecutor):
    def __init__(self, db: EvaDBDatabase, node: CreateJobStatement):
        super().__init__(db, node)

    def _parse_datetime_str(self, datetime_str: str) -> datetime:
        datetime_format = "%Y-%m-%d %H:%M:%S"
        date_format = "%Y-%m-%d"
        
        if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', datetime_str):
            try:
                return datetime.strptime(datetime_str, datetime_format)
            except ValueError:
                raise ExecutorError(
                    f"{datetime_str} is not in the correct datetime format. expected format: {datetime_format}."
                )
        elif re.match(r'\d{4}-\d{2}-\d{2}', datetime_str):
            try:
                return datetime.strptime(datetime_str, date_format)
            except ValueError:
                raise ExecutorError(
                    f"{datetime_str} is not in the correct date format. expected format: {date_format}."
                )
        else:
            raise ValueError(f"{datetime_str} does not match the expected date or datetime format")


    def exec(self, *args, **kwargs):
        # Check if the job already exists.
        job_catalog_entry = self.catalog().get_job_catalog_entry(
            self.node.job_name
        )

        if job_catalog_entry is not None:
            if self.node.if_not_exists:
                msg = f"A job with name {self.node.job_name} already exists, nothing added."
                yield Batch(pd.DataFrame([msg]))
                return
            else:
                raise ExecutorError(f"A job with name {self.node.job_name} already exists.")

        logger.debug(f"Creating job {self.node}")
        
        job_name = self.node.job_name
        queries = [str(q) for q in self.node.queries]
        start_time = self._parse_datetime_str(self.node.start_time) if self.node.start_time is not None else datetime.datetime.now()
        end_time = self._parse_datetime_str(self.node.end_time) if self.node.end_time is not None else None
        repeat_interval = self.node.repeat_interval
        repeat_period = self.node.repeat_period
        active = True
        next_schedule_run = start_time

        self.catalog().insert_job_catalog_entry(
            job_name,
            queries,
            start_time,
            end_time,
            repeat_interval,
            repeat_period,
            active,
            next_schedule_run
        )

        yield Batch(
            pd.DataFrame(
                [
                    f"The job {self.node.job_name} has been successfully created."
                ]
            )
        )
