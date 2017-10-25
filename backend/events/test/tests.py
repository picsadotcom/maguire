import json
import pytz
from datetime import datetime
from uuid import UUID
from freezegun import freeze_time

from django.contrib.auth.models import User

from identities.test.helpers import make_user
from events.models import Event
from events.test.helpers import make_event
from events import tasks
from events.tasks import model_updated, client_suspended
from maguire.schema import schema
from maguire.utils import uuid_from_b64
from maguire.test.tests import CoreTestCase, CoreTransactionTestCase


class TestEventHelpers(CoreTestCase):
    def test_make_event_helper(self):
        # Precheck
        users = User.objects.all()
        events = Event.objects.all()
        users_pre = users.count()
        events_pre = events.count()

        # Setup
        user = make_user()

        # Execute
        event = make_event(user=user)

        # Check
        self.assertEqual(users.count(), users_pre + 1)
        self.assertEqual(events.count(), events_pre + 1)

        d = Event.objects.get(id=event.id)
        self.assertEqual(d.source_model, "client")
        self.assertEqual(d.source_id, UUID("48368465-74ef-4c33-8d29-f1013d03d812"))
        self.assertEqual(d.event_at.isoformat(), "2016-04-25T10:00:00+00:00")
        self.assertEqual(d.event_type, "client.suspended")
        self.assertEqual(d.event_data, {"description": "Client Suspended"})
        self.assertEqual(d.created_by, user)
        self.assertIsNone(d.updated_by)
        self.assertIsNotNone(d.created_at)
        self.assertIsNotNone(d.updated_at)

    @freeze_time("2016-10-30")
    def test_make_event_helper_no_event_at(self):
        self.assertEqual(datetime(2016, 10, 30, 0, 0, 0, tzinfo=pytz.utc),
                         datetime.now(pytz.utc))
        # Setup
        user = make_user()
        # Execute
        event = make_event(user=user, event_at=None)
        # Check
        d = Event.objects.get(id=event.id)
        self.assertEqual(d.event_at.isoformat(), "2016-10-30T00:00:00+00:00")


