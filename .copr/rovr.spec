Name:           rovr
Version:        0.10.0rc1
Release:        1%{?dist}
Summary:        Stylish, batteries-included terminal file manager

License:        MIT
URL:            https://github.com/NSPC911/rovr
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  pyproject-rpm-macros
BuildRequires:  python3-devel

%generate_buildrequires
%pyproject_buildrequires

%description
rovr is a stylish terminal file manager built with Textual.

%prep
%autosetup -n %{name}-%{version}

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files rovr

%files -f %{pyproject_files}
%license LICENSE
%doc README.md

%changelog
* Sat Jul 31 2026 NSPC911 <87571998+NSPC911@users.noreply.github.com> - 0.10.0-1
- Initial COPR packaging setup
