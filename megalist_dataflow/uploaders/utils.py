# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from models.execution import DestinationType
from models.execution import Execution
import pytz

MAX_RETRIES = 3

timezone = pytz.timezone('America/Sao_Paulo')


def get_ads_service(service_name, version, oauth_credentials, developer_token,
                    customer_id):
    from googleads import adwords
    from googleads import oauth2
    oauth2_client = oauth2.GoogleRefreshTokenClient(
        oauth_credentials.get_client_id(), oauth_credentials.get_client_secret(),
        oauth_credentials.get_refresh_token())
    client = adwords.AdWordsClient(
        developer_token,
        oauth2_client,
        'MegaList Dataflow',
        client_customer_id=customer_id)
    
    #client.partial_failure = True
    return client.GetService(service_name, version=version)


def format_date(date):
    if isinstance(date, datetime.datetime):
        pdate = date
    else:
        pdate = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f')

    return f'{datetime.datetime.strftime(pdate, "%Y%m%d %H%M%S")} {timezone.zone}'


def safe_process(logger):
    def deco(func):
        def inner(*args, **kwargs):
            batch = args[1]
            if not batch:
                logger.warning('Skipping upload, received no elements.')
                return
            logger.info(f'Uploading {len(batch.elements)} rows...')
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f'Error uploading data for :{batch.elements}')
                logger.error(e, exc_info=True)
                logger.exception('Error uploading data.')

        return inner

    return deco


def safe_call_api(function, logger, *args, **kwargs):
    current_retry = 1
    _do_safe_call_api(function, logger, current_retry, *args, **kwargs)


def _do_safe_call_api(function, logger, current_retry, *args, **kwargs):
    try:
        return function(*args, *kwargs)
    except Exception as e:
        if current_retry < MAX_RETRIES:
            logger.exception(
                f'Fail number {current_retry}. Stack track follows. Trying again.')
            current_retry += 1
            return _do_safe_call_api(function, logger, current_retry, *args, **kwargs)


def convert_datetime_tz(dt, origin_tz, destination_tz):
    datetime_obj = pytz.timezone(origin_tz).localize(dt)
    return datetime_obj.astimezone(pytz.timezone(destination_tz))
