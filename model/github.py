# Copyright (c) 2019 SAP SE or an SAP affiliate company. All rights reserved. This file is licensed
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

import random
from urllib.parse import urlparse

from model.base import (
    BasicCredentials,
    NamedModelElement,
)


class GithubConfig(NamedModelElement):
    '''
    Not intended to be instantiated by users of this module
    '''

    def purpose_labels(self):
        return set(self.raw.get('purpose_labels', ()))

    def ssh_url(self):
        return self.raw.get('sshUrl')

    def http_url(self):
        return self.raw.get('httpUrl')

    def api_url(self):
        return self.raw.get('apiUrl')

    def tls_validation(self):
        return not self.raw.get('disable_tls_validation')

    def webhook_secret(self):
        return self.raw.get('webhook_token')

    def credentials(self):
        return GithubCredentials(self.raw.get('technicalUser'))

    def matches_hostname(self, host_name):
        return host_name.lower() == urlparse(self.http_url()).hostname.lower()

    def _optional_attributes(self):
        return (
            'purpose_labels',
        )

    def _required_attributes(self):
        return [
            'sshUrl',
            'httpUrl',
            'apiUrl',
            'disable_tls_validation',
            'webhook_token',
            'technicalUser'
        ]

    def validate(self):
        super().validate()
        # validation of credentials implicitly happens in the constructor
        self.credentials()


class GithubCredentials(BasicCredentials):
    '''
    Not intended to be instantiated by users of this module
    '''

    def auth_token(self):
        tokens = self.raw.get('auth_tokens', None)
        if tokens:
            return random.choice(tokens)
        # fallback to single token
        return self.raw.get('authToken')

    def set_auth_token(self, auth_token):
        self.raw['authToken'] = auth_token

    def private_key(self):
        return self.raw.get('privateKey')

    def email_address(self):
        return self.raw.get('emailAddress')

    def _required_attributes(self):
        required_attribs = set(super()._required_attributes())
        return required_attribs | set(('authToken','privateKey', 'emailAddress'))
