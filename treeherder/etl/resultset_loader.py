import logging
from treeherder.model.derived.jobs import JobsModel
from treeherder.model.models import Repository
from django.core.exceptions import ObjectDoesNotExist

import newrelic.agent

logger = logging.getLogger(__name__)


class ResultsetLoader:
    """Transform and load a list of Resultsets"""

    # {
    #     organization:mozilla - services
    #     details:{
    #         event.type:push
    #         event.base.repo.branch:master
    #         event.head.repo.branch:master
    #         event.head.user.login:mozilla - cloudops - deploy
    #         event.head.repo.url:https://github.com/mozilla-services/cloudops-jenkins.git
    #         event.head.sha:845
    #         aa1c93726af92accd9b748ea361a37d5238b6
    #         event.head.ref:refs / heads / master
    #         event.head.user.email:mozilla - cloudops - deploy @ noreply.github.com
    #     }
    #     repository:cloudops - jenkins
    #     version:1
    # }
    def process_list(self, resultset):

        repo_url = self.get_repo_url(resultset)
        try:
            repo = Repository.objects.get(url=repo_url)

            with JobsModel(repo.name) as jobs_model:
                jobs_model.store_result_set_data(self.transform(resultset))

        except ObjectDoesNotExist:
            newrelic.agent.record_custom_event("skip_unknown_repository",
                                               resultset["details"])


    def get_repo_url(self, resultset):
        try:
            return resultset["details"]["event.head.repo.url"]

        except:
            raise ValueError("Resultset with no repo url")

    def transform(self, pulse_job):
        """
        Transform a pulse job into a job that can be written to disk.  Log
        References and artifacts will also be transformed and loaded with the
        job.

        We can rely on the structure of ``pulse_job`` because it will
        already have been validated against the JSON Schema at this point.
        """
        pass



