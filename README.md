# RelaySMS Gateway Client for Twilio

Forwards SMS received on a Twilio number to HTTP endpoints.

## Endpoints

### `POST /twilio-sms`

Twilio calls this for each SMS.

```http
POST /twilio-sms
Content-Type: application/x-www-form-urlencoded
X-Twilio-Signature: <signature>

From=%2B237670000000&Body=<text>&MessageSid=...
```

- Each `FORWARD_URLS_JSON` URL receives:

  ```json
  {
    "address": "<HMAC-SHA256 of From under SENDER_HASH_KEY>",
    "dialing_code": "237",
    "iso": "CM",
    "text": "<Body>",
    "tag": "<FORWARD_TAG or null>"
  }
  ```

  `dialing_code` and `iso` are `null` when `From` isn't a phone number.
- Each `FORWARD_URLS_RAW` URL receives Twilio's form unchanged.

> [!WARNING]
> `FORWARD_TAG` goes to every JSON URL, and raw URLs get the sender's phone number. List only receivers you trust with both.

| Status | Body |
|---|---|
| `200` | `<Response />` (empty TwiML, no reply SMS) |
| `400` | `{"detail": "Missing required field 'From' or 'Body'."}` |
| `403` | `{"detail": "Invalid Twilio signature."}` |
| `502` | `{"detail": "Forwarding failed."}` (at least one URL failed; the log names it) |

> [!NOTE]
> Every URL is tried before Twilio gets its reply. Twilio doesn't retry, so a failed delivery is recorded only in this service's log and Twilio's error log.

### `GET /health`

| Status | Body |
|---|---|
| `200` | `{"status": "ok"}` |

## Install

As root, Python 3.12+:

- Clone:

  ```bash
  git clone https://github.com/smswithoutborders/RelaySMS-GatewayClient-Twilio.git /opt/relaysms/relaysms-gatewayclient-twilio
  cd /opt/relaysms/relaysms-gatewayclient-twilio
  ```

- Install:

  ```bash
  python3 -m venv venv && venv/bin/pip install -r requirements.txt
  ```

- Configure (variables in [template.env](template.env)):

  ```bash
  id relaysms || useradd --system --no-create-home relaysms
  sed "s/^SENDER_HASH_KEY=$/SENDER_HASH_KEY=$(openssl rand -hex 32)/" template.env >.env
  vim .env
  chown root:relaysms .env && chmod 640 .env
  ```

> [!IMPORTANT]
> Keep a copy of `SENDER_HASH_KEY`. A new key gives every sender a new `address`.

- Start:

  ```bash
  cp deploy/relaysms-gatewayclient-twilio.service /etc/systemd/system/
  systemctl daemon-reload && systemctl enable --now relaysms-gatewayclient-twilio
  ```

- Check (startup fails listing any invalid setting):

  ```bash
  journalctl -u relaysms-gatewayclient-twilio
  ```

### nginx

> [!IMPORTANT]
> Twilio signs the exact URL it calls. nginx must pass the original `Host` and scheme, and the URL in Twilio's console must match the one nginx serves.

- Save as `/etc/nginx/sites-available/<domain>.conf`:

  ```nginx
  server {
      listen 80;
      listen [::]:80;
      server_name <domain>;
      server_tokens off;

      proxy_set_header Host              $host;
      proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;

      location / {
          proxy_pass http://127.0.0.1:16100;
      }
  }
  ```

- Enable and add HTTPS:

  ```bash
  ln -s /etc/nginx/sites-available/<domain>.conf /etc/nginx/sites-enabled/
  nginx -t && systemctl reload nginx
  certbot --nginx -d <domain>
  ```

### Twilio

- Number > Messaging > A message comes in: `https://<domain>/twilio-sms`, `HTTP POST`

## Development

- `make setup`: venv, dev tools, git hooks, and a `.env` with a new `SENDER_HASH_KEY` if there isn't one; safe to rerun
- `make test`, or `make coverage` for a coverage report
- `make check`: lint, format and type checks
- `make run`: serve locally; needs a filled-in `.env`

## License

[GPL-3.0](LICENSE.md)
