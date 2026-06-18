use std::collections::HashSet;

use serde::{Deserialize, Serialize};

/// A real-time activity event delivered to connected clients.
///
/// The shape is shared verbatim with the Django backend (which produces
/// `post.created` events) and the GitHub webhook ingester (which produces
/// `github.release` / `github.push` events).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Event {
    /// Event discriminator, e.g. `post.created`, `github.release`, `github.push`.
    #[serde(rename = "type")]
    pub kind: String,
    /// Who triggered the event (a username or GitHub login).
    pub actor: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub title: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub url: Option<String>,
    /// `owner/name` of the related repository, when applicable.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub repo: Option<String>,
    /// The related ThreadSpace post id, when applicable.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub post_id: Option<String>,
    #[serde(default)]
    pub created_at: String,
}

/// An event plus its delivery target.
///
/// - `room == Some(r)` is a room-scoped delivery (e.g. a project's chat): only
///   connections subscribed to room `r` receive it.
/// - `room == None`, `audience == None` broadcasts to every non-room connection.
/// - `room == None`, `audience == Some(set)` targets connections whose username
///   is in `set` (follower fan-out).
///
/// Room connections and feed connections are kept separate: a room subscriber
/// only ever sees its own room's events, never global broadcasts/fan-out.
#[derive(Debug, Clone)]
pub struct Delivery {
    pub audience: Option<HashSet<String>>,
    pub room: Option<String>,
    pub event: Event,
}

/// Decide whether a delivery should reach a connection identified by its
/// `user` (optional username) and `conn_room` (optional subscribed room).
pub fn should_deliver(
    delivery: &Delivery,
    user: &Option<String>,
    conn_room: &Option<String>,
) -> bool {
    match (&delivery.room, conn_room) {
        // Room-scoped delivery reaches only subscribers of that exact room.
        (Some(target), Some(joined)) => target == joined,
        (Some(_), None) => false,
        // A room connection ignores non-room (broadcast / fan-out) traffic.
        (None, Some(_)) => false,
        // Feed connection: broadcast to all, or fan-out to the named audience.
        (None, None) => match &delivery.audience {
            None => true,
            Some(set) => user.as_ref().is_some_and(|name| set.contains(name)),
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn audience(names: &[&str]) -> Option<HashSet<String>> {
        Some(names.iter().map(|s| s.to_string()).collect())
    }

    fn delivery(audience: Option<HashSet<String>>, room: Option<&str>) -> Delivery {
        Delivery {
            audience,
            room: room.map(|s| s.to_string()),
            event: Event {
                kind: "post.created".into(),
                actor: "alice".into(),
                title: None,
                url: None,
                repo: None,
                post_id: None,
                created_at: String::new(),
            },
        }
    }

    #[test]
    fn broadcast_reaches_every_feed_connection() {
        let d = delivery(None, None);
        assert!(should_deliver(&d, &None, &None));
        assert!(should_deliver(&d, &Some("anyone".into()), &None));
    }

    #[test]
    fn targeted_delivery_matches_only_audience_members() {
        let d = delivery(audience(&["alice", "bob"]), None);
        assert!(should_deliver(&d, &Some("alice".into()), &None));
        assert!(should_deliver(&d, &Some("bob".into()), &None));
        assert!(!should_deliver(&d, &Some("carol".into()), &None));
        assert!(!should_deliver(&d, &None, &None));
    }

    #[test]
    fn room_delivery_reaches_only_that_rooms_subscribers() {
        let d = delivery(None, Some("octo/cat"));
        assert!(should_deliver(
            &d,
            &Some("alice".into()),
            &Some("octo/cat".into())
        ));
        // Wrong room, or not in any room → no delivery.
        assert!(!should_deliver(
            &d,
            &Some("alice".into()),
            &Some("other/repo".into())
        ));
        assert!(!should_deliver(&d, &Some("alice".into()), &None));
    }

    #[test]
    fn room_connections_ignore_broadcast_and_fanout() {
        let broadcast = delivery(None, None);
        let fanout = delivery(audience(&["alice"]), None);
        // A connection subscribed to a room only ever sees its room's events.
        assert!(!should_deliver(
            &broadcast,
            &Some("alice".into()),
            &Some("octo/cat".into())
        ));
        assert!(!should_deliver(
            &fanout,
            &Some("alice".into()),
            &Some("octo/cat".into())
        ));
    }

    #[test]
    fn event_round_trips_through_json() {
        let event = Event {
            kind: "post.created".into(),
            actor: "alice".into(),
            title: Some("shipped a thing".into()),
            url: None,
            repo: Some("alice/proj".into()),
            post_id: Some("abc".into()),
            created_at: "2026-01-01T00:00:00Z".into(),
        };
        let json = serde_json::to_string(&event).unwrap();
        assert!(json.contains("\"type\":\"post.created\""));
        // `url` is None, so it should be omitted entirely.
        assert!(!json.contains("\"url\""));
        let parsed: Event = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed, event);
    }
}
