<%def
  name="rm_pr_label_step(job_step, job_variant, github_cfg, indent)",
  filter="indent_func(indent),trim"
>
<%
from makoutil import indent_func
pr_trait = job_variant.trait('pull-request')
policies = pr_trait.policies()
require_label = policies.require_label()
replacement_label = policies.replacement_label()
main_repo = job_variant.main_repository()
pr_id_path = main_repo.pr_id_path()
%>
% if require_label:
from util import ctx, info, warning
from github.util import _create_github_api_object
from github3.exceptions import NotFoundError

github_cfg = ctx().cfg_factory().github(cfg_name='${github_cfg.name()}')
github_api = _create_github_api_object(github_cfg)

# assumption: only main repository may be PR-repo
pr_id_path = '${pr_id_path}'
with open(pr_id_path) as f:
  pr_id = int(f.read().strip())

repository = github_api.repository('${main_repo.repo_owner()}', '${main_repo.repo_name()}')
pull_request = repository.pull_request(pr_id)
issue = pull_request.issue()
# rm label to prevent malicious changes to be built
try:
  issue.remove_label('${require_label}')
except NotFoundError:
  warning("label '${require_label}' was not found on the pull request")
else:
  info("removed pr-label '${require_label}'")
% if replacement_label is not None:
issue.add_labels('${replacement_label}')
info("added pr-label '${replacement_label}'")
% endif
% endif
</%def>
