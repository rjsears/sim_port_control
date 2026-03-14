# Admin CRUD Functionality Design

**Date:** 2026-03-11
**Status:** Approved

## Overview

Wire up the existing admin views (Users, Simulators, Switches) to provide full CRUD functionality. The UI already exists as stubs - this work connects the buttons to forms and API calls.

## Scope

### In Scope
- Reusable Modal component matching existing style
- Add/Edit/Delete for Users
- Add for Simulators
- Add for Switches
- Form validation and error display

### Out of Scope
- UI redesign (keep existing interface exactly as-is)
- Edit/Delete for Simulators and Switches (can be added later)

## Components

### 1. BaseModal.vue
Reusable modal dialog component.

**Props:**
- `open` (Boolean) - controls visibility
- `title` (String) - modal header text
- `size` (String) - 'sm' | 'md' | 'lg', default 'md'

**Slots:**
- `default` - modal body content
- `footer` - action buttons

**Events:**
- `close` - emitted when modal should close

### 2. Form Fields
Use existing Tailwind form styling. Each admin view handles its own form state.

## Data Structures

### User Form
```javascript
{
  username: '',      // required, 3-50 chars
  password: '',      // required for create, 8+ chars
  role: 'simtech',   // 'admin' | 'simtech'
  assigned_simulator_ids: []  // array of simulator IDs
}
```

### Simulator Form
```javascript
{
  name: '',          // required, 1-100 chars
  short_name: '',    // required, 1-20 chars
  icon_path: ''      // optional
}
```

### Switch Form
```javascript
{
  name: '',          // required, 1-100 chars
  ip_address: '',    // required, valid IP
  username: '',      // required
  password: '',      // required for create
  device_type: 'cisco_ios'  // default value
}
```

## API Integration

Existing API methods in `src/services/api.js`:

| Action | API Method |
|--------|------------|
| Create User | `usersApi.create(data)` |
| Update User | `usersApi.update(id, data)` |
| Delete User | `usersApi.delete(id)` |
| Create Simulator | `simulatorsApi.create(data)` |
| Create Switch | `switchesApi.create(data)` |

## Error Handling

1. **Validation errors** - Display inline under form fields
2. **API errors** - Display at top of modal in red alert box
3. **Success** - Close modal, refresh list, show brief success message

## Implementation Order

1. Create BaseModal component
2. Update UsersView with Add/Edit/Delete modals
3. Update SimulatorsManageView with Add modal
4. Update SwitchesView with Add modal

## Testing

- Manual testing of each CRUD operation
- Verify form validation works
- Verify error states display correctly
- Verify list refreshes after changes
