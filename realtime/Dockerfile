# Rust realtime gateway. Multi-stage: compile with the full toolchain, then
# ship just the binary on a slim Debian runtime.
FROM rust:1 AS builder
WORKDIR /app

# Cache dependency compilation: build against a stub main, then the real source.
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs \
    && cargo build --release --features redis \
    && rm -rf src
COPY src ./src
RUN touch src/main.rs && cargo build --release --features redis

FROM debian:stable-slim AS runtime
WORKDIR /app
COPY --from=builder /app/target/release/threadspace-realtime /usr/local/bin/threadspace-realtime
EXPOSE 8080
CMD ["threadspace-realtime"]
