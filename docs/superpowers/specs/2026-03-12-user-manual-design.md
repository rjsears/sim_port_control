# SimPortControl User Manual - Design Specification

**Date:** 2026-03-12
**Status:** Approved
**Author:** Claude + Richard Sears

## Overview

Create a comprehensive, branded user manual for SimPortControl that serves both SimTech end users and Administrators. The manual will be delivered as an HTML document with print-optimized CSS, allowing it to be both hosted on the web and exported to PDF.

## Requirements

### Audience
- **SimTechs:** Day-to-day users who enable/disable simulator internet access
- **Administrators:** System managers who configure switches, simulators, users, and maintain the system

### Format
- HTML with embedded CSS for web viewing
- Print-specific CSS (`@media print`) for clean PDF export
- Branded with SimPortControl colors and styling
- Technical manual style with numbered sections, TOC, and cross-references

### Scope: Comprehensive Coverage (15-20 screenshots)
- All user-facing screens
- All admin management screens
- All modal dialogs
- Key workflows annotated

## Document Structure

```
Cover Page
Table of Contents

Part 1: SimTech Guide
  1.1 Getting Started
  1.2 Activating Internet Access
  1.3 Deactivating Internet Access
  1.4 Understanding Timeouts
  1.5 Changing Your Password

Part 2: Administrator Guide
  2.1 Admin Dashboard Overview
  2.2 User Management
  2.3 Simulator Management
  2.4 Switch Management
  2.5 Port Assignments
  2.6 Port Discovery
  2.7 Activity Logs
  2.8 System & SSL Management
  2.9 Force Enable (Admin Override)

Appendix A: Troubleshooting
Appendix B: Quick Reference
Index
```

## Deliverables

1. `docs/manual/index.html` - Complete HTML manual with screenshot placeholders
2. `docs/manual/styles.css` - Branding and print styles
3. `docs/manual/SCREENSHOTS-NEEDED.md` - Detailed list of required screenshots

## Branding

- Primary colors from SimPortControl app
- Header with SimPortControl logo/banner
- Footer with version and date
- Consistent typography throughout

## Technical Approach

- Single-page HTML document with anchor navigation
- CSS Grid/Flexbox for layout
- Print CSS for page breaks, headers, footers
- Screenshot placeholders as styled divs with descriptive labels
- Images stored in `docs/manual/images/` directory
