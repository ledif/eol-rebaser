Name:           eol-rebaser
Version:        0.1.2
Release:        1%{?dist}
Summary:        Automatically rebase bootc systems when images reach end of life

License:        Apache-2.0
URL:            https://github.com/ledif/eol-rebaser
Source0:        https://github.com/ledif/eol-rebaser/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-pip
BuildRequires:  python3-build
BuildRequires:  python3-wheel
BuildRequires:  systemd-rpm-macros

Requires:       python3
Requires:       python3-pyyaml >= 6.0
Requires:       bootc
Requires:       sudo

%description
EOL Rebaser automatically detects when a bootc container image has reached
end of life (EOL) and rebases the system to a supported alternative image.
This ensures users continue to receive updates and security patches without
manual intervention.

This package provides the core eol-rebaser tool. Configuration files and
systemd service units should be provided by downstream distributions.

%prep
%autosetup -n %{name}-%{version}

%build
%pyproject_build

%install
%pyproject_install
%pyproject_save_files eol_rebaser

# Install systemd service files
install -Dm644 systemd/eol-rebaser.service %{buildroot}%{_unitdir}/eol-rebaser.service
install -Dm644 systemd/eol-rebaser.timer %{buildroot}%{_unitdir}/eol-rebaser.timer

# Create configuration directory (but don't install configs - downstream responsibility)
install -dm755 %{buildroot}%{_datadir}/eol-rebaser
install -dm755 %{buildroot}%{_datadir}/eol-rebaser/migrations.yaml.d

%post
%systemd_post eol-rebaser.timer

%preun
%systemd_preun eol-rebaser.timer

%postun
%systemd_postun_with_restart eol-rebaser.timer

%files -f %{pyproject_files}
%license LICENSE
%doc README.md
%{_unitdir}/eol-rebaser.service
%{_unitdir}/eol-rebaser.timer
%dir %{_datadir}/eol-rebaser
%dir %{_datadir}/eol-rebaser/migrations.yaml.d

%changelog
* Mon Jul 28 2025 Adam Fidel <adam@fidel.cloud> - 0.1.0-1
- Initial package