#  Drakkar-Software OctoBot
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
import pytest
import os
import asyncio
import sqlite3
import contextlib


import octobot_commons.asyncio_tools as asyncio_tools
import octobot_backtesting.errors as errors
import octobot_backtesting.data as backtesting_data
import octobot_backtesting.enums as enums

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

DATA_FILE1 = "ExchangeHistoryDataCollector_1589740606.4862757.data"
DATA_FILE2 = "second_ExchangeHistoryDataCollector_1589740606.4862757.data"


# use context manager instead of fixture to prevent pytest threads issues
@contextlib.asynccontextmanager
async def get_database(data_file=DATA_FILE1):
    async with backtesting_data.new_database(os.path.join("tests", "static", data_file)) as db:
        yield db
    # prevent "generator didn't stop after athrow(), see https://github.com/python-trio/trio/issues/2081"
    await asyncio_tools.wait_asyncio_next_cycle()


# use context manager instead of fixture to prevent pytest threads issues
@contextlib.asynccontextmanager
async def get_temp_empty_database():
    database_name = "temp_empty_database"
    try:
        async with backtesting_data.new_database(database_name) as db:
            yield db
    finally:
        # prevent "generator didn't stop after athrow(), see https://github.com/python-trio/trio/issues/2081"
        await asyncio_tools.wait_asyncio_next_cycle()
        os.remove(database_name)


async def test_invalid_file():
    file_name = "plop"
    db = backtesting_data.DataBase(file_name)
    try:
        await db.initialize()
        assert not await db.check_table_exists(enums.ExchangeDataTables.KLINE)
        with pytest.raises(sqlite3.OperationalError):
            await db.check_table_not_empty(enums.ExchangeDataTables.KLINE)
    finally:
        await db.stop()
        os.remove(file_name)


async def test_select():
    async with get_database() as database:
        # default values
        with pytest.raises(errors.DataBaseNotExists):
            await database.select(enums.ExchangeDataTables.KLINE)

        ohlcv = await database.select(enums.ExchangeDataTables.OHLCV)
        assert len(ohlcv) == 6531

        ohlcv = await database.select(enums.ExchangeDataTables.OHLCV, time_frame="1h")
        assert len(ohlcv) == 500

        ohlcv = await database.select(enums.ExchangeDataTables.OHLCV, symbol="xyz")
        assert len(ohlcv) == 0

        ohlcv = await database.select(enums.ExchangeDataTables.OHLCV, symbol="ETH/BTC")
        assert len(ohlcv) == 6531

        changed_order_ohlcv = await database.select(enums.ExchangeDataTables.OHLCV, order_by="time_frame", symbol="ETH/BTC")
        assert changed_order_ohlcv[0] != ohlcv[0]

        ohlcv = await database.select(enums.ExchangeDataTables.OHLCV, xyz="xyz")
        assert len(ohlcv) == 0


async def test_select_max():
    async with get_database() as database:
        assert await database.select_max(enums.ExchangeDataTables.OHLCV, ["timestamp"]) == [(1590883200,)]
        assert await database.select_max(enums.ExchangeDataTables.OHLCV, ["timestamp"], time_frame="1h") == [(1589742000,)]
        assert await database.select_max(enums.ExchangeDataTables.OHLCV, ["timestamp"], ["symbol"], time_frame="1h") == \
            [(1589742000, "ETH/BTC")]


async def test_select_min():
    async with get_database() as database:
        assert await database.select_min(enums.ExchangeDataTables.OHLCV, ["timestamp"]) == [(1500249600,)]
        assert await database.select_min(enums.ExchangeDataTables.OHLCV, ["timestamp"], time_frame="1h") == [(1587945600,)]
        assert await database.select_min(enums.ExchangeDataTables.OHLCV, ["timestamp"], ["symbol"], time_frame="1h") == \
            [(1587945600, "ETH/BTC")]


