# Oracle Cloud deployment guide

Step-by-step guide for provisioning an **Oracle Always Free Ampere A1** VM and
deploying ThreadSpace. For the application stack (Docker Compose, Caddy, env
vars, GitHub OAuth, CI), see [DEPLOY.md](DEPLOY.md).

---

## Overview

| Item | Choice |
| ---- | ------ |
| Region | `ap-mumbai-1` (or your home region) |
| Shape | `VM.Standard.A1.Flex` (ARM, Always Free) |
| OS | Canonical Ubuntu 24.04 aarch64 |
| Size | 1–2 OCPU, 6–12 GB RAM (smaller lands capacity more easily) |
| DNS | DuckDNS subdomain (free HTTPS via Caddy) |
| Deploy | GitHub Actions SSH deploy on push to `main` |

---

## Part 1 — Oracle account and region

1. Sign up at [oracle.com/cloud/free](https://www.oracle.com/cloud/free/).
2. Pick a **home region** at signup (cannot change later). Example: Mumbai →
   `ap-mumbai-1`.
3. Note your **tenancy OCID** (Profile → Tenancy) if using the CLI.

---

## Part 2 — OCI CLI (Windows)

### Install

On Windows, enable long paths first (requires **Admin PowerShell**):

```powershell
New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' `
  -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force
```

Then install:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command `
  "iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.ps1'))"
```

Close and reopen PowerShell. Verify:

```powershell
oci --version
```

Default install path: `C:\Users\<you>\bin\oci.exe`.

### Log in (browser session)

```powershell
oci session authenticate
```

- Enter your region (e.g. `ap-mumbai-1`).
- Approve in the browser.
- Accept profile name `DEFAULT`.

Test:

```powershell
oci iam region list --profile DEFAULT --auth security_token --output table
```

Config is written to `C:\Users\<you>\.oci\config`.

**Session tokens expire (~1 hour).** Refresh before long operations:

```powershell
oci session refresh --profile DEFAULT
```

For unattended scripts, switch to API-key auth later (`oci setup config`).

### Suppress permission warnings (optional)

```powershell
$Env:OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING = "True"
```

Or repair permissions:

```powershell
oci setup repair-file-permissions --file C:\Users\<you>\.oci\config
```

---

## Part 3 — SSH key for the VM

Generate a deploy key (no passphrase so GitHub Actions can use it):

```powershell
ssh-keygen -t ed25519 -f $HOME\.ssh\threadspace_deploy -N '""' -C threadspace-deploy
```

- **Public key** (`threadspace_deploy.pub`) → injected into the VM at launch.
- **Private key** (`threadspace_deploy`) → GitHub secret `DEPLOY_SSH_KEY`.

---

## Part 4 — Provision networking + VM

You can use the **web Console** (Compute → Create instance, wizard creates VCN)
or the **CLI** below.

### Option A — Console (simplest)

1. **Compute → Instances → Create instance**
2. Name: `threadspace`
3. Image: **Canonical Ubuntu 24.04** (aarch64)
4. Shape: **Ampere** `VM.Standard.A1.Flex` — start with **1 OCPU / 6 GB**
5. Networking: create VCN + public subnet, assign public IPv4
6. SSH key: paste contents of `threadspace_deploy.pub`
7. Create

Then open **VCN → Security List → Ingress**: allow TCP **22, 80, 443** from
`0.0.0.0/0`.

Copy the **Public IP** from the instance page.

### Option B — CLI (scriptable)

Set env for every command:

```powershell
$env:OCI_CLI_AUTH = "security_token"
$env:OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING = "True"
```

Discover IDs (replace `<TENANCY_OCID>`):

```powershell
# Availability domain
oci iam availability-domain list --compartment-id <TENANCY_OCID> --output table

# Latest Ubuntu 24.04 ARM image
oci compute image list --compartment-id <TENANCY_OCID> `
  --operating-system "Canonical Ubuntu" --operating-system-version "24.04" `
  --shape VM.Standard.A1.Flex --sort-by TIMECREATED --sort-order DESC `
  --query 'data[0].{name:"display-name",id:id}' --output table
```

Create VCN, internet gateway, routes, security list (22/80/443), subnet, then
launch the instance. A full provisioning script lives in the repo at
[`deploy/oci-provision.ps1`](../deploy/oci-provision.ps1) (adjust OCIDs for
your tenancy).

Launch example (fill in OCIDs):

```powershell
oci compute instance launch `
  --compartment-id <TENANCY_OCID> `
  --availability-domain "<AD-NAME>" `
  --shape VM.Standard.A1.Flex `
  --shape-config '{"ocpus":1,"memoryInGBs":6}' `
  --image-id <UBUNTU-24.04-ARM-IMAGE-OCID> `
  --subnet-id <SUBNET-OCID> `
  --assign-public-ip true `
  --display-name threadspace `
  --ssh-authorized-keys-file $HOME\.ssh\threadspace_deploy.pub `
  --wait-for-state RUNNING
```

Public IP:

```powershell
oci compute instance list-vnics --instance-id <INSTANCE-OCID> `
  --query 'data[0]."public-ip"' --raw-output
```

---

## Part 5 — A1 capacity (“Out of host capacity”)

Always Free **A1** hosts are heavily contended. Common errors:

| Error | Meaning |
| ----- | ------- |
| `Out of host capacity` | No free A1 host in that fault domain — retry later |
| `TooManyRequests` | Launch API rate limit — wait 30–60 min, retry slowly |

**Tips:**

1. Try **1 OCPU / 6 GB** before 2/12.
2. Retry across **fault domains** (`FAULT-DOMAIN-1`, `-2`, `-3`).
3. Use a **gentle retry loop** (one attempt every ~5 minutes), not rapid fire.
4. **Upgrade to Pay As You Go** (still free A1 quota) — capacity is usually
   available immediately; trial accounts get lowest priority.
5. Try off-peak hours or a less busy home region (only if you can sign up there).

Persistent retry script (run locally, leave open):

```powershell
powershell -ExecutionPolicy Bypass -File $HOME\threadspace-launch-retry.ps1
```

When it prints `PUBLIC_IP = ...`, continue to Part 6.

---

## Part 6 — VM bootstrap

SSH in:

```powershell
ssh -i $HOME\.ssh\threadspace_deploy ubuntu@<PUBLIC_IP>
```

Open OS firewall (Oracle Ubuntu images use iptables):

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

Install Docker:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
docker version
```

---

## Part 7 — DuckDNS

1. Create a subdomain at [duckdns.org](https://www.duckdns.org) (e.g.
   `threadspace`).
2. Point it at the VM **public IP**.
3. Your `DOMAIN` is `threadspace.duckdns.org`.

Optional cron to keep IP updated if it changes:

```bash
echo '*/5 * * * * curl -s "https://www.duckdns.org/update?domains=threadspace&token=<TOKEN>&ip=" > /dev/null' | crontab -
```

---

## Part 8 — Deploy ThreadSpace

Follow [DEPLOY.md](DEPLOY.md) from **§3 Clone + configure** onward:

1. Clone repo on the VM
2. Copy `.env.production.example` → `.env.production`, set `DOMAIN` and secrets
3. `docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build`
4. `createsuperuser`
5. Update GitHub OAuth callback to `https://<DOMAIN>/settings/github/callback`
6. Add GitHub Actions secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`,
   `DEPLOY_PATH`

---

## Checklist (resume later)

- [ ] Oracle account + home region chosen
- [ ] OCI CLI installed and `oci session authenticate` works
- [ ] SSH key `~/.ssh/threadspace_deploy` generated
- [ ] VM running with public IP (A1 capacity landed)
- [ ] VCN security list: TCP 22, 80, 443 open
- [ ] OS firewall: 80, 443 open
- [ ] Docker installed on VM
- [ ] DuckDNS subdomain → public IP
- [ ] `.env.production` filled on VM
- [ ] First `docker compose -f docker-compose.prod.yml up -d --build`
- [ ] GitHub OAuth prod callback URL set
- [ ] GitHub Actions deploy secrets configured

---

## Current session notes (Mumbai tenancy)

Networking was partially provisioned via CLI before A1 capacity blocked the
instance launch:

- VCN `threadspace-vcn` (`10.0.0.0/16`)
- Public subnet `threadspace-subnet` (`10.0.1.0/24`)
- Internet gateway + default route
- Security list: ingress TCP 22, 80, 443

**Still needed:** launch the A1 instance into the existing subnet (or recreate
via Console wizard if you prefer a clean slate). Use the retry script in Part 5
once the rate-limit cooldown has passed.

---

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| `oci: command not found` | Reopen terminal; check `C:\Users\<you>\bin` on PATH |
| Auth errors after an hour | `oci session refresh --profile DEFAULT` |
| SSH refused | Check security list + instance is RUNNING |
| Caddy no certificate | DNS must point at VM; ports 80/443 reachable |
| Frontend can't reach API | Rebuild frontend with correct `NEXT_PUBLIC_*` / `DOMAIN` |

For app-level ops (logs, backups, redeploy), see [DEPLOY.md](DEPLOY.md).
