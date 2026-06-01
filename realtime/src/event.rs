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

/// An event plus its delivery target. `audience == None` broadcasts to every
/// connected client; otherwise only clients whose username is in the set
/// receive it (this is how follower fan-out is targeted).
#[derive(Debug, Clone)]
pub struct Delivery {
    pub audience: Option<HashSet<String>>,
    pub event: Event,
}

/// Decide whether a delivery should reach a given connection.
pub fn should_deliver(audience: &Option<HashSet<String>>, user: &Option<String>) -> bool {
    match audience {
        None => true,
        Some(set) => user.as_ref().is_some_and(|name| set.contains(name)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn audience(names: &[&str]) -> Option<HashSet<String>> {
        Some(names.iter().map(|s| s.to_string()).collect())
    }

    #[test]
    fn broadcast_reaches_everyone() {
        assert!(should_deliver(&None, &None));
        assert!(should_deliver(&None, &Some("anyone".into())));
    }

    #[test]
    fn targeted_delivery_matches_only_audience_members() {
        let aud = audience(&["alice", "bob"]);
        assert!(should_deliver(&aud, &Some("alice".into())));
        assert!(should_deliver(&aud, &Some("bob".into())));
        assert!(!should_deliver(&aud, &Some("carol".into())));
        assert!(!should_deliver(&aud, &None));
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