async def test_select_count():
    async with get_database() as database:
        assert await database.select_count(enums.ExchangeDataTables.OHLCV, ["*"]) == [(6531,)]
        assert await database.select_count(enums.ExchangeDataTables.OHLCV, ["*"], time_frame="1h") == [(500,)]
        assert await database.select_count(enums.ExchangeDataTables.OHLCV, ["*"], time_frame="1M") == [(35,)]


async def test_select_from_timestamp():
    async with get_database() as database:
        operations = [enums.DataBaseOperations.INF_EQUALS.value]
        candles = await database.select_from_timestamp(enums.ExchangeDataTables.OHLCV, ["1587960000"], operations)
        assert len(candles) > 0
        assert all(candle[0] <= 1587960000 for candle in candles)

        operations = [enums.DataBaseOperations.INF_EQUALS.value, enums.DataBaseOperations.SUP_EQUALS.value]
        candles = await database.select_from_timestamp(enums.ExchangeDataTables.OHLCV,
                                                       ["1587960000", "1587960000"],
                                                       operations)
        assert len(candles) > 0
        assert all(candle[0] == 1587960000 for candle in candles)

        operations = [enums.DataBaseOperations.INF_EQUALS.value, enums.DataBaseOperations.SUP_EQUALS.value]
        candles = await database.select_from_timestamp(enums.ExchangeDataTables.OHLCV,
                                                       ["1587960000", "1587945600"],
                                                       operations)
        assert len(candles) == 15
        assert all(1587945600 <= candle[0] <= 1587960000 for candle in candles)

        operations = [enums.DataBaseOperations.INF_EQUALS.value, enums.DataBaseOperations.SUP_EQUALS.value]
        candles = await database.select_from_timestamp(enums.ExchangeDataTables.OHLCV,
                                                       ["1587960000", "1587945600"],
                                                       operations,
                                                       symbol="xyz")
        assert len(candles) == 0


async def test_gather_concurrent_select():
    async with get_database() as database:
        timestamps_1h = [ohlcv[0] for ohlcv in await database.select(enums.ExchangeDataTables.OHLCV, time_frame="1h")]
        timestamps_4h = [ohlcv[0] for ohlcv in await database.select(enums.ExchangeDataTables.OHLCV, time_frame="4h")]
        coros = [_check_select_result(database, ts, "1h") for ts in timestamps_1h]
        coros += [_check_select_result(database, ts, "4h") for ts in timestamps_4h]
        await asyncio.gather(*coros)


async def test_create_tasks_concurrent_selects():
    async with get_database() as database:
        timestamps_1h = [ohlcv[0] for ohlcv in await database.select(enums.ExchangeDataTables.OHLCV, time_frame="1h")]
        timestamps_1m = [ohlcv[0] for ohlcv in await database.select(enums.ExchangeDataTables.OHLCV, time_frame="1m")]
        timestamps_4h = [ohlcv[0] for ohlcv in await database.select(enums.ExchangeDataTables.OHLCV, time_frame="4h",
                                                                     size=50)]

        calls_count = len(timestamps_1h) + len(timestamps_4h) + len(timestamps_1m)
        failed_calls = []
        success_calls = []

        async def select_task(db, timestamp, time_frame):
            try:
                await _check_select_result(db, timestamp, time_frame)
                success_calls.append((timestamp, time_frame))
            except Exception as e:
                failed_calls.append((timestamp, time_frame, e))

        tasks = []
        for ts in timestamps_1h:
            tasks.append(asyncio.get_event_loop().create_task(select_task(database, ts, "1h")))
        for ts in timestamps_4h:
            tasks.append(asyncio.get_event_loop().create_task(select_task(database, ts, "4h")))
        for ts in timestamps_1m:
            tasks.append(asyncio.get_event_loop().create_task(select_task(database, ts, "1m")))
            # for wait for next cycle to make previous requests end and re-use previous cursors
            await asyncio_tools.wait_asyncio_next_cycle()

        await asyncio.gather(*tasks)
        assert len(success_calls) == calls_count
        assert failed_calls == []


