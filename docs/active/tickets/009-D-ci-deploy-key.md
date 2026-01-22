# 009-D: CI Deploy Key Setup

## Parent EP
[EP-009: Ansible Deployment](../enhancement_proposals/EP-009-ansible-deployment.md)

## Objective
Set up passwordless SSH key for CI/CD deployments.

## Acceptance Criteria

- [x] Generate Ed25519 key pair without passphrase
- [x] Private key stored in Doppler as `DEPLOY_SSH_PRIVATE_KEY`
- [x] Public key added to deploy user's authorized_keys via Ansible
- [x] CI can SSH to server without passphrase prompt
- [x] Document key rotation procedure

## Technical Details

### Key Generation
```bash
ssh-keygen -t ed25519 -f deploy_key -N "" -C "ci-deploy@consult"
```

### Doppler Secret
```bash
doppler secrets set DEPLOY_SSH_PRIVATE_KEY --plain < deploy_key
# Delete local key after storing
rm deploy_key deploy_key.pub
```

### Ansible Task (in setup.yml)
```yaml
- name: Add CI deploy key to authorized_keys
  authorized_key:
    user: deploy
    key: "{{ lookup('env', 'DEPLOY_SSH_PUBLIC_KEY') }}"
    comment: "ci-deploy@consult"
```

### CI Usage (GitHub Actions)
```yaml
- name: Setup SSH key
  run: |
    mkdir -p ~/.ssh
    echo "${{ secrets.DEPLOY_SSH_PRIVATE_KEY }}" > ~/.ssh/deploy_key
    chmod 600 ~/.ssh/deploy_key

- name: Deploy
  run: |
    ansible-playbook -i ansible/inventory/dev.yml \
      --private-key ~/.ssh/deploy_key \
      ansible/playbooks/deploy.yml
```

### Key Rotation Procedure

**Step 1: Generate new key pair**
```bash
ssh-keygen -t ed25519 -f /tmp/ci-deploy-key-new -N "" -C "ci-deploy@consult"
```

**Step 2: Add new public key to Doppler (temporarily keep both)**
```bash
# Store new public key with a temp name
cat /tmp/ci-deploy-key-new.pub | doppler secrets set DEPLOY_SSH_PUBLIC_KEY_NEW
```

**Step 3: Update Ansible role to include both keys**
Temporarily modify the authorized_key task to add both old and new keys.

**Step 4: Run Ansible setup to add new key**
```bash
just ansible-setup dev
just ansible-setup prod
```

**Step 5: Update Doppler with new private key**
```bash
cat /tmp/ci-deploy-key-new | doppler secrets set DEPLOY_SSH_PRIVATE_KEY
```

**Step 6: Replace old public key in Doppler**
```bash
cat /tmp/ci-deploy-key-new.pub | doppler secrets set DEPLOY_SSH_PUBLIC_KEY
doppler secrets delete DEPLOY_SSH_PUBLIC_KEY_NEW
```

**Step 7: Remove old key from Ansible and re-run setup**
Revert the temporary Ansible changes, run setup again to remove old key.

**Step 8: Verify and cleanup**
```bash
# Test SSH access with new key
ssh -i /tmp/ci-deploy-key-new deploy@<server_ip> "echo 'Connection successful'"

# Delete local key files
rm /tmp/ci-deploy-key-new /tmp/ci-deploy-key-new.pub
```

**Step 9: Trigger a CI deploy to verify**
Push a commit or manually trigger the GitHub Actions workflow.

## Security Notes
- Key has no passphrase (required for non-interactive CI)
- Stored only in Doppler (not in repo)
- deploy user has limited sudo (only systemctl for consult services)

## Dependencies
- 009-B (deploy user exists)
- Doppler access

## Progress Log

### 2026-01-22
- Generated Ed25519 key pair without passphrase (`ci-deploy@consult`)
- Stored private key in Doppler as `DEPLOY_SSH_PRIVATE_KEY`
- Stored public key in Doppler as `DEPLOY_SSH_PUBLIC_KEY`
- Updated `ansible/roles/common/tasks/main.yml`:
  - Changed from `copy` to `ansible.posix.authorized_key` module
  - Added separate tasks for manual SSH key and CI deploy key
- Added `ansible.posix` collection to `ansible/requirements.yml`
- Documented detailed key rotation procedure
- All Ansible syntax checks pass
- Deploy key added to cloud-init for immediate availability on new servers
- Verified: CI/agent can SSH to server without passphrase prompt
- **COMPLETE** - All acceptance criteria met
