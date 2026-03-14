# SimPortControl User Manual - Required Screenshots

Save all screenshots to: `docs/manual/images/`

Use PNG format at a consistent width (recommended: 1200px or 1400px).

---

## Part 1: SimTech Guide

### 1.1 Getting Started

| Filename | Description | Notes |
|----------|-------------|-------|
| `01-login-screen.png` | Login page with username/password fields | Empty form, show branding |
| `02-login-filled.png` | Login page with credentials entered | Use test account, blur password |
| `03-dashboard-inactive.png` | Simulator grid with all simulators inactive | Show gray icons |
| `04-dashboard-active.png` | Simulator grid with 1-2 simulators active | Show green glow, "Internet Active" badges |

### 1.2 Activating Internet Access

| Filename | Description | Notes |
|----------|-------------|-------|
| `05-sim-detail-inactive.png` | Simulator detail view with port disabled | Red ethernet icon visible |
| `06-enable-confirmation.png` | Confirmation modal for enabling port | Show timeout duration |
| `07-sim-detail-active.png` | Simulator detail view with port enabled | Green icon, countdown timer visible |

### 1.3 Deactivating Internet Access

| Filename | Description | Notes |
|----------|-------------|-------|
| `08-disable-confirmation.png` | Confirmation modal for disabling port | Show warning message |
| `09-sim-detail-disabled.png` | Simulator detail after disabling | Back to red/inactive state |

### 1.4 Understanding Timeouts

| Filename | Description | Notes |
|----------|-------------|-------|
| `10-countdown-timer.png` | Close-up of countdown timer on active port | Show time remaining clearly |
| `11-multiple-ports-timers.png` | Simulator with multiple ports, different timers | If applicable to your setup |

### 1.5 Changing Your Password

| Filename | Description | Notes |
|----------|-------------|-------|
| `12-password-button.png` | Header showing Password (key) button | Highlight the button location |
| `13-change-password-modal.png` | Change password modal dialog | Show all three fields |
| `14-password-success.png` | Success toast notification | Show green success message |

---

## Part 2: Administrator Guide

### 2.1 Admin Dashboard Overview

| Filename | Description | Notes |
|----------|-------------|-------|
| `15-admin-dashboard.png` | Full admin dashboard with all menu tiles | Show all 7 sections |

### 2.2 User Management

| Filename | Description | Notes |
|----------|-------------|-------|
| `16-users-list.png` | User management table | Show mix of admin/simtech users |
| `17-add-user-simtech.png` | Add User modal - SimTech role selected | Show simulator checkboxes |
| `18-add-user-admin.png` | Add User modal - Admin role selected | Show "all simulators" message |
| `19-edit-user-modal.png` | Edit User modal | Show existing data populated |
| `20-delete-user-confirm.png` | Delete user confirmation modal | Show warning message |

### 2.3 Simulator Management

| Filename | Description | Notes |
|----------|-------------|-------|
| `21-simulators-list.png` | Simulators management table | Show multiple simulators |
| `22-add-simulator-modal.png` | Add Simulator modal | Show all fields |
| `23-edit-simulator-modal.png` | Edit Simulator modal | Show icon path field |

### 2.4 Switch Management

| Filename | Description | Notes |
|----------|-------------|-------|
| `24-switches-list.png` | Switches management table | Show switch with status |
| `25-add-switch-modal.png` | Add Switch modal | Show IP, username fields (blur password) |
| `26-test-connection-success.png` | Switch test connection success | Show success indicator/toast |
| `27-test-connection-failed.png` | Switch test connection failed | Show error message |

### 2.5 Port Assignments

| Filename | Description | Notes |
|----------|-------------|-------|
| `28-port-assignments-list.png` | Port assignments table | Show multiple assignments |
| `29-add-assignment-modal.png` | Add Port Assignment modal | Show all dropdowns |
| `30-edit-assignment-modal.png` | Edit Port Assignment modal | Show VLAN, timeout fields |

### 2.6 Port Discovery

| Filename | Description | Notes |
|----------|-------------|-------|
| `31-discovered-ports-empty.png` | Discovered ports view before scan | Show "Scan" button |
| `32-discovered-ports-scanning.png` | Scanning in progress | Show loading state if possible |
| `33-discovered-ports-results.png` | Discovered ports after scan | Show port status (up/down) |
| `34-assign-discovered-port.png` | Assigning a discovered port | Show assignment modal/action |

### 2.7 Activity Logs

| Filename | Description | Notes |
|----------|-------------|-------|
| `35-activity-logs.png` | Activity logs table | Show variety of actions |
| `36-activity-logs-filtered.png` | Activity logs with filter applied | If filtering is available |

### 2.8 System & SSL Management

| Filename | Description | Notes |
|----------|-------------|-------|
| `37-system-overview.png` | System view - health section | Show system info |
| `38-ssl-certificate-info.png` | SSL certificate status | Show domain, days remaining, expiry |
| `39-ssl-force-renew-confirm.png` | Force Renew confirmation modal | Show warning message |
| `40-ssl-renew-success.png` | SSL renewal success toast | Show success notification |

### 2.9 Force Enable (Admin Override)

| Filename | Description | Notes |
|----------|-------------|-------|
| `41-force-enable-button.png` | Simulator detail showing Force Enable button | Admin view only |
| `42-force-enable-modal.png` | Force Enable modal with timeout options | Show dropdown with "Always On" |
| `43-force-enable-reason.png` | Force Enable modal with reason filled | Show example reason |
| `44-always-on-badge.png` | Simulator showing "Always On" badge | After force enable with indefinite |

---

## Appendix Screenshots

### Troubleshooting

| Filename | Description | Notes |
|----------|-------------|-------|
| `45-connection-error.png` | Switch connection error example | Capture if you encounter one |
| `46-login-error.png` | Login failure message | Invalid credentials |

### General UI

| Filename | Description | Notes |
|----------|-------------|-------|
| `47-toast-success.png` | Success toast notification | Generic success |
| `48-toast-error.png` | Error toast notification | Generic error |
| `49-dark-mode-dashboard.png` | Dashboard in dark mode | Optional: show theme support |

---

## Screenshot Tips

1. **Browser:** Use Chrome or Firefox with DevTools to set consistent viewport (1400x900 recommended)
2. **Zoom:** 100% browser zoom for consistency
3. **Data:** Have realistic test data (multiple users, simulators, logs)
4. **Timing:** For countdown screenshots, enable a port and capture quickly
5. **Blur:** Blur any real passwords or sensitive IPs if needed
6. **Annotations:** Screenshots will be used as-is; annotations will be added in the manual via CSS overlays

---

## Checklist

- [ ] Images directory created: `docs/manual/images/`
- [ ] All Part 1 screenshots captured (14 images)
- [ ] All Part 2 screenshots captured (30 images)
- [ ] Appendix screenshots captured (5 images)
- [ ] All images named correctly per this document
- [ ] All images are consistent size/quality

**Total: 49 screenshots**
