use std::env;

/// Runtime configuration, read from the environment (12-factor style).
#[derive(Clone, Debug)]
pub struct Config {
    /// Address the HTTP/WebSocket server binds to, e.g. `0.0.0.0:8080`.
    pub bind_addr: String,
    /// Shared secret for verifying GitHub webhook signatures. When unset,
    /// signature verification is skipped (useful for local development only).
    pub webhook_secret: Option<String>,
    /// Token required on the internal publish endpoint. When unset, the
    /// endpoint is unauthenticated (local development only).
    pub internal_token: Option<String>,
    /// Optional Redis URL for cross-instance fan-out (requires the `redis`
    /// build feature). When unset, an in-memory broadcast hub is used.
    pub redis_url: Option<String>,
}

fn non_empty(key: &str) -> Option<String> {
    env::var(key).ok().filter(|value| !value.trim().is_empty())
}

impl Config {
    pub fn from_env() -> Self {
        let host = env::var("HOST").unwrap_or_else(|_| "0.0.0.0".to_string());
        let port = env::var("PORT").unwrap_or_else(|_| "8080".to_string());
        Self {
            bind_addr: format!("{host}:{port}"),
            webhook_secret: non_empty("GITHUB_WEBHOOK_SECRET"),
            internal_token: non_empty("INTERNAL_TOKEN"),
            redis_url: non_empty("REDIS_URL"),
        }
    }
}
