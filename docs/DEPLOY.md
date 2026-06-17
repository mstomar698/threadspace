# Deployment (Oracle Always Free)

ThreadSpace runs as a single-VM Docker Compose stack behind Caddy (automatic
HTTPS). One Oracle **Ampere A1 (ARM)** Always Free instance comfortably hosts
Postgres + Redis + Django + the Rust gateway + Next.js.

```
Internet ─▶ Caddy :443 (auto-TLS)
              ├─ /static, /media     → files (shared volumes)
              ├─ /api, /admin        → Django (gunicorn)
              ├─ /ws, /webhooks/*     → Rust realtime gateway
              └─ everything else     → Next.js
            Postgres + Redis (private network only)
```

Files involved: [`docker-compose.prod.yml`](../docker-compose.prod.yml),
[`deploy/Caddyfile`](../deploy/Caddyfile),
[`.env.production.example`](../.env.production.example),
[`deploy/deploy.sh`](../deploy/deploy.sh), and the
[`Deploy` workflow](../.github/workflows/deploy.yml).

---

## 1. Provision the VM (Oracle Cloud)

See **[ORACLE_DEPLOY.md](ORACLE_DEPLOY.md)** for the full Oracle guide: OCI CLI
setup, A1 capacity retries, SSH keys, and Console vs CLI provisioning.

Quick summary:

1. Create an **Ampere A1 / Ubuntu 24.04** instance (1–2 OCPU, 6–12 GB RAM).
2. Add an ingress rule in the VCN **security list** allowing TCP **22, 80, 443**
   from `0.0.0.0/0`.
3. SSH in and open the OS firewall (Oracle images ship with iptables rules):
   ```bash
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
   sudo netfilter-persistent save
   ```
4. Install Docker + Compose:
   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker "$USER" && newgrp docker
   ```

## 2. DNS (DuckDNS)

1. At <https://www.duckdns.org> create a subdomain, e.g. `threadspace`.
2. Set its IP to the VM's **public IP** (re-run whenever the IP changes; an
   hourly cron with DuckDNS's update URL keeps it current).
3. Your domain is then `threadspace.duckdns.org`.

## 3. Clone + configure

```bash
git clone https://github.com/mstomar698/threadspace.git
cd threadspace
cp .env.production.example .env.production
```

Edit `.env.production`:

- `DOMAIN=threadspace.duckdns.org`
- Generate each secret: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
  - `SECRET_KEY`, `POSTGRES_PASSWORD`, `INTERNAL_TOKEN`, `GITHUB_WEBHOOK_SECRET`
- `GITHUB_OAUTH_CLIENT_ID` / `GITHUB_OAUTH_CLIENT_SECRET` from your production
  OAuth App (see step 5).

## 4. First deploy

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Caddy obtains a certificate automatically (needs ports 80/443 open and DNS
pointing at the VM). Then create an admin user:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Visit `https://<DOMAIN>` and `https://<DOMAIN>/admin/`.

## 5. GitHub OAuth (production)

In your OAuth App (<https://github.com/settings/developers>) either reuse the
existing app or create a prod one, and set:

- **Homepage URL**: `https://<DOMAIN>`
- **Authorization callback URL**: `https://<DOMAIN>/github/callback`

This single callback URL serves both "Sign in with GitHub" (from the login and
register pages) and "Connect GitHub" (from Settings).

Put the client ID/secret in `.env.production` and redeploy.

## 6. GitHub webhooks (release/push activity)

For any repo (or org) you want live activity from, add a webhook:

- **Payload URL**: `https://<DOMAIN>/webhooks/github`
- **Content type**: `application/json`
- **Secret**: the `GITHUB_WEBHOOK_SECRET` from `.env.production`
- **Events**: Pushes and Releases

## 7. Continuous deployment (GitHub Actions)

The [`Deploy` workflow](../.github/workflows/deploy.yml) SSHes into the VM and
rebuilds on every push to `main`. Add these repo secrets
(Settings -> Secrets and variables -> Actions):

| Secret           | Value                                             |
| ---------------- | ------------------------------------------------- |
| `DEPLOY_HOST`    | VM public IP / hostname                           |
| `DEPLOY_USER`    | SSH user (e.g. `ubuntu`)                          |
| `DEPLOY_SSH_KEY` | private key (its public half in `authorized_keys`)|
| `DEPLOY_PATH`    | absolute path to the repo on the VM               |

Generate a deploy key on your machine, add the public half to the VM:

```bash
ssh-keygen -t ed25519 -f deploy_key -N ""
ssh-copy-id -i deploy_key.pub <user>@<vm-ip>   # or append to ~/.ssh/authorized_keys
# paste the contents of deploy_key (private) into the DEPLOY_SSH_KEY secret
```

After that, `git push origin main` deploys automatically. You can also deploy
manually on the VM with `./deploy/deploy.sh`.

## Operations

```bash
# Logs
docker compose -f docker-compose.prod.yml logs -f
# Restart one service
docker compose -f docker-compose.prod.yml restart backend
# DB backup
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U threadspace threadspace > backup-$(date +%F).sql
```

## Notes / follow-ups

- **Access tokens** for connected GitHub accounts are stored in plaintext in the
  DB. Before going wide, encrypt them at rest (e.g. a Fernet-wrapped field).
- Media lives on a local Docker volume. Back up the `media` volume (or move to
  object storage) if uploads matter.
- The free ARM instance is reclaimable by Oracle if idle; keep some activity or
  upgrade to a paid shape for guaranteed uptime.
