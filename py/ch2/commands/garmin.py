
from logging import getLogger
from time import sleep

from requests import HTTPError

from .args import DIR, DATE, FORCE, base_system_path, PERMANENT, DATA_DIR
from ..common.names import USER, PASSWD
from .. import BASE
from ..common.args import mm
from ..fit.download.connect import GarminConnect
from ..lib import now, local_time_to_time, time_to_local_time
from ..common.log import log_current_exception
from ..common.io import clean_path
from ..lib.workers import ProgressTree
from ..sql import Constant, SystemConstant
from ..pipeline.read.monitor import missing_dates

log = getLogger(__name__)

GARMIN_USER = 'garmin_user'
GARMIN_PASSWORD = 'garmin_password'


def garmin(config):
    '''
## garmin

    > ch2 garmin --user USER --pass PASSWORD DIR

Download recent monitor data to the given directory.

    > ch2 garmin --user USER --pass PASSWORD --date DATE DIR

Download monitor data for the given date.

Note that this cannot be used to download more than 10 days of data.
For bulk downloads use
https://www.garmin.com/en-US/account/datamanagement/
    '''
    args = config.args
    dates = [args[DATE]] if args[DATE] else []
    dir = clean_path(DIR) if args[DIR] else None
    with config.db.session_context() as s:
        run_garmin(config, s, dir=dir, base=args[BASE],
                   user=args[USER], password=args[PASSWD], dates=dates, force=args[FORCE])


def run_garmin(config, s, dir=None, base=None, user=None, password=None, dates=None, force=False, progress=None):

    if not dates: dates = list(missing_dates(s, force=force))
    local_progress = ProgressTree(len(dates), parent=progress)
    if not (base or dir):
        raise Exception('Provide one of base or dir')

    try:
        if not dates:
            log.info('No missing data to download')
            return

        old_format = bool(dir)
        data_dir = dir or config.args._format_path(DATA_DIR)
        user = user or Constant.get_single(s, GARMIN_USER)
        password = password or Constant.get_single(s, GARMIN_PASSWORD)

        last = config.get_constant(SystemConstant.LAST_GARMIN, none=True)
        if last and (now() - local_time_to_time(last)).total_seconds() < 12 * 60 * 60:
            log.info(f'Too soon since previous call ({last}; 12 hours minimum)')
            return

        connect = GarminConnect(log_response=False)
        connect.login(user, password)

        for repeat, date in enumerate(dates):
            if repeat:
                sleep(1)
            log.info('Downloading data for %s' % date)
            try:
                connect.get_monitoring_to_fit_file(date, data_dir, old_format=old_format)
                local_progress.increment()
            except HTTPError:
                log_current_exception(traceback=False)
                if force:
                    log.warning(f'No data for {date}, but continuing ({mm(FORCE)})')
                else:
                    log.info('End of data')
                    break

        config.set_constant(SystemConstant.LAST_GARMIN, time_to_local_time(now()), True)
        return

    finally:
        local_progress.complete()

