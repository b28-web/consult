# 004-A: Cal.com Embed Component

**EP:** [EP-004-integrations](../enhancement_proposals/EP-004-integrations.md)
**Status:** pending

## Summary

Create an Astro component for embedding Cal.com booking widget in client sites.

## Acceptance Criteria

- [ ] Astro component accepts Cal.com username and event slug
- [ ] Renders Cal.com embed script
- [ ] Supports inline and popup modes
- [ ] Passes client branding (colors) to embed
- [ ] Works in site template

## Implementation Notes

```astro
---
// sites/_template/src/components/CalEmbed.astro
interface Props {
  username: string;
  eventSlug: string;
  mode?: 'inline' | 'popup';
}

const { username, eventSlug, mode = 'inline' } = Astro.props;
const calLink = `${username}/${eventSlug}`;
---

{mode === 'inline' ? (
  <div
    data-cal-link={calLink}
    data-cal-config='{"layout":"month_view"}'
    style="width:100%;height:100%;overflow:scroll"
  />
) : (
  <button
    data-cal-link={calLink}
    data-cal-config='{"layout":"month_view"}'
    class="btn btn-primary"
  >
    <slot>Book Appointment</slot>
  </button>
)}

<script is:inline src="https://app.cal.com/embed/embed.js" async></script>
```

Usage in site:
```astro
---
import CalEmbed from '@/components/CalEmbed.astro';
import { config } from '@/config';
---

{config.calcom && (
  <CalEmbed
    username={config.calcom.username}
    eventSlug={config.calcom.eventSlug}
  />
)}
```

## Progress

(Not started)
