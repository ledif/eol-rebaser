Name:           eol-rebaser
Version:        0.1.1
Release:        1%{?dist}
Summary:        Automatically rebase bootc systems when images reach end of life

License:        Apache-2.0
URL:            https://github.com/ledif/eol-rebaser
Source0:        https://github.com/ledif/eol-rebaser/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-pip

Requires:       python3
Requires:       python3-pyyaml
Requires:       bootc

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
%py3_build

%install
%py3_install

# Create the main executable symlink for /usr/libexec
install -d %{buildroot}%{_libexecdir}
ln -s %{_bindir}/eol-rebaser %{buildroot}%{_libexecdir}/eol-rebaser

%files
%license LICENSE
%doc README.md

# Python package files
%{python3_sitelib}/eol_rebaser/
%{python3_sitelib}/eol_rebaser-*.egg-info/

# Executables
%{_bindir}/eol-rebaser
%{_libexecdir}/eol-rebaser

%changelog
* Mon Jul 28 2025 Adam Fidel <adam@fidel.cloud> - 0.1.0-1
- Initial package