//! Optional Redis pub/sub bridge for multi-instance fan-out.
//!
//! When several gateway instances run behind a load balancer, a WebSocket
//! client is connected to only one of them. Publishing events to a shared
//! Redis channel and having every instance subscribe to it lets any instance
//! deliver to its own connected clients. Enable with `--features redis` and set
//! `REDIS_URL`.

use futures::StreamExt;

use crate::event::{Delivery, Event};
use crate::hub::Hub;

const CHANNEL: &str = "threadspace:events";

/// Spawn the background subscriber task. Events published to the Redis channel
/// are forwarded into the local hub as broadcast deliveries.
pub fn spawn(url: String, hub: Hub) {
    tokio::spawn(async move {
        match run(url, hub).await {
            Ok(()) => tracing::warn!("redis bridge ended"),
            Err(err) => tracing::error!("redis bridge error: {err}"),
        }
    });
}

async fn run(url: String, hub: Hub) -> redis::RedisResult<()> {
    let client = redis::Client::open(url)?;
    let mut pubsub = client.get_async_pubsub().await?;
    pubsub.subscribe(CHANNEL).await?;
    tracing::info!("subscribed to redis channel '{CHANNEL}'");

    let mut stream = pubsub.on_message();
    while let Some(message) = stream.next().await {
        let payload: String = message.get_payload()?;
        match serde_json::from_str::<Event>(&payload) {
            Ok(event) => {
                hub.publish(Delivery {
                    audience: None,
                    room: None,
                    event,
                });
            }
            Err(err) => tracing::warn!("dropping malformed redis event: {err}"),
        }
    }
    Ok(())
}
