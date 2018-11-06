<%def
  name="notification_step(
    job_step,
    cfg_set,
    repo_cfgs,
    subject,
    indent
  )",
  filter="indent_func(indent),trim"
>
<%
from makoutil import indent_func
# xxx: for now, assume all repositories are from same github
default_github_cfg_name = cfg_set.github().name()
email_cfg = cfg_set.email()

notification_cfg = job_step.notifications_cfg()
notification_cfg_name = notification_cfg.name()
on_error_cfg = notification_cfg.on_error()
triggering_policy = on_error_cfg.triggering_policy()
on_error_dir = job_step.output('on_error_dir')
%>
import sys
import os
import traceback

import util
import mailutil

${notification_step_lib()}

v = meta_vars()

from util import ctx
cfg_factory = ctx().cfg_factory()
cfg_set = cfg_factory.cfg_set("${cfg_set.name()}")


print('Notification cfg: ${notification_cfg_name}')
print('Triggering policy: ${triggering_policy}')

if not should_notify(
    NotificationTriggeringPolicy('${triggering_policy.value}'),
    meta_vars=v,
):
    print('will not notify due to policy')
    sys.exit(0)


def retrieve_build_log():
    try:
      build_id = v['build-id']
      task_id = concourse_api.build_plan(build_id=build_id).task_id(task_name='${job_step.name}')
      build_events = concourse_api.build_events(build_id=build_id)
      build_log = '\n'.join(build_events.iter_buildlog(task_id=task_id))
      return build_log
    except Exception as e:
      traceback.print_exc() # print_err, but send email notification anyway
      return 'failed to retrieve build log'


notify_file = os.path.join('${on_error_dir}', 'notify.cfg')
if os.path.isfile(notify_file):
  notify_cfg = util.parse_yaml_file(notify_file)
  email_cfg = notify_cfg.get('email', {})
  util.info('found notify.cfg - applying cfg:')
  print(notify_cfg)
else:
  email_cfg = {
    'recipients': None,
    'component_name_recipients': None,
    'codeowners_files': None,
    'mail_body': None,
  }
  notify_cfg = {'email': email_cfg}

def default_mail_recipients():
  recipients = set()
% for repo_cfg in repo_cfgs:
  recipients.update(mailutil.determine_mail_recipients(
    github_cfg_name="${repo_cfg.cfg_name() if repo_cfg.cfg_name() else default_github_cfg_name}",
    src_dirs=("${repo_cfg.resource_name()}",),
    )
  )
  return recipients
% endfor

def retrieve_component_name_recipients(email_cfg):
    component_names = email_cfg.get('component_name_recipients', ())
    codeowners_files = email_cfg.get('codeowners_files', ())

    component_recipients = mailutil.determine_mail_recipients(
        github_cfg_name="${default_github_cfg_name}", # todo: actually this is not required here
        component_names=component_names,
        codeowners_files=codeowners_files,
    )
    recipients = set(email_cfg.get('recipients', set()))
    recipients.update(component_recipients)
    email_cfg['recipients'] = recipients


# fill notify_cfg with default values if not configured
if not email_cfg.get('recipients'):
  email_cfg['recipients'] = default_mail_recipients()
if not email_cfg.get('mail_body'):
  email_cfg['mail_body'] = retrieve_build_log()
retrieve_component_name_recipients(email_cfg)


# determine mail recipients
email_cfg_name = "${email_cfg.name()}"
mailutil.notify(
  subject="${subject}",
  body='\n'.join((job_url(v), email_cfg['mail_body'])),
  email_cfg_name=email_cfg_name,
  recipients=email_cfg['recipients'],
)
</%def>

<%def name="notification_step_lib()">
from concourse.model.traits.notifications import NotificationTriggeringPolicy
from concourse.client import from_cfg, BuildStatus

def meta_vars():
    v = {}
    for name in (
      'build-id',
      'build-name',
      'build-job-name',
      'build-team-name',
      'build-pipeline-name',
      'atc-external-url'
    ):
      with open(os.path.join('meta', name)) as f:
        v[name] = f.read().strip()

    return v

def job_url(v):
    return '/'.join([
      v['atc-external-url'],
      'teams',
      v['build-team-name'],
      'pipelines',
      v['build-pipeline-name'],
      'jobs',
      v['build-job-name'],
      'builds',
      v['build-name']
    ])

def determine_previous_build_status(v):
    concourse_api = from_cfg(cfg_set.concourse(), team_name=v['build-team-name'])
    try:
      build_number = int(v['build-name'])
      previous_build = str(build_number - 1)
      previous_build = concourse_api.job_build(
        pipeline_name=v['build-pipeline-name'],
        job_name=v['build-job-name'],
        build_name=previous_build
      )
      return previous_build.status()
    except Exception as e:
      if type(e) == SystemExit:
        raise e
      # in doubt, ensure notification is sent
      traceback.print_exc()
      return None

def should_notify(
    triggering_policy,
    meta_vars,
    determine_previous_build_status=determine_previous_build_status,
):
    if triggering_policy == NotificationTriggeringPolicy.ALWAYS:
        return True
    elif triggering_policy == NotificationTriggeringPolicy.NEVER:
        return False
    elif triggering_policy == NotificationTriggeringPolicy.ONLY_FIRST:
        previous_build_status = determine_previous_build_status(meta_vars)
        if not previous_build_status:
          print('failed to determine previous build status - will notify')
          return True

        # assumption: current job failed
        if previous_build_status in (BuildStatus.FAILED, BuildStatus.ERRORED):
          print('previous build was already broken - will not notify')
          return False
        return True
    else:
        raise NotImplementedError

</%def>