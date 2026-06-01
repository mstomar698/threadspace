mod config;
mod event;
mod github;
mod handlers;
mod hub;
mod state;
mod ws;

#[cfg(feature = "redis")]
mod redis_bridge;

use std::sync::Arc;

use axum::{
    routing::{get, post},
    Router,
};
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;
use tracing_subscriber::EnvFilter;

use crate::config::Config;
use crate::hub::Hub;
use crate::state::AppState;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .init();

    let config = Arc::new(Config::from_env());
    let hub = Hub::new(1024);
    let state = AppState {
        config: Arc::clone(&config),
        hub: hub.clone(),
    };

    #[cfg(feature = "redis")]
    if let Some(url) = config.redis_url.clone() {
        redis_bridge::spawn(url, hub.clone());
    }
    #[cfg(not(feature = "redis"))]
    if config.redis_url.is_some() {
        tracing::warn!("REDIS_URL is set but the binary was built without the `redis` feature");
    }

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = Router::new()
        .route("/health", get(handlers::health))
        .route("/ws", get(ws::ws_handler))
        .route("/internal/publish", post(handlers::publish))
        .route("/webhooks/github", post(handlers::github_webhook))
        .layer(TraceLayer::new_for_http())
        .layer(cors)
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(&config.bind_addr)
        .await
        .unwrap_or_else(|err| panic!("failed to bind {}: {err}", config.bind_addr));

    tracing::info!("realtime gateway listening on {}", config.bind_addr);
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .expect("server error");
}

async fn shutdown_signal() {
    let _ = tokio::signal::ctrl_c().await;
    tracing::info!("shutting down");
}
