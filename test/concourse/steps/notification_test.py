import os
import pathlib
import sys
import tempfile
import unittest

from unittest.mock import MagicMock

import test_utils

from concourse.client import BuildStatus
from concourse.steps import step_def, step_lib_def
from concourse.model.step import PipelineStep
from concourse.model.traits.notifications import (
    NotificationCfgSet,
    NotificationTriggeringPolicy,
)


class NotificationStepTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.meta_dir = os.path.join(self.tmp_dir.name, 'meta')
        os.mkdir(self.meta_dir)
        test_utils.populate_meta_dir(self.meta_dir)
        self.on_error_dir = os.path.join(self.tmp_dir.name, 'on_error_dir')
        os.mkdir(self.on_error_dir)

        self.job_step = PipelineStep('step1', raw_dict={})
        self.job_step._notifications_cfg = NotificationCfgSet('default', {})
        self.cfg_set = MagicMock()
        self.github_cfg = MagicMock()
        self.github_cfg.name = MagicMock(return_value='github_cfg')
        self.email_cfg = MagicMock()
        self.email_cfg.name = MagicMock(return_value='email_cfg')
        self.cfg_set.github = MagicMock(return_value=self.github_cfg)
        self.cfg_set.email = MagicMock(return_value=self.email_cfg)

        self.render_step = step_def('notification')

        self.old_cwd = os.getcwd()
        os.chdir(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()
        os.chdir(self.old_cwd)

    def test_render_and_compile(self):
        # as a smoke-test, just try to render
        step_snippet = self.render_step(
            job_step=self.job_step,
            cfg_set=self.cfg_set,
            repo_cfgs=(),
            subject='mail_subject1',
            indent=0
        )

        # try to compile (-> basic syntax check)
        return compile(step_snippet, 'notification', 'exec')


class NotificationStepLibTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.meta_dir = os.path.join(self.tmp_dir.name, 'meta')
        os.mkdir(self.meta_dir)
        test_utils.populate_meta_dir(self.meta_dir)

        self.render_step_lib = step_lib_def('notification')

        self.old_cwd = os.getcwd()
        os.chdir(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()
        os.chdir(self.old_cwd)

    def test_meta_vars(self):
        exec(self.render_step_lib())

        result = eval('meta_vars()')

        for name in (
            'atc-external-url',
            'build-team-name',
            'build-pipeline-name',
            'build-job-name',
            'build-name'
        ):
            self.assertEqual(result[name], name)

    def test_job_url(self):
        exec(self.render_step_lib())
        v = {
            'atc-external-url': 'f://x',
            'build-team-name': 'team',
            'build-pipeline-name': 'pl',
            'build-job-name': 'bjn',
            'build-name': 'bn'
        }
        examinee = vars()['job_url']
        result = examinee(v)

        self.assertEqual(result, 'f://x/teams/team/pipelines/pl/jobs/bjn/builds/bn')

    def test_should_notify(self):
        exec(self.render_step_lib())
        examinee = vars()['should_notify']

        # mock away `determine_previous_build_status` (previous build "succeeded"
        build_status_mock = MagicMock(return_value=BuildStatus.SUCCEEDED)

        # test policies in case previous build succeeded
        assert examinee(
                NotificationTriggeringPolicy.ONLY_FIRST,
                meta_vars={},
                determine_previous_build_status=build_status_mock,
        )
        assert examinee(
                NotificationTriggeringPolicy.ALWAYS,
                meta_vars={},
                determine_previous_build_status=build_status_mock,
        )
        assert not examinee(
                NotificationTriggeringPolicy.NEVER,
                meta_vars={},
                determine_previous_build_status=build_status_mock,
        )

        # test policies in case previous build failed
        build_status_mock = MagicMock(return_value=BuildStatus.FAILED)
        assert not examinee(
                NotificationTriggeringPolicy.ONLY_FIRST,
                meta_vars={},
                determine_previous_build_status=build_status_mock,
        )
        assert examinee(
                NotificationTriggeringPolicy.ALWAYS,
                meta_vars={},
                determine_previous_build_status=build_status_mock,
        )
        assert not examinee(
                NotificationTriggeringPolicy.NEVER,
                meta_vars={},
                determine_previous_build_status=build_status_mock,
        )