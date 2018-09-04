# Copyright (c) 2018 SAP SE or an SAP affiliate company. All rights reserved. This file is licensed
# under the Apache Software License, v. 2 except as noted otherwise in the LICENSE file
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from slackclient import SlackClient
from pydash import _

from util import warning, info
from model import SlackConfig


class SlackHelper(object):
  def __init__(
          self,
          slack_cfg: SlackConfig
      ):
      self.slack_cfg = slack_cfg

  def post_to_slack(
      self,
      channel: str,
      title: str,
      message: str,
  ):
      api_token = self.slack_cfg.api_token()

      if not api_token:
          warning("can't post to slack as there is no slack api token in config")
      else:
          info('posting message "{title}" to slack channel {c}'.format(title=title, c=channel))
          client = SlackClient(token=api_token)
          # We expect rather long messages, so we do not use incoming webhooks etc. to post
          # messages as those get truncated, see
          # https://api.slack.com/changelog/2018-04-truncating-really-long-messages
          # Instead we use the file upload mechanism so that this limit does not apply.
          result = client.api_call(
              "files.upload",
              channels=channel,
              file=(title, message),
              title=title,
              filetype='post'
          )
          if not _.get(result, 'ok', False):
              warning('failed to post to slack channel {c}: {err}'.format(
                  c=channel,
                  err=_.get(result, 'error')
              ))