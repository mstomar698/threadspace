use std::collections::HashSet;

use axum::{
    body::Bytes,
    extract::State,
    http::{HeaderMap, StatusCode},
    response::IntoResponse,
    Json,
};
use serde::Deserialize;
use serde_json::json;

use crate::event::{Delivery, Event};
use crate::github;
use crate::state::AppState;

pub async fn health() -> impl IntoResponse {
    Json(json!({ "status": "ok" }))
}

/// Body of the internal publish endpoint that the Django backend calls when it
/// has computed a fan-out audience (e.g. the author's followers).
#[derive(Deserialize)]
pub struct PublishRequest {
    #[serde(default)]
    pub audience: Option<Vec<String>>,
    pub event: Event,
}

/// Internal endpoint used by trusted services (Django) to inject events.
pub async fn publish(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(req): Json<PublishRequest>,
) -> impl IntoResponse {
    if let Some(expected) = &state.config.internal_token {
        let provided = headers
            .get("x-internal-token")
            .and_then(|v| v.to_str().ok());
        if provided != Some(expected.as_str()) {
            return (
                StatusCode::UNAUTHORIZED,
                Json(json!({ "detail": "invalid internal token" })),
            )
                .into_response();
        }
    }

    let audience = req
        .audience
        .map(|names| names.into_iter().collect::<HashSet<_>>());
    let receivers = state.hub.publish(Delivery {
        audience,
        event: req.event,
    });

    (
        StatusCode::ACCEPTED,
        Json(json!({ "receivers": receivers })),
    )
        .into_response()
}

/// GitHub webhook receiver. Verifies the signature (when a secret is set),
/// parses the payload, and broadcasts any interesting event.
pub async fn github_webhook(
    State(state): State<AppState>,
    headers: HeaderMap,
    body: Bytes,
) -> impl IntoResponse {
    if let Some(secret) = &state.config.webhook_secret {
        let signature = headers
            .get("x-hub-signature-256")
            .and_then(|v| v.to_str().ok())
            .unwrap_or_default();
        if !github::verify_signature(secret, signature, &body) {
            return (
                StatusCode::UNAUTHORIZED,
                Json(json!({ "detail": "invalid signature" })),
            )
                .into_response();
        }
    }

    let event_name = headers
        .get("x-github-event")
        .and_then(|v| v.to_str().ok())
        .unwrap_or_default();

    match github::parse_webhook(event_name, &body) {
        Some(event) => {
            let receivers = state.hub.publish(Delivery {
                audience: None,
                event,
            });
            (
                StatusCode::ACCEPTED,
                Json(json!({ "delivered": true, "receivers": receivers })),
            )
                .into_response()
        }
        None => (StatusCode::OK, Json(json!({ "delivered": false }))).into_response(),
    }
}