class TestEventsApp(CoreTestCase):

    def test_event_as_json(self):
        # Setup
        event = Event.objects.get(id="57dc822d-f8e6-41e3-a858-185c846896c8")
        # Execute
        as_json = event.as_json()
        # Check
        self.assertEqual(as_json, {
            "id": "57dc822d-f8e6-41e3-a858-185c846896c8",
            "source_model": "client",
            "source_id": "f2536ccb-1300-48a2-bb6f-a001c82b8658",
            "event_at": "2016-10-07T06:10:39.381000+00:00",
            "event_type": "client.suspended",
            "event_data": {
                "description": "Maternity leave started"
            },
            "created_by": 101,
            "updated_by": 101,
            "created_at": "2016-10-07T06:10:39.381000+00:00",
            "updated_at": "2016-10-07T06:10:39.381000+00:00",
        })

    # TEST GRAPHQL QUERIES
    def test_event_graphql(self):
        # Setup
        event = Event.objects.get(id="57dc822d-f8e6-41e3-a858-185c846896c8")
        event_id = str(event.node_id)
        query = '''
        query GetEvent {
          event(id:"%s") {
            id
            sourceModel
            sourceId
            eventAt
            eventType
            eventData
            createdAt
          }
        }
        ''' % (event_id, )

        # Execute
        result = schema.execute(query)
        # Check
        self.assertEqual(result.errors, None)
        self.assertEqual(result.data["event"]["id"], event_id)
        self.assertEqual(result.data["event"]["sourceModel"], "client")
        self.assertEqual(result.data["event"]["sourceId"], "f2536ccb-1300-48a2-bb6f-a001c82b8658")
        self.assertEqual(result.data["event"]["eventType"], "client.suspended")
        self.assertEqual(result.data["event"]["eventData"],
                         '{"description": "Maternity leave started"}')

    def test_events_graphql(self):
        # Setup
        query = '''
        query GetEvents {
            events {
                edges {
                    node {
                        id
                        sourceModel
                        sourceId
                        eventAt
                        eventType
                        eventData
                        createdAt
                    }
                }
            }
        }
        '''

        # Execute
        result = schema.execute(query)
        # Check
        self.assertEqual(result.errors, None)

    def test_event_graphql_mutation_edit_blocked(self):
        # Setup
        event = Event.objects.get(id="57dc822d-f8e6-41e3-a858-185c846896c8")
        eventid = str(event.node_id)
        query = '''
        mutation MutateEvent {
            eventMutate(input: {id: "%s", eventType: "Changed"}) {
                event {
                    id
                    sourceModel
                    sourceId
                    eventAt
                    eventType
                    eventData
                    createdAt
                }
            }
        }
        ''' % eventid

        # Execute
        result = schema.execute(query)
        # Check
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].message, "Edit mutation not supported by Event model")
        event.refresh_from_db()
        self.assertEqual(event.event_type, "client.suspended")

    def test_event_graphql_mutation_new(self):
        # Setup
        events = Event.objects.all()
        events_count = events.count()
        query = '''
        mutation MutateEvent {
            eventMutate(
                input: {
                    sourceModel: "client",
                    sourceId: "f2536ccb-1300-48a2-bb6f-a001c82b8658",
                    eventAt: "1999-09-9",
                    eventType: "client.suspended",
                    eventData: %s
                }
            ) {
                event {
                    id
                    sourceModel
                    sourceId
                    eventAt
                    eventType
                    eventData
                    createdAt
                }
            }
        }
        ''' % json.dumps(json.dumps({"description": "Fired"}))

        # Execute
        result = schema.execute(query)
        # Check
        self.assertEqual(result.errors, None)
        eventid = uuid_from_b64(result.data["eventMutate"]["event"]["id"])
        event = Event.objects.get(id=eventid)
        self.assertEqual(event.source_model, "client")
        self.assertEqual(event.source_id, UUID("f2536ccb-1300-48a2-bb6f-a001c82b8658"))
        self.assertEqual(event.event_at, datetime(1999, 9, 9, 0, 0, tzinfo=pytz.utc))
        self.assertEqual(event.event_type, "client.suspended")
        self.assertEqual(event.event_data, {"description": "Fired"})
        events_count_new = Event.objects.all().count()
        self.assertEqual(events_count+1, events_count_new)

    # TEST TASKS
    def test_task_model_updated(self):
        # Setup
        # create a model.updated Event
        event_dict = {
            "source_model": "client",
            "source_id": "cdca5116-5c82-4897-9890-8e2e16b3f65a",  # from client_fixtures.json
            "event_at": datetime(2016, 9, 29, 0, 0, 0, tzinfo=pytz.utc),
            "event_type": "model.updated",
            "event_data": {
                "status": "suspended",
                "status_reason": "Maternity leave started"
            },
            "created_by": User.objects.get(id=101)
        }
        event = Event.objects.create(**event_dict)

        # Execute
        result = model_updated.apply_async(kwargs={"event_id": event.id})

        # Check
        self.assertEqual(result.get(), "Created Event type client.suspended")

    def test_task_model_updated_no_match(self):
        # Setup
        # create a model.updated Event
        event_dict = {
            "source_model": "client",
            "source_id": "cdca5116-5c82-4897-9890-8e2e16b3f65a",  # from client_fixtures.json
            "event_at": datetime(2016, 9, 29, 0, 0, 0, tzinfo=pytz.utc),
            "event_type": "model.updated",
            "event_data": {
                "status": "unrecognised_status"
            },
            "created_by": User.objects.get(id=101)
        }
        event = Event.objects.create(**event_dict)

        # Execute
        result = model_updated.apply_async(kwargs={"event_id": event.id})

        # Check
        self.assertEqual(result.get(), "No Event created")

    def test_task_client_suspended(self):
        # Setup
        # create a client.suspended Event
        event_dict = {
            "source_model": "client",
            "source_id": "cdca5116-5c82-4897-9890-8e2e16b3f65a",  # from client_fixtures.json
            "event_at": datetime(2016, 9, 29, 0, 0, 0, tzinfo=pytz.utc),
            "event_type": "client.suspended",
            "event_data": {
                "status": "suspended",
                "status_reason": "Maternity leave started"
            },
            "created_by": User.objects.get(id=101)
        }
        event = Event.objects.create(**event_dict)

        # Execute
        result = client_suspended.apply_async(kwargs={"event_id": event.id})

        # Check
        self.assertEqual(result.get(), "client_suspended task complete")


class TestEventPostSaveHooks(CoreTransactionTestCase):

    def test_event_post_save_fires(self):
        """
        Tests that the post-save hook is firing by creating a model.updated
        Event which should create another client.suspended Event
        """
        # Setup
        events_count = Event.objects.all().count()
        user = make_user()
        # Execute
        make_event(
            user=user, source_model="client", source_id="f2536ccb-1300-48a2-bb6f-a001c82b8658",
            event_type="model.updated", event_data={"status": "suspended"}
        )
        # Check
        self.assertEqual(Event.objects.all().count(), events_count + 2)
        # Teardown

    def test_event_post_save_task_naming(self):
        # Check
        # check 1 false
        self.assertFalse("random.task".replace(".", "_") in dir(tasks))
        # check expected tasks
        self.assertTrue("model.updated".replace(".", "_") in dir(tasks))
        self.assertTrue("client.suspended".replace(".", "_") in dir(tasks))
