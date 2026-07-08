BACKEND_DIR := backend
# Paths are relative to BACKEND_DIR (used after "cd backend")
PYTHON  := .venv/bin/python
UVICORN := .venv/bin/uvicorn

# ── Infrastructure ─────────────────────────────────────────────────────────────

infra-up:
	podman compose -f compose.infra.yml up -d

infra-down:
	podman compose -f compose.infra.yml down

infra-logs:
	podman compose -f compose.infra.yml logs -f

# ── Backend ────────────────────────────────────────────────────────────────────

# Run the backend accessible to devices on the local network (ESP32, other machines).
# Binds to 0.0.0.0 so the Mac's LAN IP (e.g. 192.168.1.150) is reachable.
dev:
	cd $(BACKEND_DIR) && $(UVICORN) app.main:app \
		--host 0.0.0.0 \
		--port 8000 \
		--reload \
		--log-level info

# Run only for local browser testing (not reachable from ESP32).
dev-local:
	cd $(BACKEND_DIR) && $(UVICORN) app.main:app \
		--host 127.0.0.1 \
		--port 8000 \
		--reload

migrate:
	cd $(BACKEND_DIR) && $(PYTHON) -m alembic upgrade head

migrate-new:
	cd $(BACKEND_DIR) && $(PYTHON) -m alembic revision --autogenerate -m "$(msg)"

# ── Tests ──────────────────────────────────────────────────────────────────────

test:
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest \
		--ignore=tests/integration/test_mqtt_ingestion.py \
		-q

test-v:
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest \
		--ignore=tests/integration/test_mqtt_ingestion.py \
		-v

test-mqtt:
	cd $(BACKEND_DIR) && RUN_MQTT_INTEGRATION_TESTS=1 \
		$(PYTHON) -m pytest tests/integration/test_mqtt_ingestion.py -v

# ── Utilities ──────────────────────────────────────────────────────────────────

# Print the Mac's current LAN IP — use this address in ESP32 firmware.
lan-ip:
	@ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null

.PHONY: infra-up infra-down infra-logs dev dev-local migrate migrate-new test test-v test-mqtt lan-ip
