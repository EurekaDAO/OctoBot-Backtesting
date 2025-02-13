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
import async_channel.channels as channels
import async_channel.util as channel_util

import octobot_commons.logging as logging
import octobot_commons.channels_name as channels_name
import octobot_commons.tentacles_management as tentacles_management

import octobot_backtesting.util as backtesting_util
import octobot_backtesting.time as backtesting_time


class Backtesting:
    def __init__(self, config, exchange_ids, matrix_id, backtesting_files):
        self.config = config
        self.backtesting_files = backtesting_files
        self.logger = logging.get_logger(self.__class__.__name__)

        self.exchange_ids = exchange_ids
        self.matrix_id = matrix_id

        self.importers = []
        self.time_manager = None
        self.time_updater = None
        self.time_channel = None

    async def initialize(self):
        try:
            self.time_manager = backtesting_time.TimeManager(config=self.config)
            self.time_manager.initialize()

            self.time_channel = await channel_util.create_channel_instance(backtesting_time.TimeChannel,
                                                                           channels.set_chan,
                                                                           is_synchronized=True)

            self.time_updater = backtesting_time.TimeUpdater(
                channels.get_chan(channels_name.OctoBotBacktestingChannelsName.TIME_CHANNEL.value), self)
        except Exception as e:
            self.logger.exception(e, True, f"Error when initializing backtesting : {e}.")

    async def stop(self):
        await self.delete_time_channel()

    async def delete_time_channel(self):
        await self.time_channel.stop()
        for consumer in self.time_channel.consumers:
            await self.time_channel.remove_consumer(consumer)
        self.time_channel.flush()
        channels.del_chan(self.time_channel.get_name())

    async def start_time_updater(self):
        await self.time_updater.run()

    async def create_importers(self):
        try:
            self.importers = [await backtesting_util.create_importer_from_backtesting_file_name(
                self.config,
                backtesting_file,
                backtesting_util.get_default_importer()
            )
                              for backtesting_file in self.backtesting_files]
        except TypeError:
            pass

    async def handle_time_update(self, timestamp):
        if self.time_manager:
            self.time_manager.set_current_timestamp(timestamp)

    def get_importers(self, importer_parent_class=None) -> list:
        return [importer
                for importer in self.importers
                if tentacles_management.default_parents_inspection(importer.__class__, importer_parent_class)] \
            if importer_parent_class is not None else self.importers

    def get_progress(self):
        if self._has_nothing_to_do():
            return 0
        return 1 - (self.time_manager.get_remaining_iteration() / self.time_manager.get_total_iteration())

    def is_in_progress(self):
        if self._has_nothing_to_do():
            return False
        else:
            return self.time_manager.get_remaining_iteration() > 0

    def _has_nothing_to_do(self):
        return not self.time_manager or self.time_manager.get_total_iteration() == 0

    def has_finished(self):
        return self.time_updater and self.time_updater.finished_event.is_set()
