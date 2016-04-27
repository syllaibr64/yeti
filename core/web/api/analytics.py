from flask.ext.login import current_user
from flask.ext.classy import route
from flask import request

from core.observables import Observable
from core.web.api.crud import CrudApi
from core import analytics
from core.analytics_tasks import schedule
from core.web.api.api import render
from core.web.helpers import get_object_or_404


class ScheduledAnalytics(CrudApi):
    template = 'scheduled_analytics_api.html'
    objectmanager = analytics.ScheduledAnalytics

    @route("/<id>/refresh", methods=["POST"])
    def refresh(self, id):
        """Runs a Scheduled Analytics

        :query ObjectID id: Scheduled Analytics ObjectID
        :>json ObjectID id: ID of refreshed Scheduled Analytics
        """
        schedule.delay(id)
        return render({"id": id})

    @route("/<id>/toggle", methods=["POST"])
    def toggle(self, id):
        """Toggles a Scheduled Analytics

        Scheduled Analytics can be individually disabled using this endpoint.

        :query ObjectID id: Analytics ID
        :>json ObjectID id: The Analytics's ObjectID
        :>json boolean status: The result of the toggle operation (``true`` means the export has been enabled, ``false`` means it has been disabled)
        """
        a = self.objectmanager.objects.get(id=id)
        a.enabled = not a.enabled
        a.save()

        return render({"id": id, "status": a.enabled})


class OneShotAnalytics(CrudApi):
    template = "oneshot_analytics_api.html"
    objectmanager = analytics.OneShotAnalytics

    def index(self):
        data = []

        for obj in self.objectmanager.objects.all():
            info = obj.info()

            info['available'] = True
            if hasattr(obj, 'settings') and not current_user.has_settings(obj.settings):
                info['available'] = False

            data.append(info)

        return render(data, template=self.template)

    @route("/<id>/toggle", methods=["POST"])
    def toggle(self, id):
        """Toggles a One-shot Analytics

        One-Shot Analytics can be individually disabled using this endpoint.

        :query ObjectID id: Analytics ID
        :>json ObjectID id: The Analytics's ObjectID
        :>json boolean status: The result of the toggle operation (``true`` means the export has been enabled, ``false`` means it has been disabled)
        """
        analytics = get_object_or_404(self.objectmanager, id=id)
        analytics.enabled = not analytics.enabled
        analytics.save()

        return render({"id": analytics.id, "status": analytics.enabled})

    @route('/<id>/run', methods=["POST"])
    def run(self, id):
        """Runs a One-Shot Analytics

        Asynchronously runs a One-Shot Analytics against a given observable.
        Returns an ``AnalyticsResults`` instance, which can then be used to fetch
        the analytics results

        :query ObjectID id: Analytics ID
        :form ObjectID id: Observable ID
        :>json object: JSON object representing the ``AnalyticsResults`` instance
        """
        analytics = get_object_or_404(self.objectmanager, id=id)
        observable = get_object_or_404(Observable, id=request.form.get('id'))

        return render(analytics.run(observable, current_user.settings).to_mongo())

    def _analytics_results(self, results):
        """Query an analytics status

        Query the status of an ``AnalyticsResults`` entry.

        :query ObjectID id: ``AnalyticsResults`` ID

        The response is a JSON object representing the ``AnalyticsResults`` instance.
        The response object also contains a ``results`` field:

        :>json object results: JSON object containing two arrays representing the ``nodes`` and ``links`` generated by the analytics
        """

        nodes_id = set()
        nodes = list()
        links = list()

        # First, add the analyzed node
        nodes_id.add(results.observable.id)
        nodes.append(results.observable.to_mongo())

        for link in results.results:
            for node in (link.src, link.dst):
                if node.id not in nodes_id:
                    nodes_id.add(node.id)
                    nodes.append(node.to_mongo())
            links.append(link.to_dict())

        results = results.to_mongo()
        results['results'] = {'nodes': nodes, 'links': links}

        return results

    @route('/<id>/status')
    def status(self, id):
        results = get_object_or_404(analytics.AnalyticsResults, id=id)

        return render(self._analytics_results(results))

    @route('/<id>/last/<observable_id>')
    def last(self, id, observable_id):
        try:
            results = analytics.AnalyticsResults.objects(analytics=id, observable=observable_id, status="finished").order_by('-datetime').limit(1)
            return render(self._analytics_results(results[0]))
        except:
            return render(None)
