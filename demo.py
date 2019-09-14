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
import asyncio
import logging
import os

from octobot_commons.enums import TimeFrames
from octobot_commons.logging.logging_util import get_logger

from octobot_backtesting.collectors.exchanges.exchange_live_collector import ExchangeLiveDataCollector
from octobot_backtesting.importers.exchanges.exchange_importer import ExchangeDataImporter


async def import_exchange_live_collector(config, file_path):
    importer = ExchangeDataImporter(config, file_path)
    importer.initialize()
    print(importer.get_ohlcv("binance"))


async def run_exchange_live_collector(config, exchange_name, symbols, time_frames):
    collector = ExchangeLiveDataCollector(config, exchange_name, symbols, time_frames)
    await collector.initialize()
    await collector.start()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    get_logger().info("starting...")

    main_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(main_loop)

    # main_loop.run_until_complete(run_exchange_live_collector({}, "binance", ["BTC/USDT"], [TimeFrames.ONE_MINUTE]))
    main_loop.run_until_complete(import_exchange_live_collector({}, os.getenv('BACKTESTING-FILE')))
