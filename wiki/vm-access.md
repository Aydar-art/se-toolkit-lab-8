# VM access

<h2>Table of contents</h2>

- [About the VM access](#about-the-vm-access)
- [Set up `SSH` (LOCAL)](#set-up-ssh-local)
  - [Create a new `SSH` key (LOCAL)](#create-a-new-ssh-key-local)
  - [Find the `SSH` key files (LOCAL)](#find-the-ssh-key-files-local)
  - [Get the `SSH` public key (LOCAL)](#get-the-ssh-public-key-local)
  - [Start the `ssh-agent` (LOCAL)](#start-the-ssh-agent-local)
  - [Add the `SSH` key to the `ssh-agent` (LOCAL)](#add-the-ssh-key-to-the-ssh-agent-local)
  - [Verify the `SSH` setup (LOCAL)](#verify-the-ssh-setup-local)
- [Check that the VM is accessible (LOCAL)](#check-that-the-vm-is-accessible-local)
- [Add the VM to the `SSH` config (LOCAL)](#add-the-vm-to-the-ssh-config-local)
- [Connect to the VM (LOCAL)](#connect-to-the-vm-local)
- [Create the non-root user `<user>` (REMOTE)](#create-the-non-root-user-user-remote)
- [Set up the `SSH` key authentication for the user `<user>` (REMOTE)](#set-up-the-ssh-key-authentication-for-the-user-user-remote)
- [Verify that you can connect to the VM by `SSH` as the user `<user>` (LOCAL)](#verify-that-you-can-connect-to-the-vm-by-ssh-as-the-user-user-local)
- [Harden the `SSH` config (REMOTE)](#harden-the-ssh-config-remote)
- [Update the `SSH` config (LOCAL)](#update-the-ssh-config-local)
- [Restart `sshd` (REMOTE)](#restart-sshd-remote)
- [Verify you can connect as the user `<user>` (LOCAL)](#verify-you-can-connect-as-the-user-user-local)
- [Troubleshooting](#troubleshooting)
  - [`Permission denied (publickey)`](#permission-denied-publickey)
  - [`Bad owner or permissions`](#bad-owner-or-permissions)
  - [`Connection timed out`](#connection-timed-out)
  - [`ping` times out](#ping-times-out)
- [Login](#login)
  - [Login without password](#login-without-password)
  - [Login with password](#login-with-password)

## About the VM access

<!-- TODO first explicitly log in as root -->
<!-- TODO add LOCAL, REMOTE labels -->

> [!NOTE]
> Replace [`<user>`](./operating-system.md#user-placeholder) with the actual [username](./operating-system.md#username).

Setting up VM access involves two stages: connecting to the VM as [the user `root`](./linux.md#the-user-root) for the initial configuration, then creating a non-root user account with [`sudo`](./linux.md#sudo-group) privileges and reconfiguring [`SSH`](./ssh.md#what-is-ssh) to prevent login as the user `root`.

Complete these steps:

<!-- no toc -->
1. [Set up `SSH` (LOCAL)](#set-up-ssh-local)
2. [Create a VM](./vm.md#create-a-vm)
3. [Add the VM to the `SSH` config (LOCAL)](#add-the-vm-to-the-ssh-config-local)
4. [Connect to the VM (LOCAL)](#connect-to-the-vm-local)
5. [Create the non-root user `<user>` (REMOTE)](#create-the-non-root-user-user-remote)
6. [Set up the `SSH` key authentication for the user `<user>` (REMOTE)](#set-up-the-ssh-key-authentication-for-the-user-user-remote)
7. [Verify that you can connect to the VM by `SSH` as the user `<user>` (LOCAL)](#verify-that-you-can-connect-to-the-vm-by-ssh-as-the-user-user-local)
8. [Harden the `SSH` config (REMOTE)](#harden-the-ssh-config-remote)
9. [Update the `SSH` config (LOCAL)](#update-the-ssh-config-local)
10. [Restart `sshd` (REMOTE)](#restart-sshd-remote)

## Set up `SSH` (LOCAL)

Set up [`SSH`](./ssh.md#what-is-ssh) to connect to a [remote host](./computer-networks.md#remote-host).

Complete these steps:

<!-- no toc -->
1. [Check your current shell](./vs-code.md#check-the-current-shell-in-the-vs-code-terminal).
2. [Create a new `SSH` key (LOCAL)](#create-a-new-ssh-key-local)
3. [Find the `SSH` key files (LOCAL)](#find-the-ssh-key-files-local)
4. [Get the `SSH` public key (LOCAL)](#get-the-ssh-public-key-local)
5. [Start the `ssh-agent` (LOCAL)](#start-the-ssh-agent-local)
6. [Add the `SSH` key to the `ssh-agent` (LOCAL)](#add-the-ssh-key-to-the-ssh-agent-local)
7. [Verify the `SSH` setup (LOCAL)](#verify-the-ssh-setup-local)

### Create a new `SSH` key (LOCAL)

1. To generate a new key,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   ssh-keygen -t ed25519 -C "se-toolkit-student" -f ~/.ssh/se_toolkit_key
   ```

   *Note:* You can replace `"se-toolkit-student"` with your email or another label.

   *Note:* `-f ~/.ssh/se_toolkit_key` sets a custom file path and name.

   > Note
   > We'll use the `ed25519` algorithm, which is the modern standard for security and performance.
   > We chose this algorithm because it's used in the [`GitHub` docs on generating a new SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent#generating-a-new-ssh-key).

   > Note
   > Actually, you generate a key pair: a **private key** (secret) and a **public key** (safe to share).

2. **Passphrase:** When asked `Enter passphrase`, you may type a secure password or press `Enter` for no passphrase.

   *Note:* If you set a passphrase, use `ssh-agent` to avoid retyping it on every connection.

### Find the `SSH` key files (LOCAL)

1. To verify the keys were created,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   ls ~/.ssh/se_toolkit_key*
   ```

2. You should see two files listed.

   The file ending in `.pub` contains the [public key](./ssh.md#ssh-public-key).

   Another file contains the [private key](./ssh.md#ssh-private-key).

> [!CAUTION]
>
> Never share the private key.

### Get the `SSH` public key (LOCAL)

1. To view the content of the public key file,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cat ~/.ssh/se_toolkit_key.pub
   ```

   The output should be similar to this:

   ```terminal
   ssh-ed25519 AKdk38D3faWJnlFfalFJSKEFGG/vmLQ62Z+vpWCe5e/c2n37cnNc39N3c8qb7cBS+e3d se-toolkit-student
   ```

### Start the `ssh-agent` (LOCAL)

1. To start the agent,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   eval "$(ssh-agent -s)"
   ```

### Add the `SSH` key to the `ssh-agent` (LOCAL)

1. To add the key to the `ssh-agent`,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   ssh-add ~/.ssh/se_toolkit_key
   ```

### Verify the `SSH` setup (LOCAL)

1. To list the loaded keys,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   ssh-add -l
   ```

   You should see your key fingerprint in the output.

> <h3>Troubleshooting</h3>
>
> **`The agent has no identities`.**
>
> Complete these steps:
>
> - [Start the `ssh-agent` (LOCAL)](#start-the-ssh-agent-local).
> - [Add the `SSH` key to the `ssh-agent` (LOCAL)](#add-the-ssh-key-to-the-ssh-agent-local).
> - [Verify the `SSH` setup (LOCAL)](#verify-the-ssh-setup-local).

## Check that the VM is accessible (LOCAL)

1. [Connect to the correct network](./vm.md#connect-to-the-correct-network).

2. [Get `<your-vm-ip-address>`](./vm.md#get-the-ip-address-of-the-vm).

3. To check that the VM is accessible,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   ping <your-vm-ip-address>
   ```

## Add the VM to the `SSH` config (LOCAL)

1. [Open the file using `code`](./vs-code.md#open-the-file-or-the-directory-using-code):
   `~/.ssh/config`.

2. Add this text at the end of the opened file:

   - `Linux`, `Windows` (`WSL`):

     ```text
     Host se-toolkit-vm
        HostName <your-vm-ip-address>
        User root
        IdentityFile ~/.ssh/se_toolkit_key
        AddKeysToAgent yes
     ```

   - `macOS`:

     ```text
     Host se-toolkit-vm
        HostName <your-vm-ip-address>
        User root
        IdentityFile ~/.ssh/se_toolkit_key
        AddKeysToAgent yes
        UseKeychain yes
     ```

   Replace the placeholder [`<your-vm-ip-address>`](./vm.md#your-vm-ip-address-placeholder).

   > 🟩 **Tip**
   >
   > If `~/.ssh/config` already contains a `Host se-toolkit-vm` entry, skip this step.

## Connect to the VM (LOCAL)

1. [Connect to the correct network](./vm.md#connect-to-the-correct-network).

2. To connect to the VM,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   ssh se-toolkit-vm
   ```

3. If this is your first time connecting:

   1. You will see a message:
      `The authenticity of host ... can't be established.`

   2. Type `yes` and press `Enter`.

4. After a successful login, you should see the [shell prompt](./shell.md#shell-prompt):

   ```terminal
   <user>@<your-vm-name>:~#
   ```

   > 🟦 **Note**
   >
   > [`<user>`](./operating-system.md#user-placeholder) is the same as you specified when [adding the VM to the `SSH` config (LOCAL)](#add-the-vm-to-the-ssh-config-local).
   >
   > [`<your-vm-name>`](./vm.md#your-vm-name-placeholder) is the same as you specified when [creating the VM](./vm.md#create-a-vm).

5. You are in the [home directory (`~`)](./file-system.md#home-directory-).

<!-- 7. If you use the `ms-vscode-remote.remote-ssh` extension in `VS Code`, the status bar should show that you are connected to a remote host.
   TODO explain how to use -->

## Create the non-root user `<user>` (REMOTE)

> [!NOTE]
> Replace [`<user>`](./operating-system.md#user-placeholder) with the actual [username](./operating-system.md#username).

1. To create the user `<user>`,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   adduser <user>
   ```

2. To add the user `<user>` to the [`sudo` group](./linux.md#sudo-group),

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   usermod -aG sudo <user>
   ```

## Set up the `SSH` key authentication for the user `<user>` (REMOTE)

> [!NOTE]
> Replace [`<user>`](./operating-system.md#user-placeholder) with the actual [username](./operating-system.md#username).

1. To create the `.ssh/` directory for the user `<user>`,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   mkdir -p /home/<user>/.ssh
   ```

2. To copy the authorized keys from [the user `root`](./linux.md#the-user-root),

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cp /root/.ssh/authorized_keys /home/<user>/.ssh/
   ```

3. To set the correct ownership on the `.ssh/` directory,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   chown -R <user>:<user> /home/<user>/.ssh
   ```

   > 🟦 **Note**
   >
   > See [Change the owner and group (recursive)](./linux-administration.md#change-the-owner-and-group-recursive).

4. To set the correct permissions on the `.ssh/` directory,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   chmod 700 /home/<user>/.ssh
   ```

   > 🟦 **Note**
   >
   > See [Set the permissions](./linux-administration.md#set-the-permissions).

   <!-- TODO why these permissions are correct? -->

5. To set the correct permissions on the `authorized_keys` file,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   chmod 600 /home/<user>/.ssh/authorized_keys
   ```

   <!-- TODO why these permissions are correct? -->

## Verify that you can connect to the VM by `SSH` as the user `<user>` (LOCAL)

> [!NOTE]
> Replace [`<user>`](./operating-system.md#user-placeholder) with the actual [username](./operating-system.md#username).

1. [Open a new `VS Code Terminal`](./vs-code.md#open-a-new-vs-code-terminal).

2. To connect as the user `<user>`,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   ssh -i ~/.ssh/se_toolkit_key <user>@<your-vm-ip-address>
   ```

   Replace the placeholder [`<your-vm-ip-address>`](./vm.md#your-vm-ip-address-placeholder).

3. Confirm the connection did not prompt for a password.

## Harden the `SSH` config (REMOTE)

<!-- TODO need to log in as root? -->
<!-- TODO what are the implications -->
<!-- TODO check there's this file at all with this content -->
<!-- TODO keep root login but make it non-default? -->

1. To open the [`SSH`](./ssh.md#what-is-ssh) config,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   sudo nano /etc/ssh/sshd_config
   ```

2. Find the line `PermitRootLogin` and set it to:

   ```text
   PermitRootLogin no
   ```

3. Find the line `PasswordAuthentication` and set it to:

   ```text
   PasswordAuthentication no
   ```

4. Save (`Ctrl+O`, `Enter`).

5. Exit (`Ctrl+X`).

## Update the `SSH` config (LOCAL)

> [!NOTE]
> Replace [`<user>`](./operating-system.md#user-placeholder) with the actual [username](./operating-system.md#username).

1. [Open the file](./vs-code.md#open-the-file):
   `~/.ssh/config`

2. Find the `se-toolkit-vm` entry.

3. Change `User root` to `User <user>`.

   Replace the placeholder `<user>`.

   The result should look like this:

   - `Linux`, `Windows`:

     ```text
     Host se-toolkit-vm
        HostName <your-vm-ip-address>
        User <user>
        IdentityFile ~/.ssh/se_toolkit_key
        AddKeysToAgent yes
        PasswordAuthentication no
     ```

   - `macOS`:

     ```text
     Host se-toolkit-vm
        HostName <your-vm-ip-address>
        User <user>
        IdentityFile ~/.ssh/se_toolkit_key
        AddKeysToAgent yes
        PasswordAuthentication no
        UseKeychain yes
     ```

## Restart `sshd` (REMOTE)

1. [Connect to the VM](#connect-to-the-vm-local).

2. To validate the config,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   sudo sshd -t
   ```

   If the command prints no output, the config is valid. If it prints errors, fix them in `/etc/ssh/sshd_config` before continuing.

3. To restart the service,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   sudo systemctl restart sshd
   ```

## Verify you can connect as the user `<user>` (LOCAL)

1. To verify you can connect as the user `<user>`,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   ssh se-toolkit-vm
   ```

2. Confirm you are logged in as the user `<user>`,
   not [the user `root`](./linux.md#the-user-root).

<!-- TODO where should this important alert be moved? -->
> [!IMPORTANT]
> Keep your current `SSH` session open until you confirm the new connection works. If the new connection fails, use the existing session to fix the config.

## Troubleshooting

<!-- TODO make dry and well-formatted -->

- [`Permission denied (publickey)`](#permission-denied-publickey)
- [`Bad owner or permissions`](#bad-owner-or-permissions)
- [`Connection timed out`](#connection-timed-out)

### `Permission denied (publickey)`

1. Check `IdentityFile` in `~/.ssh/config`.
2. Ensure the `SSH` public key was added to the remote host.
3. Ensure your key is loaded: `ssh-add -l`.

### `Bad owner or permissions`

1. To fix the permissions,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   chmod 700 ~/.ssh
   chmod 600 ~/.ssh/se_toolkit_key
   chmod 644 ~/.ssh/se_toolkit_key.pub
   ```

### `Connection timed out`

1. Verify host IP and network connectivity.
2. Verify the VM is running.
3. To ping the VM,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   ping <your-vm-ip-address>
   ```

   You should see logs like these:

   ```terminal
   PING 192.0.2.1 (192.0.2.1) 56(84) bytes of data.

   64 bytes from 192.0.2.1: icmp_seq=1 ttl=61 time=2.15 ms
   64 bytes from 192.0.2.1: icmp_seq=2 ttl=61 time=0.996 ms
   64 bytes from 192.0.2.1: icmp_seq=3 ttl=61 time=1.08 ms
   
   ...
   ```

4. To enable verbose logs for debugging,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   ssh -v se-toolkit-vm
   ```

5. Try to stop, delete, and create a new VM if there are still problems.

### `ping` times out

1. Recreate the VM with the same public key as [before](#create-a-new-ssh-key).

If you can't connect:

1. [Go to the VM page](./vm.md#go-to-the-vm-page).
2. Verify the VM is in `Running` status.
3. Verify the VM IP address has not changed.
4. To test the [`SSH`](./ssh.md) connection in verbose mode,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   ssh -v se-toolkit-vm
   ```

5. If you get `Permission denied (publickey)`, check:
   1. Your public key was added to the VM configuration.
   2. `IdentityFile` in your `SSH` config points to the correct private key.
   3. Your private key file permissions are correct (`chmod 600 ~/.ssh/se_toolkit_key` on `Linux`/`macOS`/`WSL`).
6. Ask the TA to help and show them:
   1. The VM page.
   2. The output of `ssh -v se-toolkit-vm`.
   3. Your [`VS Code Terminal`](./vs-code.md#vs-code-terminal).

<!-- TODO forgot to add SSH key when creating the VM -->

## Login

`SSH` supports two authentication methods: [key-based](#login-without-password) (no password prompt) and [password-based](#login-with-password).

### Login without password

Key-based authentication uses your private key to prove your identity. The remote host checks whether the matching public key is listed as authorized.

This is the recommended method and is what [Set up `SSH`](./vm-access.md#set-up-ssh) configures.

1. [Set up `SSH`](./vm-access.md#set-up-ssh).
2. Ensure your `SSH` public key is added to the remote host.
3. [Connect to the VM](./vm-access.md#connect-to-the-vm).

You will not be asked for a password.

### Login with password

Password-based authentication asks you to type the remote user's password.

> [!NOTE]
> Password authentication may be disabled on the VM. Use [key-based authentication](#login-without-password) instead.

1. To connect with a password,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   ssh -o PasswordAuthentication=yes root@<your-vm-ip-address>
   ```

2. Type the VM's root password when prompted.