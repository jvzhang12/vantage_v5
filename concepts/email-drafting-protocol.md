---
id: email-drafting-protocol
title: Email Drafting Protocol
type: protocol
card: 'Reusable instructions for drafting email; style: clear, useful, human.'
created_at: '2026-04-28'
updated_at: '2026-04-28'
links_to: []
comes_from: []
status: active
source_instruction: Default Vantage email drafting protocol.
learned_by: system_default
protocol_kind: email
variables:
  recipient_name: Infer from the request; ask only when the recipient is ambiguous.
  sender_name: Infer from the user's saved preference when available.
  signature: ''
  style:
  - clear
  - useful
  - human
  format:
  - include greeting, body, close, and signature for complete drafts
applies_to:
- email
- emails
- business email
- draft email
- polish email
modifiable: true
---

## Protocol

Use this protocol whenever the user asks Vantage to draft, revise, polish, or format an email.

## Variables

- recipient_name: Infer from the request; ask only when the recipient is ambiguous.
- sender_name: Infer from the user's saved preference when available.
- style: clear, useful, human
- format: include greeting, body, close, and signature for complete drafts

## Procedure

1. Infer routine fields such as recipient name, sender name, context, and desired outcome from the request.
2. Ask a follow-up only when a missing variable would materially change the email.
3. Draft with a clear greeting, useful body, appropriate close, and the configured signature when available.
4. Respect any turn-specific override over this stored protocol.

## Latest Instruction

Default Vantage email drafting protocol.
