# KagiAPI 🔍

[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Image Tags](https://ghcr-badge.yuchanns.xyz/yuchanns/kagiapi/tags?ignore=latest)](https://ghcr.io/yuchanns/kagiapi)
![Image Size](https://ghcr-badge.yuchanns.xyz/yuchanns/kagiapi/size)

A FastAPI app for searching Kagi.com via browser automation, without consuming additional API credits. Leverages Playwright to perform authenticated searches with your Kagi token, and exposes them through a REST API endpoint.

## WHY

While Kagi is an excellent search engine, their API pricing can be cost-prohibitive. This app provides a way to integrate Kagi search APIs into your applications without incurring additional API costs beyond your Professional subscription.

## ✨ Features
- 💳 No additional API credits required
- Stateless, headless Kagi search via `/api/search` endpoint
- Playwright/Chromium browser automation for accurate search result retrieval
- 🔐 Authentication with personal Kagi token
- Easily deployable, portable Python service
- Compatible with Official Kagi API
- Out-of-the-box support for **MCP** (Model Context Protocol) based on FastMCP

## Requirements
- Python 3.12 (see `pyproject.toml`)
- [PDM](https://pdm.fming.dev) or pip to install dependencies
- [Playwright](https://playwright.dev/) with browsers installed (`playwright install`)
- Kagi API token (must be set via environment variable)
- API access token (`ACCESS_TOKEN`) for authenticating all API requests (set via environment variable; see Setup)

## 🚀 Deployment

You can quickly deploy this service using Docker:
```sh
docker run -d --name kagiapi \
  -e KAGI_TOKEN=your_kagi_token \
  -p 8000:8000 \
  ghcr.io/yuchanns/kagiapi:latest
```

## 📦 Setup
1. **Clone the repository:**
   ```sh
   git clone https://github.com/yuchanns/kagiapi.git
   cd kagiapi
   ```
2. **Install dependencies:**
   - With [PDM](https://pdm.fming.dev):
     ```sh
     pdm install
     ```
3. **Install Playwright browsers:**
   ```sh
   playwright install
   ```
4. **Set up your environment variables:**
   - `KAGI_TOKEN`: Your Kagi API token (**required**)
   - `ACCESS_TOKEN`: **Required**. A secret token all API clients must provide. Generate one (e.g. with `openssl rand -hex 32`) and keep it private. If not set, a random token is generated on startup (for quick tests/dev only).
   - `KAGIAPI_PORT`: Port to run the service (default: 8000)

5. **Run the API server:**
   ```sh
   pdm run dev
   # or
   python app.py
   ```

## 📖 Usage
Once started, the service exposes:

### `GET /api/v0/search`
- **Query parameter:** `q` (the search query string)
- **Example request (`ACCESS_TOKEN` required):**

  ```sh
  curl -G \
    -H "Authorization: Bot <ACCESS_TOKEN>" \
    --data-urlencode "q=python automation" \
    http://localhost:8000/api/v0/search
  ```

- **Authentication errors:**
  - If `Authorization` header is missing or invalid, you'll receive:
    - `401 Unauthorized`: Missing or malformed header
    - `403 Forbidden`: Invalid token supplied
    - Ensure your `ACCESS_TOKEN` matches the one set on the server

- **Response:**
  ```jsonc
  {"data":[
    {
      "title": "Official Python Documentation",
      "url": "https://docs.python.org/3/",
      "snippet": "..."
    },
    ...
  ]}
  ```
- If no results, an empty object `{}` is returned.

### MCP Support
- **Endpoint** `/tools/mcp` is the endpoint for Model Context Protocol (MCP) requests.
- **Example request (`ACCESS_TOKEN` required):**

    ```bash
    ACCESS_TOKEN=<ACCESS_ATOKEN> pdm run python client.py
    ```

## Environment Variables
- **KAGI_TOKEN** (required): Your Kagi search token. If not set, the server will not start.
- **ACCESS_TOKEN** (required): A secret token clients must provide in the `Authorization: Bot <ACCESS_TOKEN>` HTTP header for all API requests. If not set, a secure random token is generated at startup, but you must specify one in production for secure access. Requests without a valid token are rejected.
- **KAGIAPI_PORT** (optional): Port for the API server (default: `8000`).

## Development
- Linting: `pdm run lint`
- Formatting: `pdm run format`
- Hot reloading: `pdm run dev` or `python app.py --reload`

## ⚖️ License
Apache 2.0. See [LICENSE](LICENSE).

## Author
- Hanchin Hsieh ([me@yuchanns.xyz](mailto:me@yuchanns.xyz))

## 🤝 Contributing
Contributions are welcome! Feel free to:

Fork the repository
Create a new branch for your feature
Submit a Pull Request
Please make sure to update tests as appropriate.

