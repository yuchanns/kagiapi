# KagiAPI

A FastAPI app for searching Kagi.com via browser automation. Leverages Playwright to perform authenticated searches with your Kagi token, and exposes them through a REST API endpoint.

## Features
- Stateless, headless Kagi search via `/api/search` endpoint
- Playwright/Chromium browser automation for accurate search result retrieval
- Authentication with personal Kagi token
- Easily deployable, portable Python service

## Requirements
- Python 3.12 (see `pyproject.toml`)
- [PDM](https://pdm.fming.dev) or pip to install dependencies
- [Playwright](https://playwright.dev/) with browsers installed (`playwright install`)
- Kagi API token (must be set via environment variable)

## Setup
1. **Clone the repository:**
   ```sh
   git clone https://github.com/yuchanns/kagiflare.git
   cd kagiflare
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
   - `KAGIAPI_PORT`: Port to run the service (default: 8000)

5. **Run the API server:**
   ```sh
   pdm run dev
   # or
   python app.py
   ```

## Usage
Once started, the service exposes:

### `GET /api/search`
- **Query parameter:** `q` (the search query string)
- **Example request:**

  ```sh
  curl -G --data-urlencode "q=python automation" http://localhost:8000/api/search
  ```
- **Response:**
  ```json
  [
    {
      "title": "Official Python Documentation",
      "url": "https://docs.python.org/3/",
      "snippet": "..."
    },
    ...
  ]
  ```
- If no results, an empty object `{}` is returned.

## Environment Variables
- **KAGI_TOKEN** (required): Your Kagi search token. If not set, the server will not start.
- **KAGIAPI_PORT** (optional): Port for the API server (default: `8000`).

## Development
- Linting: `pdm run lint`
- Formatting: `pdm run format`
- Hot reloading: `pdm run dev` or `python app.py --reload`

## License
Apache 2.0. See [LICENSE](LICENSE).

## Author
- Hanchin Hsieh ([me@yuchanns.xyz](mailto:me@yuchanns.xyz))

