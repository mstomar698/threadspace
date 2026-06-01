use std::sync::Arc;

use crate::config::Config;
use crate::hub::Hub;

/// Shared application state handed to every request handler.
#[derive(Clone)]
pub struct AppState {
    pub config: Arc<Config>,
    pub hub: Hub,
}
