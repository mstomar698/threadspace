use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Query, State,
    },
    response::IntoResponse,
};
use futures::{SinkExt, StreamExt};
use serde::Deserialize;
use tokio::sync::broadcast::error::RecvError;

use crate::event::should_deliver;
use crate::state::AppState;

#[derive(Deserialize)]
pub struct WsParams {
    /// The connecting user's username. Used to target follower fan-out; when
    /// absent the client still receives broadcast events.
    #[serde(default)]
    pub user: Option<String>,
    /// When set, the client subscribes to a single room (e.g. a project's chat
    /// keyed by `owner/name`) and receives only that room's events.
    #[serde(default)]
    pub room: Option<String>,
}

pub async fn ws_handler(
    State(state): State<AppState>,
    Query(params): Query<WsParams>,
    upgrade: WebSocketUpgrade,
) -> impl IntoResponse {
    upgrade.on_upgrade(move |socket| handle_socket(socket, state, params.user, params.room))
}

async fn handle_socket(
    socket: WebSocket,
    state: AppState,
    user: Option<String>,
    room: Option<String>,
) {
    let (mut sender, mut receiver) = socket.split();
    let mut rx = state.hub.subscribe();

    let hello = serde_json::json!({ "type": "connected", "user": user, "room": room });
    if sender
        .send(Message::Text(hello.to_string().into()))
        .await
        .is_err()
    {
        return;
    }

    // Forward matching deliveries from the hub to this client.
    let mut send_task = tokio::spawn(async move {
        loop {
            match rx.recv().await {
                Ok(delivery) => {
                    if !should_deliver(&delivery, &user, &room) {
                        continue;
                    }
                    let Ok(text) = serde_json::to_string(&delivery.event) else {
                        continue;
                    };
                    if sender.send(Message::Text(text.into())).await.is_err() {
                        break;
                    }
                }
                // We fell behind; skip dropped messages rather than disconnect.
                Err(RecvError::Lagged(_)) => continue,
                Err(RecvError::Closed) => break,
            }
        }
    });

    // Drain inbound frames so we notice client disconnects (and answer pings).
    let mut recv_task = tokio::spawn(async move {
        while let Some(Ok(message)) = receiver.next().await {
            if matches!(message, Message::Close(_)) {
                break;
            }
        }
    });

    tokio::select! {
        _ = &mut send_task => recv_task.abort(),
        _ = &mut recv_task => send_task.abort(),
    }
}
