#  Drakkar-Software OctoBot-Backtesting
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import os

from octobot_commons.tentacles_management import get_deep_class_from_string

from octobot_backtesting import BACKTESTING_DATA_FILE_SEPARATOR, collectors
from octobot_backtesting.importers import DataImporter


async def create_importer_from_backtesting_file_name(config, backtesting_file) -> DataImporter:
    collector_klass = get_deep_class_from_string(parse_class_name_from_backtesting_file(backtesting_file), collectors)
    importer = collector_klass.IMPORTER(config, backtesting_file) if collector_klass else None
    await importer.initialize()
    return importer


def parse_class_name_from_backtesting_file(backtesting_file):
    return os.path.basename(backtesting_file).split(BACKTESTING_DATA_FILE_SEPARATOR)[0]
