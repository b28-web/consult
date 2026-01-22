# 009-B: Ansible Inventory and Base Playbook

## Parent EP
[EP-009: Ansible Deployment](../enhancement_proposals/EP-009-ansible-deployment.md)

## Objective
Set up Ansible project structure and base server configuration playbook.

## Acceptance Criteria

- [x] `ansible/` directory with standard structure
- [x] Inventory files for dev and prod environments
- [x] `setup.yml` playbook configures fresh server
- [x] Creates `deploy` user with sudo access
- [x] Installs Python 3.12, uv, nginx, Doppler CLI
- [x] Configures UFW firewall (22, 80, 443)
- [x] `just ansible-setup ENV` runs the playbook

## Technical Details

### Directory Structure
```
ansible/
├── ansible.cfg
├── inventory/
│   ├── dev.yml
│   └── prod.yml
├── playbooks/
│   ├── setup.yml
│   └── deploy.yml (009-C)
├── roles/
│   ├── common/
│   ├── docker/  # for local reference, not used in prod
│   └── django/
└── group_vars/
    └── all.yml
```

### Inventory (dev.yml)
```yaml
all:
  hosts:
    django:
      ansible_host: "{{ lookup('env', 'DJANGO_SERVER_IP') }}"
      ansible_user: root  # initial, then deploy
```

### setup.yml tasks
1. Create deploy user
2. Add SSH authorized keys
3. Install apt packages
4. Install uv via official installer
5. Install Doppler CLI
6. Configure nginx base
7. Set up UFW firewall
8. Create /app directory

## Dependencies
- Pulumi outputs server IP
- SSH access as root (initial setup)

## Progress Log

### 2026-01-22
- Created `ansible/` directory structure with roles, inventory, playbooks
- Created `ansible.cfg` with sensible defaults
- Created inventory files for dev and prod environments (get server IP from Pulumi)
- Created `group_vars/all.yml` with common variables
- Created `common` role with tasks for:
  - System packages installation
  - Deploy user creation with sudo access
  - SSH key authorization
  - Python 3.12 installation
  - uv package manager installation
  - Doppler CLI installation
  - UFW firewall configuration (22, 80, 443)
  - Nginx base setup
  - Application directory creation
- Created placeholder `django` role for 009-C
- Added justfile commands: `ansible-setup`, `ansible-check`, `ansible-inventory`
- Added ansible to flox environment
- Syntax check passes
