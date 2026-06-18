use tokio::sync::broadcast;

use crate::event::Delivery;

/// In-memory fan-out hub backed by a Tokio broadcast channel.
///
/// Every WebSocket connection holds a [`broadcast::Receiver`]; publishers send
/// a [`Delivery`] which each receiver filters against its own subscription.
/// This keeps fan-out lock-free and scales to thousands of connections on a
/// single instance. For multiple instances, enable the `redis` feature so an
/// external Redis channel feeds this hub.
#[derive(Clone)]
pub struct Hub {
    tx: broadcast::Sender<Delivery>,
}

impl Hub {
    pub fn new(capacity: usize) -> Self {
        let (tx, _rx) = broadcast::channel(capacity);
        Self { tx }
    }

    pub fn subscribe(&self) -> broadcast::Receiver<Delivery> {
        self.tx.subscribe()
    }

    /// Publish a delivery to all subscribers. Returns the number of live
    /// receivers it was queued to (0 when nobody is connected).
    pub fn publish(&self, delivery: Delivery) -> usize {
        self.tx.send(delivery).unwrap_or(0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::event::Event;

    fn sample_event() -> Event {
        Event {
            kind: "post.created".into(),
            actor: "alice".into(),
            title: None,
            url: None,
            repo: None,
            post_id: None,
            created_at: String::new(),
        }
    }

    #[tokio::test]
    async fn subscribers_receive_published_deliveries() {
        let hub = Hub::new(16);
        let mut rx = hub.subscribe();
        let queued = hub.publish(Delivery {
            audience: None,
            room: None,
            event: sample_event(),
        });
        assert_eq!(queued, 1);
        let received = rx.recv().await.unwrap();
        assert_eq!(received.event.actor, "alice");
    }

    #[test]
    fn publish_without_subscribers_is_a_noop() {
        let hub = Hub::new(16);
        assert_eq!(
            hub.publish(Delivery {
                audience: None,
                room: None,
                event: sample_event(),
            }),
            0
        );
    }
}