async def test_stop_while_concurrent_select():
    async with get_database() as database:
        timestamps = [ohlcv[0] for ohlcv in await database.select(enums.ExchangeDataTables.OHLCV, time_frame="1h")]
        await _check_select_result(database, timestamps[0])
        asyncio.create_task(asyncio.wait(
            asyncio.gather(*[_check_select_result(database, ts, expected_exception=sqlite3.ProgrammingError)
                             for ts in timestamps])))
        # not enough time to finish all requests, most if not all will remaining pending
        await asyncio_tools.wait_asyncio_next_cycle()


async def test_double_database():
    async with get_database() as database1, get_database(DATA_FILE2) as database2:
        timestamps1 = [ohlcv[0] for ohlcv in await database1.select(enums.ExchangeDataTables.OHLCV, time_frame="1h")]
        timestamps2 = [ohlcv[0] for ohlcv in await database2.select(enums.ExchangeDataTables.OHLCV, time_frame="1h")]
        await asyncio.gather(*[_check_select_result(database1, ts) for ts in timestamps1])
        await asyncio.gather(*[_check_select_result(database2, ts) for ts in timestamps2])


async def test_double_database_stop_while_concurrent_select():
    async with get_database() as database1, get_database(DATA_FILE2) as database2:
        timestamps1 = [ohlcv[0] for ohlcv in await database1.select(enums.ExchangeDataTables.OHLCV, time_frame="1h")]
        timestamps2 = [ohlcv[0] for ohlcv in await database2.select(enums.ExchangeDataTables.OHLCV, time_frame="1h")]
        await _check_select_result(database1, timestamps1[0])
        await _check_select_result(database2, timestamps2[0])
        asyncio.create_task(asyncio.wait(
            asyncio.gather(*[_check_select_result(database1, ts, expected_exception=sqlite3.ProgrammingError)
                             for ts in timestamps1])))
        asyncio.create_task(asyncio.wait(
            asyncio.gather(*[_check_select_result(database2, ts, expected_exception=sqlite3.ProgrammingError)
                             for ts in timestamps2])))
        # not enough time to finish all requests, most if not all will remaining pending
        await asyncio_tools.wait_asyncio_next_cycle()


async def test_insert():
    async with get_temp_empty_database() as temp_empty_database:
        await temp_empty_database.insert(enums.ExchangeDataTables.OHLCV, symbol="xyz", timestamp=1, price=1, date="01")
        assert await temp_empty_database.select(enums.ExchangeDataTables.OHLCV) == [(1, 'xyz', '1', '01')]


async def test_insert_all():
    async with get_temp_empty_database() as temp_empty_database:
        await temp_empty_database.insert_all(enums.ExchangeDataTables.OHLCV,
                                             symbol=["xyz", "abc"],
                                             timestamp=[1, 2],
                                             price=[1, 10],
                                             date=["01", "05"])
        assert await temp_empty_database.select(enums.ExchangeDataTables.OHLCV) == [(2, 'abc', '10', '05'), (1, 'xyz', '1', '01')]
        assert await temp_empty_database.select(enums.ExchangeDataTables.OHLCV, date="05") == [(2, 'abc', '10', '05')]


async def test_create_index():
    async with get_temp_empty_database() as temp_empty_database:
        await temp_empty_database.insert(enums.ExchangeDataTables.OHLCV, 1, symbol="xyz", price="1", date="01")
        # ensure no exception
        await temp_empty_database.create_index(enums.ExchangeDataTables.OHLCV, ["symbol", "timestamp"])
        assert await temp_empty_database.select(enums.ExchangeDataTables.OHLCV) == [(1, 'xyz', '1', '01')]


async def _check_select_result(database, timestamp, time_frame="1h", expected_exception=None):
    try:
        ohlcv = await database.select(enums.ExchangeDataTables.OHLCV, time_frame=time_frame, timestamp=str(timestamp))
        assert len(ohlcv) == 1
        assert ohlcv[0][0] == timestamp
    except Exception as e:
        if e.__class__ is expected_exception:
            pass
        else:
            raise
