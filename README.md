# eol-rebaser

A utility to automatically rebase bootc systems when its currently booted image stream reaches end-of-life (EOL).

## Usage

```bash
eol-rebaser --check
eol-rebaser --migrate
```

### Systemd Service

A service can be enabled and will run periodically to check for required migrations:

```bash
sudo systemctl status eol-rebaser
sudo systemctl enable eol-rebaser
```

## Configuration

The main configuration file is located at `/usr/share/eol-rebaser/migrations.conf`, with drop-in overrides supported in `/usr/share/eol-rebaser/migrations.conf.d/`.

### Example Configuration

```yaml
migrations:
  - name: "Aurora ASUS HWE to Standard HWE"
    from_pattern: "ghcr.io/ublue-os/aurora.*-asus:.*"
    to_image: "ghcr.io/ublue-os/aurora-dx"
    reason: "ASUS-specific images are deprecated."
    effective_date: "2025-10-15"

  - name: "Aurora Surface HWE to Standard HWE"
    from_pattern: "ghcr.io/ublue-os/aurora.*-surface:.*"
    to_image: "ghcr.io/ublue-os/aurora-dx"
    reason: "Surface-specific images are deprecated. Migrating to standard HWE image."
    effective_date: "2025-10-15"
```


## Development

### Setup

```bash
uv sync
uv run eol-rebaser --help
```

### Testing

```bash
uv run pytest
```