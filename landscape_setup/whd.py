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

import os

from ensure import ensure_annotations

from landscape_setup import kube_ctx
from landscape_setup.utils import (
    ensure_cluster_version,
    create_tls_secret,
    execute_helm_deployment,
)
from model import (
    ConfigFactory,
)
from model.webhook_dispatcher import (
    WebhookDispatcherDeploymentConfig
)
from util import (
    ctx as global_ctx,
    not_empty,
    info,
)


@ensure_annotations
def create_webhook_dispatcher_helm_values(
    cfg_set,
    webhook_dispatcher_deployment_cfg: WebhookDispatcherDeploymentConfig,
    cfg_factory: ConfigFactory,
):
    # calculate secrets server endpoint
    secrets_server_name = webhook_dispatcher_deployment_cfg.secrets_server_config_name()
    secrets_server_cfg = cfg_factory.secrets_server(secrets_server_name)
    secrets_server_endpoint = secrets_server_cfg.endpoint_url()
    secrets_server_concourse_cfg_name = secrets_server_cfg.secrets().concourse_cfg_name()
    container_port = webhook_dispatcher_deployment_cfg.webhook_dispatcher_container_port()

    env_vars = []
    env_vars.append({
        'name': 'SECRETS_SERVER_ENDPOINT', 'value': secrets_server_endpoint
    })
    env_vars.append({
        'name': 'SECRETS_SERVER_CONCOURSE_CFG_NAME', 'value': secrets_server_concourse_cfg_name
    })

    cmd_args = [
        '--webhook-dispatcher-cfg-name',
        webhook_dispatcher_deployment_cfg.webhook_dispatcher_config_name(),
        '--port',
        f'"{container_port}"',
        '--cfg-set-name',
        cfg_set.name(),
    ]

    helm_values = {
        'ingress_host': webhook_dispatcher_deployment_cfg.ingress_host(),
        'external_url': webhook_dispatcher_deployment_cfg.external_url(),
        'tls_name': webhook_dispatcher_deployment_cfg.tls_config_name(),
        'image_reference': webhook_dispatcher_deployment_cfg.image_reference(),
        'cmd_args': cmd_args,
        'env_vars': env_vars,
        'webhook_dispatcher_port': container_port,
    }

    return helm_values


@ensure_annotations
def deploy_webhook_dispatcher_landscape(
    cfg_set,
    webhook_dispatcher_deployment_cfg: WebhookDispatcherDeploymentConfig,
    chart_dir: str,
    deployment_name: str,
):
    not_empty(deployment_name)

    chart_dir = os.path.abspath(chart_dir)
    cfg_factory = global_ctx().cfg_factory()

    # Set the global context to the cluster specified in KubernetesConfig
    kubernetes_config_name = webhook_dispatcher_deployment_cfg.kubernetes_config_name()
    kubernetes_config = cfg_factory.kubernetes(kubernetes_config_name)
    kube_ctx.set_kubecfg(kubernetes_config.kubeconfig())

    ensure_cluster_version(kubernetes_config)

    # TLS config
    tls_config_name = webhook_dispatcher_deployment_cfg.tls_config_name()
    tls_config = cfg_factory.tls_config(tls_config_name)
    tls_secret_name = "webhook-dispatcher-tls"

    info('Creating tls-secret ...')
    create_tls_secret(
        tls_config=tls_config,
        tls_secret_name=tls_secret_name,
        namespace=deployment_name,
    )

    kubernetes_cfg_name = webhook_dispatcher_deployment_cfg.kubernetes_config_name()
    kubernetes_cfg = cfg_factory.kubernetes(kubernetes_cfg_name)

    whd_helm_values = create_webhook_dispatcher_helm_values(
        cfg_set=cfg_set,
        webhook_dispatcher_deployment_cfg=webhook_dispatcher_deployment_cfg,
        cfg_factory=cfg_factory,
    )

    execute_helm_deployment(
        kubernetes_cfg,
        deployment_name,
        chart_dir,
        deployment_name,
        whd_helm_values
    )
