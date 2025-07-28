# eol-rebaser

A utility to automatically rebase bootc systems when its currently booted image stream reaches end-of-life (EOL).

## Usage

```bash
eol-rebaser --check
eol-rebaser --migrate
```

### Systemd Service

Systemd service and timer units are provided. The service can be enabled and will run periodically to check for required migrations:


```bash
sudo systemctl status eol-rebaser.timer
sudo systemctl enable eol-rebaser.timer
```

## Configuration

The main configuration file should be located at `/usr/share/eol-rebaser/migrations.conf`, with drop-in overrides supported in `/usr/share/eol-rebaser/migrations.conf.d/`.


### Example Configuration

```yaml
migrations:
  - name: "Aurora ASUS to HWE Migration"
    from_pattern: "ghcr\\.io/ublue-os/(aurora(?:-dx)?)-asus(-nvidia(?:-open)?)?:(.+)"
    to_image: "ghcr.io/ublue-os/\\1-hwe\\2:\\3"
    reason: "ASUS-specific images are deprecated. Migrating to HWE images which include all necessary drivers."
    effective_date: "2025-10-15"

  - name: "Aurora Surface to HWE Migration"
    from_pattern: "ghcr\\.io/ublue-os/(aurora(?:-dx)?)-surface(-nvidia(?:-open)?)?:(.+)"
    to_image: "ghcr.io/ublue-os/\\1-hwe\\2:\\3"
    reason: "Surface-specific images are deprecated. Migrating to HWE images which include all necessary drivers."
    effective_date: "2025-10-15"
```

### Regex Substitution

The `to_image` field supports regex substitution using capture groups from `from_pattern`. This allows for sophisticated transformations that preserve image variants and tags:

**Examples:**
- `aurora-dx-surface-nvidia-open:stable-daily` → `aurora-dx-hwe-nvidia-open:stable-daily`
- `aurora-asus-nvidia:latest` → `aurora-hwe-nvidia:latest`
- `aurora-surface:42` → `aurora-hwe:42`

The regex patterns use capture groups `()` to extract parts of the source image, which are then substituted into the target using `\\1`, `\\2`, etc.


## Development

### Setup

```bash
uv sync --extra dev
uv run eol-rebaser --help
```

### Testing

```bash
uv run pytest
```