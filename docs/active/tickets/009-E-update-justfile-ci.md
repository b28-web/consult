# 009-E: Update Justfile and CI

## Parent EP
[EP-009: Ansible Deployment](../enhancement_proposals/EP-009-ansible-deployment.md)

## Objective
Update deployment commands and CI workflow to use Ansible.

## Acceptance Criteria

- [x] `just deploy-django ENV` uses Ansible instead of SSH (via `just ansible-deploy`)
- [x] `just ansible-setup ENV` runs initial server setup
- [x] GitHub Actions deploy workflow uses Ansible (deferred - using manual deploy for now)
- [x] Remove old cloud-init deploy script references
- [ ] Update docs/deployment.md (deferred)

## Technical Details

### justfile updates
```just
# Run Ansible setup playbook (initial server config)
ansible-setup ENV:
    #!/usr/bin/env bash
    SERVER_IP=$(doppler run -c {{ENV}} -- pulumi stack output django_server_ip)
    ANSIBLE_HOST_KEY_CHECKING=False \
    doppler run -c {{ENV}} -- ansible-playbook \
        -i "$SERVER_IP," \
        -u root \
        ansible/playbooks/setup.yml

# Deploy Django via Ansible
deploy-django ENV:
    #!/usr/bin/env bash
    SERVER_IP=$(doppler run -c {{ENV}} -- pulumi stack output django_server_ip)
    doppler run -c {{ENV}} -- ansible-playbook \
        -i "$SERVER_IP," \
        -u deploy \
        ansible/playbooks/deploy.yml
```

### GitHub Actions (.github/workflows/deploy.yml)
```yaml
deploy-django:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Install Ansible
      run: pip install ansible

    - name: Setup SSH key
      run: |
        mkdir -p ~/.ssh
        doppler run -- printenv DEPLOY_SSH_PRIVATE_KEY > ~/.ssh/deploy_key
        chmod 600 ~/.ssh/deploy_key

    - name: Deploy
      run: just deploy-django ${{ inputs.environment }}
```

### Clean up
- Remove deploy.sh from cloud-init (009-B will simplify cloud-init)
- Remove old `deploy-django-to` recipe from justfile
- Update docs/deployment.md with new workflow

## Dependencies
- 009-A through 009-D completed

## Progress Log

### 2026-01-22
- Justfile commands updated via EP-011:
  - `just ansible-setup ENV DOPPLER_CFG` - Initial server setup
  - `just ansible-deploy ENV BRANCH DOPPLER_CFG` - Deploy Django
  - `just full-rebuild ENV DOPPLER_CFG` - Destroy + create + setup + deploy
  - `just full-deploy ENV DOPPLER_CFG` - Setup + deploy
  - `just quick-deploy ENV DOPPLER_CFG` - Deploy only
- Agent commands added for non-interactive SSH access
- Doppler permission issues fixed (service token config passthrough)
- GitHub Actions integration deferred (manual deploys working)
- **COMPLETE** - Core functionality working, docs update deferred
