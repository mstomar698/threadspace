use hmac::{Hmac, Mac};
use serde_json::Value;
use sha2::Sha256;

use crate::event::Event;

type HmacSha256 = Hmac<Sha256>;

/// Verify the `X-Hub-Signature-256` header GitHub sends with webhook payloads.
///
/// The header looks like `sha256=<hex digest>`; we recompute the HMAC of the
/// raw body with the shared secret and compare in constant time.
pub fn verify_signature(secret: &str, signature_header: &str, body: &[u8]) -> bool {
    let Some(hex_digest) = signature_header.strip_prefix("sha256=") else {
        return false;
    };
    let Ok(expected) = hex::decode(hex_digest) else {
        return false;
    };
    let Ok(mut mac) = HmacSha256::new_from_slice(secret.as_bytes()) else {
        return false;
    };
    mac.update(body);
    mac.verify_slice(&expected).is_ok()
}

fn now_iso() -> String {
    chrono::Utc::now().to_rfc3339()
}

/// Translate a GitHub webhook (event name + raw JSON body) into a ThreadSpace
/// [`Event`]. Returns `None` for events we deliberately ignore (anything other
/// than a published release or a non-empty push).
pub fn parse_webhook(event_name: &str, body: &[u8]) -> Option<Event> {
    let payload: Value = serde_json::from_slice(body).ok()?;
    let repo = payload["repository"]["full_name"]
        .as_str()
        .map(str::to_string);

    match event_name {
        "release" => {
            if payload["action"].as_str() != Some("published") {
                return None;
            }
            let release = &payload["release"];
            let tag = release["tag_name"].as_str().unwrap_or("");
            let label = release["name"]
                .as_str()
                .filter(|name| !name.is_empty())
                .unwrap_or(tag);
            Some(Event {
                kind: "github.release".into(),
                actor: payload["sender"]["login"]
                    .as_str()
                    .unwrap_or("github")
                    .to_string(),
                title: Some(format!("released {label}")),
                url: release["html_url"].as_str().map(str::to_string),
                repo,
                post_id: None,
                created_at: now_iso(),
            })
        }
        "push" => {
            let commits = payload["commits"].as_array().map_or(0, Vec::len);
            if commits == 0 {
                return None;
            }
            let branch = payload["ref"]
                .as_str()
                .unwrap_or("")
                .rsplit('/')
                .next()
                .unwrap_or("");
            let plural = if commits == 1 { "commit" } else { "commits" };
            Some(Event {
                kind: "github.push".into(),
                actor: payload["pusher"]["name"]
                    .as_str()
                    .or_else(|| payload["sender"]["login"].as_str())
                    .unwrap_or("github")
                    .to_string(),
                title: Some(format!("pushed {commits} {plural} to {branch}")),
                url: payload["compare"].as_str().map(str::to_string),
                repo,
                post_id: None,
                created_at: now_iso(),
            })
        }
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sign(secret: &str, body: &[u8]) -> String {
        let mut mac = HmacSha256::new_from_slice(secret.as_bytes()).unwrap();
        mac.update(body);
        format!("sha256={}", hex::encode(mac.finalize().into_bytes()))
    }

    #[test]
    fn accepts_a_valid_signature() {
        let secret = "topsecret";
        let body = br#"{"hello":"world"}"#;
        assert!(verify_signature(secret, &sign(secret, body), body));
    }

    #[test]
    fn rejects_wrong_secret_and_malformed_headers() {
        let body = br#"{"hello":"world"}"#;
        assert!(!verify_signature("a", &sign("b", body), body));
        assert!(!verify_signature("a", "not-a-signature", body));
        assert!(!verify_signature("a", "sha256=zzzz", body));
    }

    #[test]
    fn parses_published_release() {
        let body = br#"{
            "action": "published",
            "release": {"tag_name": "v1.2.0", "name": "Big release", "html_url": "https://gh/r"},
            "repository": {"full_name": "alice/proj"},
            "sender": {"login": "alice"}
        }"#;
        let event = parse_webhook("release", body).expect("should parse");
        assert_eq!(event.kind, "github.release");
        assert_eq!(event.actor, "alice");
        assert_eq!(event.repo.as_deref(), Some("alice/proj"));
        assert_eq!(event.title.as_deref(), Some("released Big release"));
    }

    #[test]
    fn ignores_non_published_release_actions() {
        let body = br#"{"action": "created", "release": {}, "repository": {}}"#;
        assert!(parse_webhook("release", body).is_none());
    }

    #[test]
    fn parses_non_empty_push() {
        let body = br#"{
            "ref": "refs/heads/main",
            "commits": [{"id": "1"}, {"id": "2"}],
            "compare": "https://gh/compare",
            "repository": {"full_name": "alice/proj"},
            "pusher": {"name": "alice"}
        }"#;
        let event = parse_webhook("push", body).expect("should parse");
        assert_eq!(event.kind, "github.push");
        assert_eq!(event.title.as_deref(), Some("pushed 2 commits to main"));
    }

    #[test]
    fn ignores_empty_push_and_unknown_events() {
        let empty_push = br#"{"ref": "refs/heads/main", "commits": [], "repository": {}}"#;
        assert!(parse_webhook("push", empty_push).is_none());
        assert!(parse_webhook("issues", br#"{}"#).is_none());
    }
}
