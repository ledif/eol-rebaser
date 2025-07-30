# eol-rebaser

Utility to automatically rebase bootc systems when its currently booted image stream reaches end-of-life (EOL).

## Usage

```
usage: eol-rebaser [-h] [--check] [--migrate] [--dry-run] [--config CONFIG] [--force] [--verbose] [--no-sudo]
                   [--version]

Automatically rebase bootc systems when images reach EOL

options:
  -h, --help       show this help message and exit
  --check          Check if current image needs migration
  --migrate        Perform migration if needed
  --dry-run        Show what would be done without executing
  --config CONFIG  Path to configuration file (default: /usr/share/eol-rebaser/migrations.yaml)
  --force          Force migration even if not scheduled yet
  --verbose, -v    Enable verbose logging
  --no-sudo        Don't use sudo for bootc commands (requires root)
  --version        show program's version number and exit

Examples:
  eol-rebaser --check              Check if migration is needed
  eol-rebaser --migrate            Perform migration if needed
  eol-rebaser --dry-run            Show what would be done without executing
  eol-rebaser --config /path/to/config.yaml  Use custom config file
```

### Systemd Service

Systemd service and timer units are provided. The service can be enabled and will run periodically to check for required migrations:


```bash
sudo systemctl status eol-rebaser.timer
sudo systemctl enable eol-rebaser.timer
```

## Configuration

The main configuration file should be located at `/usr/share/eol-rebaser/migrations.yaml`, with drop-in overrides supported in `/usr/share/eol-rebaser/migrations.yaml.d/`.


### Example Configuration

```yaml
migrations:
  - name: "Aurora ASUS to HWE Migration"
    from_pattern: "ghcr\\.io/ublue-os/(aurora(?:-dx)?)-asus(-nvidia(?:-open)?)?:(.+)"
    to_image: "ghcr.io/ublue-os/\\1-hwe\\2:\\3"
    reason: "ASUS-specific images are deprecated. Migrating to HWE images which include hardware support."
    effective_date: "2025-10-15"

  - name: "Aurora Surface to HWE Migration"
    from_pattern: "ghcr\\.io/ublue-os/(aurora(?:-dx)?)-surface(-nvidia(?:-open)?)?:(.+)"
    to_image: "ghcr.io/ublue-os/\\1-hwe\\2:\\3"
    reason: "Surface-specific images are deprecated. Migrating to HWE images which include hardware support."
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
