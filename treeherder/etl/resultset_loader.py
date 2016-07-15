import logging

from treeherder.etl.common import fetch_json
from treeherder.model.derived.jobs import JobsModel
from treeherder.model.models import Repository
from django.core.exceptions import ObjectDoesNotExist

import newrelic.agent

logger = logging.getLogger(__name__)


class ResultsetLoader:
    """Transform and load a list of Resultsets"""

    def process(self, resultset, exchange):

        transformer = self.get_transformer(resultset, exchange)
        try:
            repo = Repository.objects.get(url=transformer.repo_url)

            with JobsModel(repo.name) as jobs_model:
                jobs_model.store_result_set_data(
                    transformer.transform(resultset))

        except ObjectDoesNotExist:
            newrelic.agent.record_custom_event("skip_unknown_repository",
                                               resultset["details"])

    def get_transformer(self, resultset, exchange):
        if exchange.contains("github"):
            if exchange.endswith("push"):
                return GithubPushTransformer(resultset, exchange)
            elif exchange.endswith("pull-request"):
                return GithubPullRequestTransformer(resultset, exchange)
        elif exchange.contains("hgpushes"):
            return HgPushTransformer(resultset, exchange)
        raise PulseResultsetError(
            "Unsupported resultset type: {}".format(exchange))


class GithubTransformer:

    def __init__(self, resultset, exchange):
        self.resultset = resultset
        self.exchange = exchange

        try:
            self.repo_url = resultset["details"]["event.head.repo.url"]
        except:
            raise PulseResultsetError(
                "Unable to find Github repo.url in resultset: {}".format(
                    resultset))

class GithubPushTransformer(GithubTransformer):
    # {
    #     organization:mozilla - services
    #     details:{
    #         event.type:push
    #         event.base.repo.branch:master
    #         event.head.repo.branch:master
    #         event.head.user.login:mozilla-cloudops-deploy
    #         event.head.repo.url:https://github.com/mozilla-services/cloudops-jenkins.git
    #         event.head.sha:845aa1c93726af92accd9b748ea361a37d5238b6
    #         event.head.ref:refs/heads/master
    #         event.head.user.email:mozilla-cloudops-deploy@noreply.github.com
    #     }
    #     repository:cloudops-jenkins
    #     version:1
    # }

    def transform(self):
        commit = self.resultset["details"]["event.head.sha"]
        push_url = "https://api.github.com/repos/mozilla/fxa-auth-server/commits"
        url = "https://api.github.com/repos/mozilla/fxa-auth-server/commits?sha=8ad10c9435217397627b98ff3753eff9e22cdd9d"
        # do the transformation of what we have into a skeleton RS and either
        # schedule a celery task to fill-in, or just do it here.  The RPM may
        # well be low enough that it's fine to just make the query here.

class GithubPullRequestTransformer(GithubTransformer):
    # {
    #     organization:mozilla
    #     action:synchronize
    #     details:{
    #         event.type:pull_request.synchronize
    #         event.base.repo.branch:master
    #         event.pullNumber:561
    #         event.base.user.login:mozilla
    #         event.base.repo.url:https: // github.com / mozilla / dxr.git
    #         event.base.sha:270077cdb8219460714c3e4ba29e5527cbb1caf1
    #         event.base.ref:master
    #         event.head.user.login:pelmers
    #         event.head.repo.url:https: // github.com / pelmers / dxr.git
    #         event.head.repo.branch:dsecrips
    #         event.head.sha:f1791a6e3030d3b6d4d8dd77d5020b3dc890204e
    #         event.head.ref:dsecrips
    #         event.head.user.email:peter.elmers @ yahoo.com
    #     }
    #     repository:dxr
    #     version:1
    # }
    def transform(self):
        pass

class HgPushTransformer:
    """
    payload:{} 3 items
        pushlog_pushes:[] 1 item
            0:{} 5 items
                time:14686073660
                push_full_json_url:https://hg.mozilla.org/try/json-pushes?version=2&full=1&startID=134147&endID=134148
                pushid:134148
                push_json_url:https://hg.mozilla.org/try/json-pushes?version=2&startID=134147&endID=134148
                user:amiyaguchi@mozilla.com
        heads:[] 1 item
            0:a6c36f356d6b6bd34778bcf20506f4424b61b63c
        repo_url:https://hg.mozilla.org/try
        _meta:{} 4 items
            sent:2016-07-15T18:30:00.423330
            routing_key:try
            serializer:json
            exchange:exchange/hgpushes/v1

    """
    def __init__(self, resultset, exchange):
        self.resultset = resultset
        self.exchange = exchange

        try:
            self.repo_url = resultset["payload"]["repo_url"]
        except:
            raise PulseResultsetError(
                "Unable to find Hg repo_url in resultset: {}".format(
                    resultset))


class PulseResultsetError(ValueError):
    pass