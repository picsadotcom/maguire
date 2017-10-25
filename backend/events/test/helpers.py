import pendulum

from events.models import Event


def make_event(user, source_model, source_id, event_type, event_data,
               event_at=pendulum.create(
                   2016, 4, 25, 12, 0, 0, tz='Africa/Johannesburg')):
    """
    Helper function to create a new Event
    """
    if event_at is not None:
        event = Event.objects.create(
            source_model=source_model,
            source_id=source_id,
            event_at=event_at,
            event_type=event_type,
            event_data=event_data,
            created_by=user
        )
    else:
        event = Event.objects.create(
            source_model=source_model,
            source_id=source_id,
            event_type=event_type,
            event_data=event_data,
            created_by=user
        )

    return event
